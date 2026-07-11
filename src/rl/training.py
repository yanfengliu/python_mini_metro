"""Stable-Baselines3 orchestration without making RL packages core imports."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable

from rl.artifacts import sha256_file
from rl.manifest import ManifestCompatibilityError, TrainingManifest
from rl.protocol import (
    TaskSpec,
    protocol_fingerprint,
    resolve_render_profile,
)

DEFAULT_FRAME_STACK = 4
DEFAULT_FEATURES_DIM = 256
TRAINING_SOURCE_PATHS = (
    "environment.yml",
    "requirements-locked.txt",
    "requirements-rl-locked.txt",
    "requirements-rl.txt",
    "requirements.txt",
    "scripts/evaluate_rl.py",
    "scripts/train_rl.py",
    "src/rl/artifacts.py",
    "src/rl/evaluation.py",
    "src/rl/manifest.py",
    "src/rl/model.py",
    "src/rl/provenance.py",
    "src/rl/training.py",
)
PPO_DEFAULTS: Mapping[str, int | float] = MappingProxyType(
    {
        "n_steps": 128,
        "n_epochs": 4,
        "learning_rate": 2.5e-4,
        "gamma": 0.999,
        "gae_lambda": 0.95,
        "clip_range": 0.1,
        "ent_coef": 0.01,
        "vf_coef": 0.5,
        "max_grad_norm": 0.5,
    }
)


@lru_cache(maxsize=1)
def require_rl_dependencies() -> SimpleNamespace:
    """Import the optional training stack or raise one actionable error."""

    module_names = {
        "gymnasium": "gymnasium",
        "stable_baselines3": "stable_baselines3",
        "callbacks": "stable_baselines3.common.callbacks",
        "evaluation": "stable_baselines3.common.evaluation",
        "vec_env": "stable_baselines3.common.vec_env",
        "torch": "torch",
    }
    modules: dict[str, Any] = {}
    missing: list[str] = []
    for key, module_name in module_names.items():
        try:
            modules[key] = importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        names = ", ".join(sorted(missing))
        raise RuntimeError(
            "RL dependencies are not installed "
            f"({names}); install requirements-rl-locked.txt or requirements-rl.txt"
        )
    return SimpleNamespace(**modules)


@dataclass(frozen=True, slots=True)
class PlayerEnvThunk:
    """Spawn-safe constructor for one independently seeded player environment."""

    render_profile: str
    fixed_ticks: int
    reward_mode: str
    max_episode_steps: int
    seed: int

    def __call__(self) -> Any:
        from rl.player_env import PlayerPixelEnv

        env = PlayerPixelEnv(
            render_profile=self.render_profile,
            fixed_ticks=self.fixed_ticks,
            reward_mode=self.reward_mode,
            max_episode_steps=self.max_episode_steps,
        )
        env.action_space.seed(self.seed)
        env.observation_space.seed(self.seed)
        return env


def make_env_thunks(
    task_spec: TaskSpec,
    *,
    n_envs: int,
    seed: int,
) -> tuple[PlayerEnvThunk, ...]:
    if isinstance(n_envs, bool) or not isinstance(n_envs, int) or n_envs <= 0:
        raise ValueError("n_envs must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    return tuple(
        PlayerEnvThunk(
            render_profile=task_spec.render_profile.name,
            fixed_ticks=task_spec.fixed_ticks,
            reward_mode=task_spec.reward_mode.value,
            max_episode_steps=task_spec.max_episode_steps,
            seed=seed + rank,
        )
        for rank in range(n_envs)
    )


def select_base_vec_env_class(n_envs: int) -> type[Any]:
    if isinstance(n_envs, bool) or not isinstance(n_envs, int) or n_envs <= 0:
        raise ValueError("n_envs must be a positive integer")
    components = require_rl_dependencies()
    if n_envs == 1:
        return components.vec_env.DummyVecEnv
    return components.vec_env.SubprocVecEnv


def build_vector_env(
    task_spec: TaskSpec,
    *,
    n_envs: int,
    seed: int,
    frame_stack: int = DEFAULT_FRAME_STACK,
) -> Any:
    """Build Dummy/Spawn workers, then monitor and channel-first frame stack."""

    if isinstance(frame_stack, bool) or not isinstance(frame_stack, int):
        raise TypeError("frame_stack must be an integer")
    if frame_stack <= 0:
        raise ValueError("frame_stack must be positive")
    components = require_rl_dependencies()
    thunks = make_env_thunks(
        task_spec,
        n_envs=n_envs,
        seed=seed,
    )
    base_class = select_base_vec_env_class(n_envs)
    if n_envs == 1:
        base = base_class(list(thunks))
    else:
        base = base_class(list(thunks), start_method="spawn")
    try:
        base.seed(seed)
        monitored = components.vec_env.VecMonitor(base)
        return components.vec_env.VecFrameStack(
            monitored, n_stack=frame_stack, channels_order="first"
        )
    except BaseException:
        base.close()
        raise


def adjusted_batch_size(rollout_size: int, preferred: int = 256) -> int:
    """Choose the largest useful minibatch divisor near the preferred size."""

    for value, name in ((rollout_size, "rollout_size"), (preferred, "preferred")):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if rollout_size < 2:
        raise ValueError("PPO rollout_size must be at least two")
    for candidate in range(min(rollout_size, preferred), 1, -1):
        if rollout_size % candidate == 0:
            return candidate
    return rollout_size


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _finite_number(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    converted = float(value)
    if not math.isfinite(converted) or (positive and converted <= 0):
        qualifier = "positive and " if positive else ""
        raise ValueError(f"{name} must be {qualifier}finite")
    return converted


def ppo_manifest_hyperparameters(
    *,
    n_envs: int,
    n_steps: int = int(PPO_DEFAULTS["n_steps"]),
    n_epochs: int = int(PPO_DEFAULTS["n_epochs"]),
    learning_rate: float = float(PPO_DEFAULTS["learning_rate"]),
    gamma: float = float(PPO_DEFAULTS["gamma"]),
    gae_lambda: float = float(PPO_DEFAULTS["gae_lambda"]),
    clip_range: float = float(PPO_DEFAULTS["clip_range"]),
    ent_coef: float = float(PPO_DEFAULTS["ent_coef"]),
    vf_coef: float = float(PPO_DEFAULTS["vf_coef"]),
    max_grad_norm: float = float(PPO_DEFAULTS["max_grad_norm"]),
    features_dim: int = DEFAULT_FEATURES_DIM,
) -> dict[str, int | float | str]:
    n_envs = _positive_int(n_envs, "n_envs")
    n_steps = _positive_int(n_steps, "n_steps")
    n_epochs = _positive_int(n_epochs, "n_epochs")
    features_dim = _positive_int(features_dim, "features_dim")
    rollout_size = n_envs * n_steps
    return {
        "batch_size": adjusted_batch_size(rollout_size),
        "clip_range": _finite_number(clip_range, "clip_range", positive=True),
        "ent_coef": _finite_number(ent_coef, "ent_coef"),
        "features_extractor": "MiniMetroCNN",
        "features_dim": features_dim,
        "gae_lambda": _finite_number(gae_lambda, "gae_lambda", positive=True),
        "gamma": _finite_number(gamma, "gamma", positive=True),
        "learning_rate": _finite_number(learning_rate, "learning_rate", positive=True),
        "learning_rate_schedule": "linear",
        "max_grad_norm": _finite_number(max_grad_norm, "max_grad_norm", positive=True),
        "n_epochs": n_epochs,
        "n_steps": n_steps,
        "policy": "CnnPolicy",
        "vf_coef": _finite_number(vf_coef, "vf_coef"),
    }


@dataclass(frozen=True, slots=True)
class LinearSchedule:
    initial_value: float

    def __call__(self, progress_remaining: float) -> float:
        return self.initial_value * float(progress_remaining)


def make_ppo(
    env: Any,
    *,
    seed: int,
    n_envs: int,
    device: str = "auto",
    tensorboard_log: str | Path | None = None,
    verbose: int = 0,
    n_steps: int = int(PPO_DEFAULTS["n_steps"]),
    n_epochs: int = int(PPO_DEFAULTS["n_epochs"]),
    learning_rate: float = float(PPO_DEFAULTS["learning_rate"]),
    gamma: float = float(PPO_DEFAULTS["gamma"]),
    gae_lambda: float = float(PPO_DEFAULTS["gae_lambda"]),
    clip_range: float = float(PPO_DEFAULTS["clip_range"]),
    ent_coef: float = float(PPO_DEFAULTS["ent_coef"]),
    vf_coef: float = float(PPO_DEFAULTS["vf_coef"]),
    max_grad_norm: float = float(PPO_DEFAULTS["max_grad_norm"]),
    features_dim: int = DEFAULT_FEATURES_DIM,
) -> Any:
    components = require_rl_dependencies()
    from rl.model import MiniMetroCNN

    hyperparameters = ppo_manifest_hyperparameters(
        n_envs=n_envs,
        n_steps=n_steps,
        n_epochs=n_epochs,
        learning_rate=learning_rate,
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
        max_grad_norm=max_grad_norm,
        features_dim=features_dim,
    )
    return components.stable_baselines3.PPO(
        "CnnPolicy",
        env,
        learning_rate=LinearSchedule(float(hyperparameters["learning_rate"])),
        n_steps=int(hyperparameters["n_steps"]),
        batch_size=int(hyperparameters["batch_size"]),
        n_epochs=int(hyperparameters["n_epochs"]),
        gamma=float(hyperparameters["gamma"]),
        gae_lambda=float(hyperparameters["gae_lambda"]),
        clip_range=float(hyperparameters["clip_range"]),
        ent_coef=float(hyperparameters["ent_coef"]),
        vf_coef=float(hyperparameters["vf_coef"]),
        max_grad_norm=float(hyperparameters["max_grad_norm"]),
        policy_kwargs={
            "features_extractor_class": MiniMetroCNN,
            "features_extractor_kwargs": {
                "features_dim": int(hyperparameters["features_dim"])
            },
        },
        seed=seed,
        device=device,
        tensorboard_log=(str(tensorboard_log) if tensorboard_log else None),
        verbose=verbose,
    )


def load_ppo_model(
    source: Any,
    *,
    env: Any,
    seed: int,
    device: str = "auto",
) -> Any:
    return require_rl_dependencies().stable_baselines3.PPO.load(
        source,
        env=env,
        device=device,
        seed=seed,
    )


def callback_frequency(transitions: int, n_envs: int) -> int:
    transitions = _positive_int(transitions, "transitions")
    n_envs = _positive_int(n_envs, "n_envs")
    return max(transitions // n_envs, 1)


def build_training_callbacks(
    run_dir: str | Path,
    *,
    eval_env: Any,
    eval_seed: int,
    n_envs: int,
    checkpoint_every: int,
    eval_every: int,
    eval_episodes: int,
    after_checkpoint: Callable[[int], None] | None = None,
) -> Any:
    """Create transition-adjusted checkpoint and deterministic evaluation hooks."""

    if isinstance(eval_seed, bool) or not isinstance(eval_seed, int) or eval_seed < 0:
        raise ValueError("eval_seed must be a non-negative integer")
    components = require_rl_dependencies()
    run_path = Path(run_dir)
    checkpoint_path = run_path / "checkpoints"
    best_path = run_path / "best"
    evaluation_path = run_path / "evaluations"
    for path in (checkpoint_path, best_path, evaluation_path):
        path.mkdir(parents=True, exist_ok=True)
    checkpoint = components.callbacks.CheckpointCallback(
        save_freq=callback_frequency(checkpoint_every, n_envs),
        save_path=str(checkpoint_path),
        name_prefix="mini_metro_ppo",
        verbose=1,
    )

    class SeededEvalCallback(components.callbacks.EvalCallback):
        def _on_step(self) -> bool:
            if self.eval_freq > 0 and self.n_calls % self.eval_freq == 0:
                self.eval_env.seed(eval_seed)
            return bool(super()._on_step())

    evaluation = SeededEvalCallback(
        eval_env,
        best_model_save_path=str(best_path),
        log_path=str(evaluation_path),
        eval_freq=callback_frequency(eval_every, n_envs),
        n_eval_episodes=_positive_int(eval_episodes, "eval_episodes"),
        deterministic=True,
        render=False,
        verbose=1,
    )
    callbacks: list[Any] = [checkpoint, evaluation]
    if after_checkpoint is not None:
        checkpoint_frequency = callback_frequency(checkpoint_every, n_envs)
        evaluation_frequency = callback_frequency(eval_every, n_envs)

        class ProvenanceCallback(components.callbacks.BaseCallback):
            def _on_step(self) -> bool:
                if (
                    self.n_calls % checkpoint_frequency == 0
                    or self.n_calls % evaluation_frequency == 0
                ):
                    after_checkpoint(int(self.model.num_timesteps))
                return True

        callbacks.append(ProvenanceCallback(verbose=0))
    return components.callbacks.CallbackList(callbacks)


def task_spec_from_manifest(manifest: TrainingManifest) -> TaskSpec:
    if manifest.protocol_fingerprint != protocol_fingerprint():
        raise ManifestCompatibilityError(
            "protocol fingerprint mismatch while reconstructing saved task"
        )
    spec = TaskSpec(
        resolve_render_profile(manifest.render_profile),
        manifest.fixed_ticks,
        manifest.reward_mode,
        manifest.max_episode_steps,
    )
    if spec.fingerprint() != manifest.task_fingerprint:
        raise ManifestCompatibilityError(
            "task fingerprint does not match manifest task fields"
        )
    return spec


def compute_content_fingerprint(repo_root: str | Path) -> str:
    """Hash game, player-environment, and visible-content files deterministically."""

    root = Path(repo_root).resolve()
    files = []
    for path in (root / "src").rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("src/rl/") and relative not in {
            "src/rl/player_env.py",
            "src/rl/protocol.py",
        }:
            continue
        files.append(path)
    for directory in (
        root / "assets",
        root / "content",
        root / "data",
        root / "resources",
        root / "src" / "assets",
        root / "src" / "resources",
    ):
        if directory.exists():
            files.extend(path for path in directory.rglob("*") if path.is_file())
    return _fingerprint_files(root, files, "mini-metro-environment-content-v1")


def compute_training_fingerprint(repo_root: str | Path) -> str:
    """Hash trainer/model code and its direct dependency declarations."""

    root = Path(repo_root).resolve()
    files = [root / relative for relative in TRAINING_SOURCE_PATHS]
    missing = [
        path.relative_to(root).as_posix() for path in files if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(f"training fingerprint inputs are missing: {missing}")
    return _fingerprint_files(root, files, "mini-metro-training-source-v1")


def _fingerprint_files(root: Path, files: list[Path], schema: str) -> str:
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(set(files))
    ]
    encoded = json.dumps(
        {"files": entries, "schema": schema},
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

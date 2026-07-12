"""Vector environments, callbacks, task reconstruction, and fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl.artifacts import sha256_file
from rl.dependencies import require_rl_dependencies as require_rl_dependencies
from rl.history import HistoryDescriptor, contiguous_history
from rl.manifest import ManifestCompatibilityError, TrainingManifest
from rl.policy import (
    DEFAULT_ALGORITHM,
    DEFAULT_FEATURES_DIM,
    DEFAULT_FRAME_STACK,
    DEFAULT_LSTM_HIDDEN_SIZE,
    DEFAULT_N_LSTM_LAYERS,
    DEFAULT_RECURRENT_BATCH_SIZE,
    PPO_DEFAULTS,
    RECURRENT_PPO_DEFAULTS,
    SUPPORTED_ALGORITHMS,
    LinearSchedule,
    _positive_int,
    _require_supported_algorithm,
    adjusted_batch_size,
    load_model,
    load_ppo_model,
    make_model,
    make_ppo,
    model_manifest_hyperparameters,
    ppo_manifest_hyperparameters,
)
from rl.protocol import (
    TaskSpec,
    protocol_fingerprint,
    resolve_render_profile,
)

__all__ = (
    "DEFAULT_ALGORITHM",
    "DEFAULT_FEATURES_DIM",
    "DEFAULT_FRAME_STACK",
    "DEFAULT_LSTM_HIDDEN_SIZE",
    "DEFAULT_N_LSTM_LAYERS",
    "DEFAULT_RECURRENT_BATCH_SIZE",
    "PPO_DEFAULTS",
    "RECURRENT_PPO_DEFAULTS",
    "SUPPORTED_ALGORITHMS",
    "LinearSchedule",
    "PlayerEnvThunk",
    "adjusted_batch_size",
    "build_training_callbacks",
    "build_vector_env",
    "callback_frequency",
    "compute_content_fingerprint",
    "compute_training_fingerprint",
    "load_model",
    "load_ppo_model",
    "make_env_thunks",
    "make_model",
    "make_ppo",
    "model_manifest_hyperparameters",
    "ppo_manifest_hyperparameters",
    "require_contiguous_frame_stack_history",
    "require_rl_dependencies",
    "select_base_vec_env_class",
    "task_spec_from_manifest",
)

TRAINING_SOURCE_PATHS = (
    "environment.yml",
    "requirements-locked.txt",
    "requirements-rl-locked.txt",
    "requirements-rl.txt",
    "requirements.txt",
    "scripts/evaluate_rl.py",
    "scripts/train_rl.py",
    "src/rl/artifacts.py",
    "src/rl/dependencies.py",
    "src/rl/evaluation.py",
    "src/rl/history.py",
    "src/rl/manifest.py",
    "src/rl/manifest_schema.py",
    "src/rl/model.py",
    "src/rl/policy.py",
    "src/rl/provenance.py",
    "src/rl/temporal_history.py",
    "src/rl/training.py",
)


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


def require_contiguous_frame_stack_history(
    manifest: TrainingManifest,
) -> HistoryDescriptor:
    """Fail closed while the runtime still delegates history to VecFrameStack."""

    expected = contiguous_history(manifest.frame_stack)
    if manifest.history != expected:
        raise ManifestCompatibilityError(
            "the current frame-stack runtime supports only contiguous history: "
            f"saved={manifest.history.layout!r}, expected={expected.layout!r}"
        )
    return expected


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
    algorithm: str = "ppo",
    after_checkpoint: Callable[[int], None] | None = None,
) -> Any:
    """Create transition-adjusted checkpoint and deterministic evaluation hooks."""

    if isinstance(eval_seed, bool) or not isinstance(eval_seed, int) or eval_seed < 0:
        raise ValueError("eval_seed must be a non-negative integer")
    algorithm = _require_supported_algorithm(algorithm)
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
        name_prefix=f"mini_metro_{algorithm}",
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

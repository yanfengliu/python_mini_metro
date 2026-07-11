"""Algorithm contracts plus Stable-Baselines model construction and loading."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rl.dependencies import require_rl_dependencies

DEFAULT_ALGORITHM = "recurrent_ppo"
SUPPORTED_ALGORITHMS = ("ppo", DEFAULT_ALGORITHM)
DEFAULT_FRAME_STACK = 8
DEFAULT_FEATURES_DIM = 256
DEFAULT_LSTM_HIDDEN_SIZE = 256
DEFAULT_N_LSTM_LAYERS = 1
DEFAULT_RECURRENT_BATCH_SIZE = 64
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
RECURRENT_PPO_DEFAULTS: Mapping[str, int | float] = MappingProxyType(
    {
        **PPO_DEFAULTS,
        "gamma": 1.0,
        "gae_lambda": 0.99,
    }
)


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


def _require_supported_algorithm(algorithm: str) -> str:
    if algorithm not in SUPPORTED_ALGORITHMS:
        supported = ", ".join(SUPPORTED_ALGORITHMS)
        raise ValueError(
            f"unsupported algorithm {algorithm!r}; expected one of: {supported}"
        )
    return algorithm


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


def model_manifest_hyperparameters(
    algorithm: str,
    *,
    n_envs: int,
    n_steps: int | None = None,
    n_epochs: int | None = None,
    learning_rate: float | None = None,
    gamma: float | None = None,
    gae_lambda: float | None = None,
    clip_range: float | None = None,
    ent_coef: float | None = None,
    vf_coef: float | None = None,
    max_grad_norm: float | None = None,
    features_dim: int = DEFAULT_FEATURES_DIM,
) -> dict[str, int | float | str]:
    """Record the exact policy and optimizer contract for one algorithm."""

    algorithm = _require_supported_algorithm(algorithm)
    defaults = PPO_DEFAULTS if algorithm == "ppo" else RECURRENT_PPO_DEFAULTS
    hyperparameters = ppo_manifest_hyperparameters(
        n_envs=n_envs,
        n_steps=(int(defaults["n_steps"]) if n_steps is None else n_steps),
        n_epochs=(int(defaults["n_epochs"]) if n_epochs is None else n_epochs),
        learning_rate=(
            float(defaults["learning_rate"]) if learning_rate is None else learning_rate
        ),
        gamma=float(defaults["gamma"]) if gamma is None else gamma,
        gae_lambda=(
            float(defaults["gae_lambda"]) if gae_lambda is None else gae_lambda
        ),
        clip_range=(
            float(defaults["clip_range"]) if clip_range is None else clip_range
        ),
        ent_coef=float(defaults["ent_coef"]) if ent_coef is None else ent_coef,
        vf_coef=float(defaults["vf_coef"]) if vf_coef is None else vf_coef,
        max_grad_norm=(
            float(defaults["max_grad_norm"]) if max_grad_norm is None else max_grad_norm
        ),
        features_dim=features_dim,
    )
    if algorithm == DEFAULT_ALGORITHM:
        hyperparameters.update(
            {
                "batch_size": adjusted_batch_size(
                    int(n_envs) * int(hyperparameters["n_steps"]),
                    preferred=DEFAULT_RECURRENT_BATCH_SIZE,
                ),
                "enable_critic_lstm": True,
                "lstm_hidden_size": DEFAULT_LSTM_HIDDEN_SIZE,
                "n_lstm_layers": DEFAULT_N_LSTM_LAYERS,
                "policy": "CnnLstmPolicy",
                "shared_lstm": False,
            }
        )
    return hyperparameters


@dataclass(frozen=True, slots=True)
class LinearSchedule:
    initial_value: float

    def __call__(self, progress_remaining: float) -> float:
        return self.initial_value * float(progress_remaining)


def make_model(
    env: Any,
    *,
    algorithm: str = DEFAULT_ALGORITHM,
    seed: int,
    n_envs: int,
    device: str = "auto",
    tensorboard_log: str | Path | None = None,
    verbose: int = 0,
    n_steps: int | None = None,
    n_epochs: int | None = None,
    learning_rate: float | None = None,
    gamma: float | None = None,
    gae_lambda: float | None = None,
    clip_range: float | None = None,
    ent_coef: float | None = None,
    vf_coef: float | None = None,
    max_grad_norm: float | None = None,
    features_dim: int = DEFAULT_FEATURES_DIM,
) -> Any:
    algorithm = _require_supported_algorithm(algorithm)
    components = require_rl_dependencies()
    from rl.model import MiniMetroCNN

    hyperparameters = model_manifest_hyperparameters(
        algorithm,
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
    policy_kwargs: dict[str, Any] = {
        "features_extractor_class": MiniMetroCNN,
        "features_extractor_kwargs": {
            "features_dim": int(hyperparameters["features_dim"])
        },
    }
    if algorithm == DEFAULT_ALGORITHM:
        policy_kwargs.update(
            {
                "enable_critic_lstm": bool(hyperparameters["enable_critic_lstm"]),
                "lstm_hidden_size": int(hyperparameters["lstm_hidden_size"]),
                "n_lstm_layers": int(hyperparameters["n_lstm_layers"]),
                "shared_lstm": bool(hyperparameters["shared_lstm"]),
            }
        )
        model_class = components.sb3_contrib.RecurrentPPO
    else:
        model_class = components.stable_baselines3.PPO
    return model_class(
        str(hyperparameters["policy"]),
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
        policy_kwargs=policy_kwargs,
        seed=seed,
        device=device,
        tensorboard_log=(str(tensorboard_log) if tensorboard_log else None),
        verbose=verbose,
    )


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
    """Build the legacy feed-forward PPO policy."""

    return make_model(
        env,
        algorithm="ppo",
        seed=seed,
        n_envs=n_envs,
        device=device,
        tensorboard_log=tensorboard_log,
        verbose=verbose,
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


def load_model(
    source: Any,
    *,
    algorithm: str,
    env: Any,
    seed: int,
    device: str = "auto",
) -> Any:
    algorithm = _require_supported_algorithm(algorithm)
    components = require_rl_dependencies()
    model_class = (
        components.stable_baselines3.PPO
        if algorithm == "ppo"
        else components.sb3_contrib.RecurrentPPO
    )
    return model_class.load(
        source,
        env=env,
        device=device,
        seed=seed,
    )


def load_ppo_model(
    source: Any,
    *,
    env: Any,
    seed: int,
    device: str = "auto",
) -> Any:
    """Load the legacy feed-forward PPO artifact format."""

    return load_model(
        source,
        algorithm="ppo",
        env=env,
        seed=seed,
        device=device,
    )

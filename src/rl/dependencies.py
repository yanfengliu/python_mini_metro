"""Lazy imports for the optional reinforcement-learning dependency stack."""

from __future__ import annotations

import importlib
from functools import lru_cache
from types import SimpleNamespace
from typing import Any


@lru_cache(maxsize=1)
def require_rl_dependencies() -> SimpleNamespace:
    """Import the optional training stack or raise one actionable error."""

    module_names = {
        "gymnasium": "gymnasium",
        "sb3_contrib": "sb3_contrib",
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

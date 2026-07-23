"""Signature-tolerant draw dispatch shared by the game renderer.

``_call_flexibly`` filters keyword arguments to those a target draw method
actually declares, so the renderer can pass optional kwargs (``resources``,
``reduced_motion``, ``is_unassignment_queued``, ...) uniformly and each entity
draw receives only what its own signature supports.
"""

from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=128)
def _supported_keyword_names(method: Any) -> frozenset[str] | None:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return frozenset()
    if any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return None
    return frozenset(signature.parameters)


def _supported_kwargs(method: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    target = getattr(method, "__func__", method)
    try:
        supported = _supported_keyword_names(target)
    except TypeError:
        supported = frozenset(inspect.signature(method).parameters)
    if supported is None:
        return kwargs
    return {name: value for name, value in kwargs.items() if name in supported}


def _call_flexibly(method: Any, *args: Any, **kwargs: Any) -> Any:
    return method(*args, **_supported_kwargs(method, kwargs))

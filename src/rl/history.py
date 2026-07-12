"""Dependency-light identity for model-side temporal observation history."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

HISTORY_DESCRIPTOR_SCHEMA = "mini-metro-observation-history-v1"
CONTIGUOUS_HISTORY_LAYOUT = "contiguous-history-v1"
DECISION_HISTORY_LAYOUT = "decision-history-v1"
EIGHT_MULTISCALE_HISTORY_LAYOUT = "decision-history-8-control-v1"
TEN_MULTISCALE_HISTORY_LAYOUT = "decision-history-10-fallback-v1"

OFFSET_UNIT = "agent-decisions"
SAMPLE_ORDER = "oldest-to-newest"
CHANNEL_ORDER = "sample-major-channel-first-rgb"
PREHISTORY_FILL = "zeros"
RESET_BEHAVIOR = "clear-then-insert-initial"
TERMINAL_BEHAVIOR = "append-terminal-copy-before-autoreset"

_NAMED_OFFSETS = MappingProxyType(
    {
        DECISION_HISTORY_LAYOUT: (128, 64, 32, 16, 7, 6, 5, 4, 3, 2, 1, 0),
        EIGHT_MULTISCALE_HISTORY_LAYOUT: (128, 64, 32, 16, 3, 2, 1, 0),
        TEN_MULTISCALE_HISTORY_LAYOUT: (128, 64, 7, 6, 5, 4, 3, 2, 1, 0),
    }
)
_DESCRIPTOR_KEYS = {
    "channelOrder",
    "layout",
    "offsetUnit",
    "prehistoryFill",
    "resetBehavior",
    "sampleOffsets",
    "sampleOrder",
    "schema",
    "terminalBehavior",
}
_FIXED_FIELDS = {
    "channelOrder": CHANNEL_ORDER,
    "offsetUnit": OFFSET_UNIT,
    "prehistoryFill": PREHISTORY_FILL,
    "resetBehavior": RESET_BEHAVIOR,
    "sampleOrder": SAMPLE_ORDER,
    "schema": HISTORY_DESCRIPTOR_SCHEMA,
    "terminalBehavior": TERMINAL_BEHAVIOR,
}

__all__ = (
    "CHANNEL_ORDER",
    "CONTIGUOUS_HISTORY_LAYOUT",
    "DECISION_HISTORY_LAYOUT",
    "EIGHT_MULTISCALE_HISTORY_LAYOUT",
    "HISTORY_DESCRIPTOR_SCHEMA",
    "HistoryDescriptor",
    "OFFSET_UNIT",
    "PREHISTORY_FILL",
    "RESET_BEHAVIOR",
    "SAMPLE_ORDER",
    "TEN_MULTISCALE_HISTORY_LAYOUT",
    "TERMINAL_BEHAVIOR",
    "canonical_history_bytes",
    "contiguous_history",
    "history_for_layout",
)


def _require_exact_keys(document: Mapping[str, Any]) -> None:
    actual = set(document)
    if actual != _DESCRIPTOR_KEYS:
        missing = sorted(_DESCRIPTOR_KEYS - actual)
        unknown = sorted(actual - _DESCRIPTOR_KEYS)
        raise ValueError(
            f"invalid history descriptor keys: missing={missing}, unknown={unknown}"
        )


@dataclass(frozen=True, slots=True)
class HistoryDescriptor:
    """One exact interpretation of stacked single-frame observations."""

    layout: str
    offsets: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.layout, str) or not self.layout.strip():
            raise TypeError("history layout must be a non-empty string")
        offsets = tuple(self.offsets)
        if not offsets:
            raise ValueError("history offsets must not be empty")
        for offset in offsets:
            if isinstance(offset, bool) or not isinstance(offset, int):
                raise TypeError("history offsets must be integers")
            if offset < 0:
                raise ValueError("history offsets must be non-negative")
        if offsets[-1] != 0:
            raise ValueError("history offsets must end at zero")
        if any(older <= newer for older, newer in zip(offsets, offsets[1:])):
            raise ValueError("history offsets must be strictly oldest-to-newest")

        if self.layout == CONTIGUOUS_HISTORY_LAYOUT:
            expected = tuple(range(len(offsets) - 1, -1, -1))
        elif self.layout in _NAMED_OFFSETS:
            expected = _NAMED_OFFSETS[self.layout]
        else:
            raise ValueError(f"unsupported history layout: {self.layout!r}")
        if offsets != expected:
            raise ValueError(
                f"history offsets do not match layout {self.layout!r}: "
                f"expected={expected}, actual={offsets}"
            )
        object.__setattr__(self, "offsets", offsets)

    @property
    def frame_stack(self) -> int:
        return len(self.offsets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channelOrder": CHANNEL_ORDER,
            "layout": self.layout,
            "offsetUnit": OFFSET_UNIT,
            "prehistoryFill": PREHISTORY_FILL,
            "resetBehavior": RESET_BEHAVIOR,
            "sampleOffsets": list(self.offsets),
            "sampleOrder": SAMPLE_ORDER,
            "schema": HISTORY_DESCRIPTOR_SCHEMA,
            "terminalBehavior": TERMINAL_BEHAVIOR,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> HistoryDescriptor:
        if not isinstance(document, Mapping):
            raise TypeError("history descriptor must be an object")
        _require_exact_keys(document)
        for name, expected in _FIXED_FIELDS.items():
            if document[name] != expected:
                raise ValueError(
                    f"unsupported history {name}: "
                    f"expected={expected!r}, actual={document[name]!r}"
                )
        offsets = document["sampleOffsets"]
        if not isinstance(offsets, list):
            raise TypeError("history sampleOffsets must be an array")
        return cls(document["layout"], tuple(offsets))

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_history_bytes(self)).hexdigest()


def canonical_history_bytes(history: HistoryDescriptor) -> bytes:
    if not isinstance(history, HistoryDescriptor):
        raise TypeError("history must be a HistoryDescriptor")
    encoded = json.dumps(
        history.to_dict(),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{encoded}\n".encode("utf-8")


def contiguous_history(frame_stack: int) -> HistoryDescriptor:
    if isinstance(frame_stack, bool) or not isinstance(frame_stack, int):
        raise TypeError("frame_stack must be an integer")
    if frame_stack <= 0:
        raise ValueError("frame_stack must be positive")
    return HistoryDescriptor(
        CONTIGUOUS_HISTORY_LAYOUT,
        tuple(range(frame_stack - 1, -1, -1)),
    )


def history_for_layout(layout: str) -> HistoryDescriptor:
    if layout == CONTIGUOUS_HISTORY_LAYOUT:
        raise ValueError("contiguous history requires an explicit frame_stack")
    try:
        offsets = _NAMED_OFFSETS[layout]
    except (KeyError, TypeError) as error:
        raise ValueError(f"unsupported history layout: {layout!r}") from error
    return HistoryDescriptor(layout, offsets)

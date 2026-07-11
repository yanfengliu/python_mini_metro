"""Render-only interpolation snapshots for fixed-step metro movement."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable

from .layout import MetroPose, Position, VisualPath, project_metro_pose


@dataclass(frozen=True, slots=True)
class MetroSnapshot:
    metro_id: str
    path_id: str
    segment_index: int
    position: Position
    is_forward: bool
    is_stopped: bool


@dataclass(frozen=True, slots=True)
class _SnapshotPoint:
    left: float
    top: float


def _metro_id(metro: Any) -> str:
    return str(getattr(metro, "id", id(metro)))


def capture_metro(metro: Any) -> MetroSnapshot:
    position = metro.position
    return MetroSnapshot(
        metro_id=_metro_id(metro),
        path_id=str(getattr(metro, "path_id", "")),
        segment_index=int(metro.current_segment_idx),
        position=(float(position.left), float(position.top)),
        is_forward=bool(metro.is_forward),
        is_stopped=getattr(metro, "current_station", None) is not None,
    )


def _metros(source: Any) -> Iterable[Any]:
    return getattr(source, "metros", source)


def capture_metros(source: Any) -> dict[str, MetroSnapshot]:
    return {_metro_id(metro): capture_metro(metro) for metro in _metros(source)}


def interpolate_heading(start: float, end: float, alpha: float) -> float:
    """Interpolate angles over the shortest arc in degrees."""

    amount = max(0.0, min(1.0, float(alpha)))
    delta = (end - start + 180.0) % 360.0 - 180.0
    raw = start + delta * amount
    normalized = (raw + 180.0) % 360.0 - 180.0
    if normalized == -180.0 and raw > 0:
        return 180.0
    return normalized


def _snapshot_proxy(snapshot: MetroSnapshot) -> SimpleNamespace:
    return SimpleNamespace(
        current_segment_idx=snapshot.segment_index,
        position=_SnapshotPoint(*snapshot.position),
        is_forward=snapshot.is_forward,
        current_station=object() if snapshot.is_stopped else None,
    )


def _project_snapshot(
    path: Any, snapshot: MetroSnapshot, layout: VisualPath
) -> MetroPose:
    return project_metro_pose(path, _snapshot_proxy(snapshot), layout)


class MetroInterpolator:
    """Keep only the two render snapshots needed for frame interpolation."""

    def __init__(self) -> None:
        self._previous: dict[str, MetroSnapshot] = {}
        self._current: dict[str, MetroSnapshot] = {}

    def clear(self) -> None:
        self._previous = {}
        self._current = {}

    def before_step(self, source: Any) -> None:
        self._previous = capture_metros(source)

    def after_step(self, source: Any) -> None:
        self._current = capture_metros(source)
        if not self._previous:
            self._previous = dict(self._current)

    def pose_for(
        self,
        path: Any,
        metro: Any,
        layout: VisualPath,
        alpha: float,
    ) -> MetroPose:
        """Return an interpolated pose, falling back safely for new topology."""

        live_snapshot = capture_metro(metro)
        current_snapshot = self._current.get(live_snapshot.metro_id, live_snapshot)
        try:
            current_pose = _project_snapshot(path, current_snapshot, layout)
        except (IndexError, ValueError):
            current_snapshot = live_snapshot
            current_pose = _project_snapshot(path, current_snapshot, layout)
        previous_snapshot = self._previous.get(current_snapshot.metro_id)
        if (
            previous_snapshot is None
            or previous_snapshot.path_id != current_snapshot.path_id
        ):
            return current_pose
        try:
            previous_pose = _project_snapshot(path, previous_snapshot, layout)
        except (IndexError, ValueError):
            return current_pose

        amount = max(0.0, min(1.0, float(alpha)))
        position = (
            previous_pose.position[0]
            + (current_pose.position[0] - previous_pose.position[0]) * amount,
            previous_pose.position[1]
            + (current_pose.position[1] - previous_pose.position[1]) * amount,
        )
        return MetroPose(
            position=position,
            heading_degrees=interpolate_heading(
                previous_pose.heading_degrees,
                current_pose.heading_degrees,
                amount,
            ),
            logical_segment_index=current_pose.logical_segment_index,
            progress=(
                previous_pose.progress
                + (current_pose.progress - previous_pose.progress) * amount
            ),
            is_forward=current_pose.is_forward,
            is_stopped=current_pose.is_stopped,
        )

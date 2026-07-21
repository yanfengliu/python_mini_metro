"""Render-only interpolation snapshots for fixed-step metro movement."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any, Iterable

from .consist_layout import consist_layout
from .layout import MetroPose, Position, VisualPath, project_metro_pose
from .turnaround import is_terminal_turnaround, turnaround_positions


@dataclass(frozen=True, slots=True)
class MetroSnapshot:
    metro_id: str
    path_id: str
    segment_index: int
    segment: Any | None
    transition_key: tuple[Any, ...] | None
    position: Position
    is_forward: bool
    is_stopped: bool
    station: Any | None


@dataclass(frozen=True, slots=True)
class _SnapshotPoint:
    left: float
    top: float


def _metro_id(metro: Any) -> str:
    return str(getattr(metro, "id", id(metro)))


def _position(value: Any) -> Position:
    return (float(value.left), float(value.top))


def _is_path_segment(segment: Any) -> bool:
    return (
        getattr(segment, "start_station", None) is not None
        and getattr(segment, "end_station", None) is not None
    )


def _station_pair(segment: Any) -> tuple[int, int] | None:
    start = getattr(segment, "start_station", None)
    end = getattr(segment, "end_station", None)
    if start is None or end is None:
        return None
    return tuple(sorted((id(start), id(end))))


def _endpoint_pair(segment: Any) -> tuple[Position, Position] | None:
    try:
        return tuple(
            sorted(
                (
                    _position(segment.segment_start),
                    _position(segment.segment_end),
                )
            )
        )
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _nearest_path_segment(
    segments: tuple[Any, ...],
    start_index: int,
    step: int,
    is_looped: bool,
) -> Any | None:
    index = start_index + step
    for _ in segments:
        if not is_looped and not 0 <= index < len(segments):
            return None
        index %= len(segments)
        segment = segments[index]
        if _is_path_segment(segment):
            return segment
        index += step
    return None


def _transition_key(
    path: Any | None,
    segment_index: int,
    segment: Any | None,
) -> tuple[Any, ...] | None:
    if path is None or segment is None:
        return None
    try:
        segments = tuple(path.segments)
    except (AttributeError, TypeError):
        return None
    if not 0 <= segment_index < len(segments) or segments[segment_index] is not segment:
        return None
    endpoints = _endpoint_pair(segment)
    if endpoints is None:
        return None
    if _is_path_segment(segment):
        stations = _station_pair(segment)
        return None if stations is None else ("path", stations, endpoints)

    is_looped = bool(getattr(path, "is_looped", False))
    previous = _nearest_path_segment(segments, segment_index, -1, is_looped)
    following = _nearest_path_segment(segments, segment_index, 1, is_looped)
    if previous is None or following is None:
        return None
    previous_pair = _station_pair(previous)
    following_pair = _station_pair(following)
    if previous_pair is None or following_pair is None:
        return None
    adjacency = tuple(sorted((previous_pair, following_pair)))
    return ("padding", adjacency, endpoints)


def _segment_for(metro: Any, path: Any | None, segment_index: int) -> Any | None:
    missing = object()
    segment = getattr(metro, "current_segment", missing)
    if segment is not missing:
        return segment
    if path is None:
        return None
    try:
        segments = tuple(path.segments)
    except (AttributeError, TypeError):
        return None
    if 0 <= segment_index < len(segments):
        return segments[segment_index]
    return None


def capture_metro(metro: Any, path: Any | None = None) -> MetroSnapshot:
    position = metro.position
    segment_index = int(metro.current_segment_idx)
    segment = _segment_for(metro, path, segment_index)
    return MetroSnapshot(
        metro_id=_metro_id(metro),
        path_id=str(getattr(metro, "path_id", "")),
        segment_index=segment_index,
        segment=segment,
        transition_key=_transition_key(path, segment_index, segment),
        position=(float(position.left), float(position.top)),
        is_forward=bool(metro.is_forward),
        is_stopped=getattr(metro, "current_station", None) is not None,
        station=getattr(metro, "current_station", None),
    )


def _metros(source: Any) -> Iterable[Any]:
    return getattr(source, "metros", source)


def _paths(source: Any) -> tuple[Any, ...]:
    values = getattr(source, "paths", None)
    if values is not None:
        try:
            return tuple(values)
        except TypeError:
            return ()
    if hasattr(source, "segments") and hasattr(source, "metros"):
        return (source,)
    return ()


def _containing_path(metro: Any, paths: tuple[Any, ...]) -> Any | None:
    owners = [
        path
        for path in paths
        if any(item is metro for item in getattr(path, "metros", ()))
    ]
    if len(owners) == 1:
        return owners[0]
    return None


def capture_metros(source: Any) -> dict[str, MetroSnapshot]:
    paths = _paths(source)
    return {
        _metro_id(metro): capture_metro(metro, _containing_path(metro, paths))
        for metro in _metros(source)
    }


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
        current_station=snapshot.station,
    )


def _project_snapshot(
    path: Any, snapshot: MetroSnapshot, layout: VisualPath
) -> MetroPose:
    return project_metro_pose(path, _snapshot_proxy(snapshot), layout)


def _matches_live_path(path: Any, snapshot: MetroSnapshot) -> bool:
    try:
        segments = tuple(path.segments)
    except (AttributeError, TypeError):
        return False
    return (
        str(getattr(path, "id", id(path))) == snapshot.path_id
        and snapshot.segment is not None
        and 0 <= snapshot.segment_index < len(segments)
        and segments[snapshot.segment_index] is snapshot.segment
    )


def _bind_snapshot(
    snapshot: MetroSnapshot,
    live: MetroSnapshot,
    direction_flip: bool,
) -> MetroSnapshot:
    return replace(
        snapshot,
        segment_index=live.segment_index,
        segment=live.segment,
        transition_key=live.transition_key,
        is_forward=snapshot.is_forward ^ direction_flip,
    )


def _rebase_snapshots(
    previous: MetroSnapshot | None,
    current: MetroSnapshot,
    live: MetroSnapshot,
) -> tuple[MetroSnapshot, MetroSnapshot] | None:
    if (
        previous is None
        or previous.path_id != current.path_id
        or current.path_id != live.path_id
        or current.position != live.position
        or current.is_stopped != live.is_stopped
        or current.station is not live.station
        or current.segment is None
        or previous.segment is not current.segment
        or current.transition_key is None
        or previous.transition_key != current.transition_key
        or live.transition_key != current.transition_key
    ):
        return None
    direction_flip = current.is_forward != live.is_forward
    return (
        _bind_snapshot(previous, live, direction_flip),
        _bind_snapshot(current, live, direction_flip),
    )


def _rebase_unbound_legacy_snapshots(
    previous: MetroSnapshot | None,
    current: MetroSnapshot,
    live: MetroSnapshot,
) -> tuple[MetroSnapshot, MetroSnapshot] | None:
    """Keep incomplete legacy renderer doubles working without weakening real hosts."""

    if (
        previous is None
        or previous.segment is not None
        or current.segment is not None
        or previous.path_id != current.path_id
        or current.path_id != live.path_id
        or previous.segment_index != live.segment_index
        or current.segment_index != live.segment_index
        or current.position != live.position
    ):
        return None
    direction_flip = current.is_forward != live.is_forward
    return (
        _bind_snapshot(previous, live, direction_flip),
        _bind_snapshot(current, live, direction_flip),
    )


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

    def _resolved_snapshots(
        self,
        path: Any,
        metro: Any,
    ) -> tuple[MetroSnapshot | None, MetroSnapshot]:
        live_snapshot = capture_metro(metro, path)
        cached_current = self._current.get(live_snapshot.metro_id)
        previous_snapshot = self._previous.get(live_snapshot.metro_id)
        if cached_current is None:
            current_snapshot = live_snapshot
        elif _matches_live_path(path, cached_current):
            current_snapshot = cached_current
        else:
            rebased = _rebase_snapshots(
                previous_snapshot,
                cached_current,
                live_snapshot,
            )
            if rebased is None and not hasattr(metro, "current_segment"):
                rebased = _rebase_unbound_legacy_snapshots(
                    previous_snapshot,
                    cached_current,
                    live_snapshot,
                )
            if rebased is None:
                return None, live_snapshot
            previous_snapshot, current_snapshot = rebased

        if (
            previous_snapshot is None
            or previous_snapshot.path_id != current_snapshot.path_id
            or not _matches_live_path(path, previous_snapshot)
        ):
            previous_snapshot = None
        return previous_snapshot, current_snapshot

    @staticmethod
    def _interpolate_pose(
        previous: MetroPose,
        current: MetroPose,
        alpha: float,
    ) -> MetroPose:
        amount = max(0.0, min(1.0, float(alpha)))
        position = (
            previous.position[0]
            + (current.position[0] - previous.position[0]) * amount,
            previous.position[1]
            + (current.position[1] - previous.position[1]) * amount,
        )
        return replace(
            current,
            position=position,
            heading_degrees=interpolate_heading(
                previous.heading_degrees,
                current.heading_degrees,
                amount,
            ),
            progress=previous.progress
            + (current.progress - previous.progress) * amount,
        )

    def pose_for(
        self,
        path: Any,
        metro: Any,
        layout: VisualPath,
        alpha: float,
    ) -> MetroPose:
        """Return an interpolated pose, falling back safely for new topology."""

        previous_snapshot, current_snapshot = self._resolved_snapshots(path, metro)
        current_pose = _project_snapshot(path, current_snapshot, layout)
        if previous_snapshot is None:
            return current_pose
        previous_pose = _project_snapshot(path, previous_snapshot, layout)
        return self._interpolate_pose(previous_pose, current_pose, alpha)

    @staticmethod
    def _spacing() -> float:
        import config

        return float(MetroInterpolator._body_length() + config.carriage_gap)

    @staticmethod
    def _body_length() -> float:
        import config

        return float(
            getattr(
                config,
                "carriage_body_length",
                2 * config.carriage_size,
            )
        )

    @staticmethod
    def _interpolate_consists(
        previous: tuple[MetroPose, ...],
        current: tuple[MetroPose, ...],
        alpha: float,
    ) -> tuple[MetroPose, ...]:
        amount = max(0.0, min(1.0, float(alpha)))
        if amount <= 0.0:
            return previous
        if amount >= 1.0:
            return current
        return tuple(
            MetroInterpolator._interpolate_pose(before, after, amount)
            for before, after in zip(previous, current)
        )

    def poses_for_consist(
        self,
        path: Any,
        metro: Any,
        layout: VisualPath,
        alpha: float,
        spacing: float | None = None,
    ) -> tuple[MetroPose, ...]:
        """Sample carriage poses from coherent interpolation endpoints."""

        count = len(getattr(metro, "carriages", ()))
        if count == 0:
            return ()
        gap = self._spacing() if spacing is None else float(spacing)
        previous_snapshot, current_snapshot = self._resolved_snapshots(path, metro)
        current_head = _project_snapshot(path, current_snapshot, layout)
        current = consist_layout(layout, current_head, count, gap)
        if previous_snapshot is None:
            return current
        previous_head = _project_snapshot(path, previous_snapshot, layout)
        previous = consist_layout(layout, previous_head, count, gap)
        if not is_terminal_turnaround(
            path,
            previous_snapshot,
            current_snapshot,
        ):
            return self._interpolate_consists(previous, current, alpha)

        amount = max(0.0, min(1.0, float(alpha)))
        if amount <= 0.0:
            return previous
        if amount >= 1.0:
            return current
        head = self._interpolate_pose(previous_head, current_head, amount)
        heading_delta = (
            current_head.heading_degrees - previous_head.heading_degrees + 180.0
        ) % 360.0 - 180.0
        positions = turnaround_positions(
            previous_head.position,
            current_head.position,
            head.position,
            (pose.position for pose in previous),
            (pose.position for pose in current),
            amount,
            heading_delta,
            self._body_length(),
        )
        return tuple(
            replace(
                after,
                position=position,
                heading_degrees=interpolate_heading(
                    before.heading_degrees,
                    after.heading_degrees,
                    amount,
                ),
            )
            for position, before, after in zip(
                positions,
                previous,
                current,
            )
        )

    consist_poses_for = poses_for_consist
    sample_consist = poses_for_consist

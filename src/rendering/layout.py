"""Immutable route geometry derived from mutable game entities.

This module intentionally uses plain numeric tuples instead of gameplay geometry
classes.  Constructing a visual layout must never allocate entity IDs or mutate
the simulation objects it describes.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

Position = tuple[float, float]
SegmentKind = Literal["path", "padding"]


@dataclass(frozen=True, slots=True)
class VisualSegment:
    """One immutable visual counterpart for one logical path segment."""

    logical_index: int
    kind: SegmentKind
    start: Position
    end: Position
    start_station_id: str | None = None
    end_station_id: str | None = None


@dataclass(frozen=True, slots=True)
class VisualPath:
    """The visual lane occupied by a logical path."""

    path_id: str
    color: tuple[int, int, int]
    order: float
    is_looped: bool
    segments: tuple[VisualSegment, ...]


@dataclass(frozen=True, slots=True)
class MetroPose:
    """A visual metro position and heading without modifying the metro."""

    position: Position
    heading_degrees: float
    logical_segment_index: int
    progress: float
    is_forward: bool
    is_stopped: bool


def centered_path_orders(count: int) -> tuple[float, ...]:
    """Return symmetric lane slots centered exactly around zero."""

    if count < 0:
        raise ValueError("path count cannot be negative")
    midpoint = (count - 1) / 2
    return tuple(index - midpoint for index in range(count))


def _position(value: Any) -> Position:
    if isinstance(value, tuple) and len(value) == 2:
        return (float(value[0]), float(value[1]))
    return (float(value.left), float(value.top))


def _station_id(station: Any | None) -> str | None:
    if station is None:
        return None
    return str(getattr(station, "id", id(station)))


def _is_path_segment(segment: Any) -> bool:
    return (
        getattr(segment, "start_station", None) is not None
        and getattr(segment, "end_station", None) is not None
    )


def _canonical_normal(start: Position, end: Position) -> Position:
    """Return one stable normal for either direction of a station pair."""

    canonical_start, canonical_end = sorted((start, end))
    dx = canonical_end[0] - canonical_start[0]
    dy = canonical_end[1] - canonical_start[1]
    magnitude = math.hypot(dx, dy)
    if magnitude == 0:
        return (0.0, 0.0)
    return (-dy / magnitude, dx / magnitude)


def _offset_pair(
    start: Position,
    end: Position,
    order: float,
    lane_spacing: float,
) -> tuple[Position, Position]:
    normal_x, normal_y = _canonical_normal(start, end)
    shift = order * lane_spacing
    offset = (normal_x * shift, normal_y * shift)
    return (
        (start[0] + offset[0], start[1] + offset[1]),
        (end[0] + offset[0], end[1] + offset[1]),
    )


def _nearest_path_index(
    segments: list[Any],
    start_index: int,
    step: int,
    is_looped: bool,
) -> int | None:
    count = len(segments)
    if count == 0:
        return None
    index = start_index + step
    inspected = 0
    while inspected < count:
        if not is_looped and not 0 <= index < count:
            return None
        index %= count
        if _is_path_segment(segments[index]):
            return index
        index += step
        inspected += 1
    return None


def build_visual_path(
    path: Any,
    order: float,
    lane_spacing: float,
) -> VisualPath:
    """Build an immutable lane layout without rebuilding logical segments."""

    if lane_spacing < 0:
        raise ValueError("lane spacing cannot be negative")
    logical_segments = list(getattr(path, "segments", ()))
    is_looped = bool(getattr(path, "is_looped", False))
    visual_segments: list[VisualSegment | None] = [None] * len(logical_segments)

    for index, logical in enumerate(logical_segments):
        if not _is_path_segment(logical):
            continue
        start_station = logical.start_station
        end_station = logical.end_station
        start = _position(start_station.position)
        end = _position(end_station.position)
        visual_start, visual_end = _offset_pair(
            start, end, float(order), float(lane_spacing)
        )
        visual_segments[index] = VisualSegment(
            logical_index=index,
            kind="path",
            start=visual_start,
            end=visual_end,
            start_station_id=_station_id(start_station),
            end_station_id=_station_id(end_station),
        )

    for index, logical in enumerate(logical_segments):
        if visual_segments[index] is not None:
            continue
        previous_index = _nearest_path_index(logical_segments, index, -1, is_looped)
        next_index = _nearest_path_index(logical_segments, index, 1, is_looped)
        previous = (
            visual_segments[previous_index] if previous_index is not None else None
        )
        following = visual_segments[next_index] if next_index is not None else None
        raw_start = _position(logical.segment_start)
        raw_end = _position(logical.segment_end)
        visual_segments[index] = VisualSegment(
            logical_index=index,
            kind="padding",
            start=previous.end if previous is not None else raw_start,
            end=following.start if following is not None else raw_end,
        )

    return VisualPath(
        path_id=str(getattr(path, "id", id(path))),
        color=tuple(int(channel) for channel in path.color),
        order=float(order),
        is_looped=is_looped,
        segments=tuple(segment for segment in visual_segments if segment is not None),
    )


def build_preview_visual_path(
    *,
    path_id: str,
    color: Sequence[int],
    stations: Sequence[Any],
    order: float,
    lane_spacing: float,
    loop: bool,
    temp_point: Any | None = None,
    temp_insertion_index: int | None = None,
) -> VisualPath:
    """Build an immutable off-live route preview from station positions."""

    if lane_spacing < 0:
        raise ValueError("lane spacing cannot be negative")
    station_values = tuple(
        (_station_id(station), _position(station.position)) for station in stations
    )
    preview_values = station_values
    if temp_insertion_index is not None:
        if not 0 <= temp_insertion_index <= len(station_values):
            raise ValueError("temporary insertion index is outside the route")
        if temp_point is not None:
            pointer = (None, _position(temp_point))
            preview_values = (
                *station_values[:temp_insertion_index],
                pointer,
                *station_values[temp_insertion_index:],
            )

    edges: list[tuple[tuple[str | None, Position], tuple[str | None, Position]]] = [
        (start, end) for start, end in zip(preview_values, preview_values[1:])
    ]
    is_looped = bool(loop and len(preview_values) >= 2)
    if is_looped:
        edges.append((preview_values[-1], preview_values[0]))
    elif temp_insertion_index is None and station_values and temp_point is not None:
        pointer_position = _position(temp_point)
        if pointer_position != station_values[-1][1]:
            edges.append((station_values[-1], (None, pointer_position)))

    path_segments: list[VisualSegment] = []
    for start, end in edges:
        visual_start, visual_end = _offset_pair(
            start[1], end[1], float(order), float(lane_spacing)
        )
        path_segments.append(
            VisualSegment(
                logical_index=0,
                kind="path",
                start=visual_start,
                end=visual_end,
                start_station_id=start[0],
                end_station_id=end[0],
            )
        )

    segments: list[VisualSegment] = []
    for segment in path_segments:
        if segments:
            segments.append(
                VisualSegment(
                    logical_index=len(segments),
                    kind="padding",
                    start=segments[-1].end,
                    end=segment.start,
                )
            )
        segments.append(
            VisualSegment(
                logical_index=len(segments),
                kind="path",
                start=segment.start,
                end=segment.end,
                start_station_id=segment.start_station_id,
                end_station_id=segment.end_station_id,
            )
        )
    if is_looped and segments:
        segments.append(
            VisualSegment(
                logical_index=len(segments),
                kind="padding",
                start=segments[-1].end,
                end=segments[0].start,
            )
        )

    return VisualPath(
        path_id=str(path_id),
        color=tuple(int(channel) for channel in color),
        order=float(order),
        is_looped=is_looped,
        segments=tuple(segments),
    )


def _project_progress(position: Position, start: Position, end: Position) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-12:
        return math.nan
    projected = (
        (position[0] - start[0]) * dx + (position[1] - start[1]) * dy
    ) / length_squared
    return max(0.0, min(1.0, projected))


def _heading_for_segment(
    visual_path: VisualPath,
    segment_index: int,
    is_forward: bool,
) -> float:
    count = len(visual_path.segments)
    step = 1 if is_forward else -1
    index = segment_index
    for _ in range(count):
        segment = visual_path.segments[index]
        dx = segment.end[0] - segment.start[0]
        dy = segment.end[1] - segment.start[1]
        if not is_forward:
            dx = -dx
            dy = -dy
        if abs(dx) > 1e-12 or abs(dy) > 1e-12:
            heading = math.degrees(math.atan2(dy, dx))
            return 180.0 if math.isclose(heading, -180.0) else heading
        index += step
        if visual_path.is_looped:
            index %= count
        elif not 0 <= index < count:
            break
    return 0.0


def project_metro_pose(path: Any, metro: Any, visual_path: VisualPath) -> MetroPose:
    """Project a logical metro onto its immutable visual lane."""

    logical_segments = tuple(getattr(path, "segments", ()))
    if len(logical_segments) != len(visual_path.segments):
        raise ValueError("logical and visual segment counts differ")
    if not logical_segments:
        raise ValueError("cannot project a metro on an empty path")

    segment_index = int(metro.current_segment_idx)
    if not 0 <= segment_index < len(logical_segments):
        raise IndexError("metro segment index is outside the path")
    logical = logical_segments[segment_index]
    visual = visual_path.segments[segment_index]
    is_forward = bool(metro.is_forward)
    is_stopped = getattr(metro, "current_station", None) is not None

    if visual.kind == "padding" and is_stopped:
        progress = 0.0 if is_forward else 1.0
    else:
        logical_progress = _project_progress(
            _position(metro.position),
            _position(logical.segment_start),
            _position(logical.segment_end),
        )
        progress = (
            (0.0 if is_forward else 1.0)
            if math.isnan(logical_progress)
            else logical_progress
        )

    position = (
        visual.start[0] + (visual.end[0] - visual.start[0]) * progress,
        visual.start[1] + (visual.end[1] - visual.start[1]) * progress,
    )
    return MetroPose(
        position=position,
        heading_degrees=_heading_for_segment(visual_path, segment_index, is_forward),
        logical_segment_index=segment_index,
        progress=progress,
        is_forward=is_forward,
        is_stopped=is_stopped,
    )

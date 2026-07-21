"""Pure carriage-center layout over one coherent projected metro pose."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .layout import MetroPose, Position, VisualPath, VisualSegment

_EPSILON = 1e-12


def _vector(segment: VisualSegment) -> tuple[float, float, float]:
    dx = segment.end[0] - segment.start[0]
    dy = segment.end[1] - segment.start[1]
    length = math.hypot(dx, dy)
    return dx, dy, length


def _heading(segment: VisualSegment, is_forward: bool, fallback: float) -> float:
    dx, dy, length = _vector(segment)
    if length <= _EPSILON:
        return fallback
    if not is_forward:
        dx = -dx
        dy = -dy
    value = math.degrees(math.atan2(dy, dx))
    return 180.0 if math.isclose(value, -180.0) else value


def _straight_fallback(head: MetroPose, distance: float) -> MetroPose:
    heading = head.heading_degrees if math.isfinite(head.heading_degrees) else 0.0
    radians = math.radians(heading)
    position = (
        head.position[0] - math.cos(radians) * distance,
        head.position[1] - math.sin(radians) * distance,
    )
    return replace(head, position=position, heading_degrees=heading)


def _segment_index(path: VisualPath, logical_index: int) -> int | None:
    return next(
        (
            index
            for index, segment in enumerate(path.segments)
            if segment.logical_index == logical_index
        ),
        None,
    )


def _next_index(path: VisualPath, index: int, step: int) -> int | None:
    candidate = index + step
    if path.is_looped and path.segments:
        return candidate % len(path.segments)
    return candidate if 0 <= candidate < len(path.segments) else None


def _terminal_tangent(
    path: VisualPath,
    *,
    from_start: bool,
) -> tuple[float, float] | None:
    segments = path.segments if from_start else tuple(reversed(path.segments))
    for segment in segments:
        dx, dy, length = _vector(segment)
        if length > _EPSILON:
            return (dx / length, dy / length)
    return None


def _pose(
    segment: VisualSegment,
    position: Position,
    progress: float,
    head: MetroPose,
) -> MetroPose:
    return MetroPose(
        position=position,
        heading_degrees=_heading(
            segment,
            head.is_forward,
            head.heading_degrees,
        ),
        logical_segment_index=segment.logical_index,
        progress=max(0.0, min(1.0, progress)),
        is_forward=head.is_forward,
        is_stopped=head.is_stopped,
    )


def _walk(path: VisualPath, head: MetroPose, distance: float) -> MetroPose:
    total_length = sum(_vector(segment)[2] for segment in path.segments)
    if total_length <= _EPSILON:
        return _straight_fallback(head, distance)
    if path.is_looped:
        distance %= total_length
        if distance <= _EPSILON:
            return replace(head)

    index = _segment_index(path, head.logical_segment_index)
    if index is None:
        return _straight_fallback(head, distance)
    step = -1 if head.is_forward else 1
    position = head.position
    progress = max(0.0, min(1.0, float(head.progress)))
    remaining = distance

    while True:
        segment = path.segments[index]
        dx, dy, length = _vector(segment)
        available = length * (progress if step < 0 else 1.0 - progress)
        if length > _EPSILON and remaining < available - _EPSILON:
            direction = -1.0 if step < 0 else 1.0
            unit_x, unit_y = dx / length, dy / length
            position = (
                position[0] + direction * unit_x * remaining,
                position[1] + direction * unit_y * remaining,
            )
            progress += direction * remaining / length
            return _pose(segment, position, progress, head)

        remaining = max(0.0, remaining - available)
        position = segment.start if step < 0 else segment.end
        next_index = _next_index(path, index, step)
        if next_index is None:
            tangent = _terminal_tangent(path, from_start=step < 0)
            if tangent is None:
                return _straight_fallback(head, distance)
            direction = -1.0 if step < 0 else 1.0
            terminal_position = (
                position[0] + direction * tangent[0] * remaining,
                position[1] + direction * tangent[1] * remaining,
            )
            return _pose(
                segment,
                terminal_position,
                0.0 if step < 0 else 1.0,
                head,
            )

        index = next_index
        progress = 1.0 if step < 0 else 0.0
        adjoining = path.segments[index]
        position = adjoining.end if step < 0 else adjoining.start
        if remaining <= _EPSILON:
            return _pose(adjoining, position, progress, head)


def consist_layout(
    visual_path: VisualPath,
    head_pose: MetroPose,
    carriage_count: int,
    spacing: float,
) -> tuple[MetroPose, ...]:
    """Place ordered carriage centers behind one coherent locomotive pose."""

    if type(carriage_count) is not int or carriage_count < 0:
        raise ValueError("carriage count must be a nonnegative integer")
    distance = float(spacing)
    if not math.isfinite(distance) or distance < 0.0:
        raise ValueError("carriage spacing must be finite and nonnegative")
    return tuple(
        _walk(visual_path, head_pose, distance * ordinal)
        for ordinal in range(1, carriage_count + 1)
    )


def consist_passenger_slices(metro: Any) -> tuple[tuple[Any, tuple[Any, ...]], ...]:
    """Pair each consist body with its canonical ordered passenger slice."""

    passengers = tuple(getattr(metro, "passengers", ()))
    carriages = tuple(getattr(metro, "carriages", ()))
    carriage_capacity = sum(
        int(getattr(carriage, "capacity", 0)) for carriage in carriages
    )
    base_capacity = int(
        getattr(
            metro,
            "_base_capacity",
            max(0, int(getattr(metro, "capacity", 0)) - carriage_capacity),
        )
    )
    result = []
    start = 0
    for body, capacity in (
        (metro, base_capacity),
        *((carriage, int(getattr(carriage, "capacity", 0))) for carriage in carriages),
    ):
        result.append((body, passengers[start : start + capacity]))
        start += capacity
    return tuple(result)


__all__ = ["consist_layout", "consist_passenger_slices"]

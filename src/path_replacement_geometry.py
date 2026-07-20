"""Structural geometry validation for atomic path replacement."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

_TOLERANCE = 1e-6


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=_TOLERANCE)


def _point(value: Any) -> tuple[float, float]:
    coordinates = (value.left, value.top)
    if any(
        isinstance(item, bool) or not isinstance(item, Real) for item in coordinates
    ):
        raise ValueError("non-numeric geometry")
    result = (float(coordinates[0]), float(coordinates[1]))
    if not all(math.isfinite(item) for item in result):
        raise ValueError("non-finite geometry")
    return result


def is_canonical_point(value: Any) -> bool:
    try:
        _point(value)
    except (AttributeError, OverflowError, TypeError, ValueError):
        return False
    return True


def _same_identity_sequence(actual: Any, expected: Any) -> bool:
    actual_items = tuple(actual)
    expected_items = tuple(expected)
    return len(actual_items) == len(expected_items) and all(
        left is right for left, right in zip(actual_items, expected_items)
    )


def _identity_unique(values: Any) -> bool:
    items = tuple(values)
    return len({id(item) for item in items}) == len(items)


def _expected_offset(
    start: tuple[float, float],
    end: tuple[float, float],
    order: int,
    lane_spacing: float,
) -> tuple[float, float]:
    canonical_start, canonical_end = sorted((start, end))
    dx = canonical_end[0] - canonical_start[0]
    dy = canonical_end[1] - canonical_start[1]
    magnitude = math.hypot(dx, dy)
    if magnitude == 0:
        return (0.0, 0.0)
    buffer_x = dx / magnitude * lane_spacing
    buffer_y = dy / magnitude * lane_spacing
    radians = math.radians(90)
    sine = math.sin(radians)
    cosine = math.cos(radians)
    rotated_x = round(cosine * buffer_x - sine * buffer_y)
    rotated_y = round(sine * buffer_x + cosine * buffer_y)
    return (rotated_x * order, rotated_y * order)


def _line_is_consistent(segment: Any, color: Any, stroke_width: int) -> bool:
    line = segment.line
    return (
        segment.color == color
        and line.color == color
        and type(line.width) is int
        and line.width == stroke_width
        and line.start is segment.segment_start
        and line.end is segment.segment_end
    )


def validate_path_geometry(
    path: Any,
    stations: list[Any],
    loop: bool,
    *,
    lane_spacing: int | float,
    stroke_width: int,
) -> bool:
    """Validate one complete path against canonical rounded geometry."""

    try:
        if (
            not isinstance(path.stations, list)
            or not isinstance(path.segments, list)
            or not isinstance(path.path_segments, list)
            or not isinstance(path.padding_segments, list)
            or path.is_looped is not loop
            or type(path.path_order) is not int
            or isinstance(lane_spacing, bool)
            or not isinstance(lane_spacing, (int, float))
            or not math.isfinite(lane_spacing)
            or lane_spacing < 0
            or type(stroke_width) is not int
            or stroke_width <= 0
            or not _same_identity_sequence(path.stations, stations)
        ):
            return False

        path_count = len(stations) if loop else len(stations) - 1
        padding_count = path_count if loop else max(0, path_count - 1)
        path_segments = tuple(path.path_segments)
        padding_segments = tuple(path.padding_segments)
        path_endpoints = tuple(
            point
            for segment in path_segments
            for point in (segment.segment_start, segment.segment_end)
        )
        station_position_ids = {id(station.position) for station in stations}
        if (
            len(path_segments) != path_count
            or len(padding_segments) != padding_count
            or len(path.segments) != path_count + padding_count
            or not _identity_unique(path_segments)
            or not _identity_unique(padding_segments)
            or {id(item) for item in path_segments}
            & {id(item) for item in padding_segments}
            or not _identity_unique(path_endpoints)
            or any(id(point) in station_position_ids for point in path_endpoints)
            or not _identity_unique(segment.line for segment in path.segments)
        ):
            return False

        expected_segments = []
        for index, segment in enumerate(path_segments):
            start_station = stations[index]
            end_station = stations[(index + 1) % len(stations)]
            if (
                segment.start_station is not start_station
                or segment.end_station is not end_station
                or type(segment.path_order) is not int
                or segment.path_order != path.path_order
            ):
                return False
            start = _point(start_station.position)
            end = _point(end_station.position)
            segment_start = _point(segment.segment_start)
            segment_end = _point(segment.segment_end)
            offset = _expected_offset(start, end, path.path_order, float(lane_spacing))
            if not all(
                _close(actual, expected)
                for actual, expected in (
                    (segment_start[0], start[0] + offset[0]),
                    (segment_start[1], start[1] + offset[1]),
                    (segment_end[0], end[0] + offset[0]),
                    (segment_end[1], end[1] + offset[1]),
                )
            ) or not _line_is_consistent(segment, path.color, stroke_width):
                return False
            expected_segments.append(segment)
            if index < padding_count:
                expected_segments.append(padding_segments[index])

        for index, segment in enumerate(padding_segments):
            previous = path_segments[index]
            following = path_segments[(index + 1) % path_count]
            if (
                segment.start_station is not None
                or segment.end_station is not None
                or segment.segment_start is not previous.segment_end
                or segment.segment_end is not following.segment_start
                or not _line_is_consistent(segment, path.color, stroke_width)
            ):
                return False
        return _same_identity_sequence(path.segments, expected_segments)
    except (AttributeError, OverflowError, TypeError, ValueError):
        return False


def build_candidate(
    path: Any,
    stations: list[Any],
    loop: bool,
    factory: Any,
    live_paths: Any,
    lane_spacing: int | float,
    stroke_width: int,
    live_storage_ids: set[int],
    live_geometry_ids: set[int],
):
    """Build and fully validate replacement geometry before any live write."""

    candidate = factory(path.color)
    if any(candidate is live_path for live_path in live_paths):
        raise ValueError("path factory returned a live path")
    candidate_collections = (
        candidate.stations,
        candidate.segments,
        candidate.path_segments,
        candidate.padding_segments,
        candidate.metros,
    )
    if (
        any(type(collection) is not list for collection in candidate_collections)
        or not _identity_unique(candidate_collections)
        or any(
            id(collection) in live_storage_ids for collection in candidate_collections
        )
    ):
        raise ValueError("path factory returned aliased collection storage")
    if any(candidate_collections):
        raise ValueError("path factory returned a nonempty candidate")
    candidate.color = path.color
    candidate.path_order = path.path_order
    candidate.stations[:] = stations
    candidate.is_looped = loop
    candidate.rebuild_geometry()
    candidate_collections = (
        candidate.stations,
        candidate.segments,
        candidate.path_segments,
        candidate.padding_segments,
        candidate.metros,
    )
    if (
        any(type(collection) is not list for collection in candidate_collections)
        or not _identity_unique(candidate_collections)
        or any(
            id(collection) in live_storage_ids for collection in candidate_collections
        )
        or candidate.color is not path.color
        or candidate.path_order != path.path_order
        or candidate.metros
        or any(
            id(value) in live_geometry_ids
            for segment in candidate.segments
            for value in (
                segment,
                segment.line,
                segment.segment_start,
                segment.segment_end,
            )
        )
        or not validate_path_geometry(
            candidate,
            stations,
            loop,
            lane_spacing=lane_spacing,
            stroke_width=stroke_width,
        )
    ):
        raise ValueError("path factory returned an invalid candidate")
    return candidate

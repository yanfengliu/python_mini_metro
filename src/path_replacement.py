"""Atomic, identity-preserving path replacement without domain imports."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from crossings import within_tunnel_budget
from path_replacement_geometry import (
    build_candidate,
    is_canonical_point,
    validate_path_geometry,
)
from path_replacement_snapshot import (
    exact_graph_value,
    finalize_replacement,
    identity_unique,
    restore_state,
    snapshot_state,
    validated_carriage_storage,
)

_POSITION_TOLERANCE = 1e-6
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _Motion:
    metro: Any
    key: tuple[Any, ...]
    preferred_direction: bool
    stopped: bool = False


@dataclass(frozen=True, slots=True)
class _Binding:
    metro: Any
    segment: Any
    index: int
    is_forward: bool


def _point(value: Any) -> tuple[Any, Any]:
    return (value.left, value.top)


def _is_path_segment(segment: Any) -> bool:
    return (
        getattr(segment, "start_station", None) is not None
        and getattr(segment, "end_station", None) is not None
    )


def _advance(index: int, is_forward: bool, count: int, is_looped: bool):
    if count == 1:
        return index, not is_forward
    if index == count - 1:
        if is_looped:
            return 0, is_forward
        return (index, False) if is_forward else (index - 1, is_forward)
    if index == 0:
        if is_forward:
            return 1, is_forward
        return (count - 1, is_forward) if is_looped else (index, True)
    return index + (1 if is_forward else -1), is_forward


def _path_key(segment: Any, is_forward: bool) -> tuple[Any, ...]:
    if is_forward:
        source, target = segment.start_station, segment.end_station
        start, end = segment.segment_start, segment.segment_end
    else:
        source, target = segment.end_station, segment.start_station
        start, end = segment.segment_end, segment.segment_start
    return ("path", id(source), id(target), _point(start), _point(end))


def _nearest_path_segment(
    segments: tuple[Any, ...], index: int, step: int, is_looped: bool
) -> Any | None:
    cursor = index + step
    for _ in segments:
        if not is_looped and not 0 <= cursor < len(segments):
            return None
        cursor %= len(segments)
        if _is_path_segment(segments[cursor]):
            return segments[cursor]
        cursor += step
    return None


def _padding_key(path: Any, index: int, is_forward: bool) -> tuple[Any, ...] | None:
    segments = tuple(path.segments)
    previous = _nearest_path_segment(segments, index, -1, bool(path.is_looped))
    following = _nearest_path_segment(segments, index, 1, bool(path.is_looped))
    if previous is None or following is None:
        return None
    if previous.end_station is not following.start_station:
        return None
    padding = segments[index]
    if is_forward:
        stations = (
            id(previous.start_station),
            id(previous.end_station),
            id(following.end_station),
        )
        start, end = padding.segment_start, padding.segment_end
    else:
        stations = (
            id(following.end_station),
            id(following.start_station),
            id(previous.start_station),
        )
        start, end = padding.segment_end, padding.segment_start
    return ("padding", *stations, _point(start), _point(end))


def _is_on_segment(metro: Any, segment: Any) -> bool:
    start_x, start_y = _point(segment.segment_start)
    end_x, end_y = _point(segment.segment_end)
    position_x, position_y = _point(metro.position)
    dx, dy = end_x - start_x, end_y - start_y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return (position_x, position_y) == (start_x, start_y)
    projection = (
        (position_x - start_x) * dx + (position_y - start_y) * dy
    ) / length_squared
    residual = abs((position_x - start_x) * dy - (position_y - start_y) * dx)
    residual /= math.sqrt(length_squared)
    return 0 <= projection <= 1 and residual <= _POSITION_TOLERANCE


def _stopped_motion(path: Any, metro: Any) -> _Motion | None:
    segments = tuple(path.segments)
    arrivals = []
    for index, segment in enumerate(segments):
        if not _is_path_segment(segment):
            continue
        for direction in (False, True):
            key = _path_key(segment, direction)
            station = segment.end_station if direction else segment.start_station
            endpoint = segment.segment_end if direction else segment.segment_start
            post_index, post_direction = _advance(
                index, direction, len(segments), bool(path.is_looped)
            )
            if (
                station is metro.current_station
                and _point(endpoint) == _point(metro.position)
                and post_index == metro.current_segment_idx
                and post_direction is metro.is_forward
            ):
                arrivals.append((key, direction))
    if len(arrivals) != 1:
        return None
    key, direction = arrivals[0]
    return _Motion(metro, key, direction, stopped=True)


def _target_motion(path: Any, metro: Any) -> _Motion | None:
    if (
        type(metro.current_segment_idx) is not int
        or type(metro.is_forward) is not bool
        or not is_canonical_point(metro.position)
    ):
        return None
    index = metro.current_segment_idx
    segments = tuple(path.segments)
    if not 0 <= index < len(segments) or segments[index] is not metro.current_segment:
        return None
    if metro.current_station is not None:
        return _stopped_motion(path, metro)
    if not _is_on_segment(metro, metro.current_segment):
        return None
    if _is_path_segment(metro.current_segment):
        key = _path_key(metro.current_segment, metro.is_forward)
    else:
        key = _padding_key(path, index, metro.is_forward)
        if key is None:
            return None
    return _Motion(metro, key, metro.is_forward)


def _choose_binding(candidate: Any, motion: _Motion) -> _Binding | None:
    matches = []
    segments = tuple(candidate.segments)
    for index, segment in enumerate(segments):
        for direction in (False, True):
            key = (
                _path_key(segment, direction)
                if _is_path_segment(segment)
                else _padding_key(candidate, index, direction)
            )
            if key != motion.key:
                continue
            if motion.stopped:
                post_index, post_direction = _advance(
                    index, direction, len(segments), bool(candidate.is_looped)
                )
                matches.append((direction, post_index, post_direction))
            else:
                matches.append((direction, index, direction))
    if len(matches) != 1:
        preferred = [item for item in matches if item[0] is motion.preferred_direction]
        if len(preferred) != 1:
            return None
        matches = preferred
    _, index, direction = matches[0]
    return _Binding(motion.metro, segments[index], index, direction)


def _normalize(host: Any, station_indices: Any, loop: Any):
    if type(loop) is not bool or type(station_indices) is not list:
        return None
    if len(station_indices) < 2 or any(
        type(index) is not int for index in station_indices
    ):
        return None
    if any(index < 0 or index >= len(host.stations) for index in station_indices):
        return None
    normalized = list(station_indices)
    if loop and normalized[-1] == normalized[0]:
        normalized.pop()
    if len(normalized) < 2 or len(set(normalized)) != len(normalized):
        return None
    stations = [host.stations[index] for index in normalized]
    if not identity_unique(stations):
        return None
    return stations


def _preflight(
    host: Any,
    target: Any,
    target_stations: list[Any],
    lane_spacing: int | float,
    stroke_width: int,
):
    paths = tuple(host.paths)
    stations = tuple(host.stations)
    if (
        bool(host.is_creating_path)
        or host.path_being_created is not None
        or getattr(host, "path_redraw", None) is not None
        or sum(path is target for path in paths) != 1
        or bool(getattr(target, "is_being_created", False))
        or not identity_unique(paths)
        or not identity_unique(stations)
    ):
        return None
    mutable_collections = [
        host.paths,
        host.stations,
        host.metros,
        host.passengers,
        *(
            collection
            for path in paths
            for collection in (
                path.stations,
                path.segments,
                path.path_segments,
                path.padding_segments,
                path.metros,
            )
        ),
    ]
    if any(not isinstance(collection, list) for collection in mutable_collections):
        return None
    if not identity_unique(mutable_collections):
        return None
    path_ids = [getattr(path, "id", _MISSING) for path in paths]
    if any(type(path_id) is not str or not path_id for path_id in path_ids):
        return None
    if len(set(path_ids)) != len(paths):
        return None
    active_station_ids = {id(station) for station in stations}
    if any(
        id(station) not in active_station_ids
        for path in paths
        for station in path.stations
    ):
        return None
    for path in paths:
        if not validate_path_geometry(
            path,
            path.stations,
            bool(path.is_looped),
            lane_spacing=lane_spacing,
            stroke_width=stroke_width,
        ):
            return None
    live_geometry_ids = {
        id(value)
        for path in paths
        for segment in path.segments
        for value in (
            segment,
            segment.line,
            segment.segment_start,
            segment.segment_end,
        )
    }
    live_geometry_ids.update(
        id(entity.position) for entity in (*stations, *host.metros, *host.passengers)
    )

    owners: dict[int, Any] = {}
    path_metros = []
    for path in paths:
        if bool(getattr(path, "is_being_created", False)):
            return None
        for metro in path.metros:
            if id(metro) in owners:
                return None
            owners[id(metro)] = path
            path_metros.append(metro)
            if metro.path_id != path.id:
                return None
    global_metros = tuple(host.metros)
    if not identity_unique(global_metros) or {
        id(item) for item in global_metros
    } != set(owners):
        return None
    carriage_lists = validated_carriage_storage(host, mutable_collections)
    if carriage_lists is None:
        return None

    global_passengers = tuple(host.passengers)
    if not identity_unique(global_passengers):
        return None
    holder_lists = [
        *(station.passengers for station in stations),
        *(metro.passengers for metro in global_metros),
    ]
    if any(not isinstance(collection, list) for collection in holder_lists):
        return None
    if not identity_unique([*mutable_collections, *carriage_lists, *holder_lists]):
        return None
    holders: dict[int, tuple[Any, Any | None]] = {}
    for station in stations:
        for passenger in station.passengers:
            if id(passenger) in holders:
                return None
            holders[id(passenger)] = (station, None)
    for metro in global_metros:
        for passenger in metro.passengers:
            if id(passenger) in holders:
                return None
            holders[id(passenger)] = (metro, owners[id(metro)])
    if {id(item) for item in global_passengers} != set(holders):
        return None

    plan_items = tuple(host.travel_plans.items())
    if any(id(passenger) not in holders for passenger, _ in plan_items):
        return None
    if any(
        plan is None
        or type(getattr(plan, "node_path", None)) is not list
        or type(getattr(plan, "next_station_idx", None)) is not int
        for _, plan in plan_items
    ):
        return None
    if not identity_unique(plan for _, plan in plan_items):
        return None
    node_lists = [plan.node_path for _, plan in plan_items]
    if not identity_unique(
        [*mutable_collections, *carriage_lists, *holder_lists, *node_lists]
    ):
        return None
    live_storage_ids = {
        id(collection)
        for collection in (
            *mutable_collections,
            *carriage_lists,
            *holder_lists,
            *node_lists,
        )
    }
    plans = {id(passenger): plan for passenger, plan in plan_items}
    onboard = []
    target_ids = {id(station) for station in target_stations}
    for metro in global_metros:
        owner = owners[id(metro)]
        for passenger in metro.passengers:
            plan = plans.get(id(passenger))
            if plan is None or type(plan.next_station_idx) is not int:
                return None
            nodes = plan.node_path
            cursor = plan.next_station_idx
            if not 0 <= cursor < len(nodes):
                return None
            node = nodes[cursor]
            station = getattr(node, "station", None)
            if (
                plan.next_station is not station
                or id(station) not in active_station_ids
                or plan.next_path is not owner
                or not any(value is station for value in owner.stations)
                or (owner is target and id(station) not in target_ids)
            ):
                return None
            onboard.append((passenger, owner, plan, station))

    motions = []
    for metro in target.metros:
        motion = _target_motion(target, metro)
        if motion is None:
            return None
        motions.append(motion)
    waiting = [
        (station, passenger)
        for station in stations
        for passenger in tuple(station.passengers)
    ]
    return motions, onboard, waiting, live_storage_ids, live_geometry_ids


def replace_path(
    host: Any,
    path: Any,
    station_indices: list[int],
    loop: bool = False,
    *,
    get_path_factory: Any,
    get_geometry_style: Any,
    get_graph_builder: Any,
    get_scoped_replanner: Any,
) -> bool:
    """Replace one live path atomically after semantic continuity preflight."""

    stations = _normalize(host, station_indices, loop)
    if stations is None:
        return False
    lane_spacing, stroke_width = get_geometry_style()
    preflight = _preflight(host, path, stations, lane_spacing, stroke_width)
    if preflight is None:
        return False
    motions, onboard, waiting, live_storage_ids, live_geometry_ids = preflight
    if (
        bool(path.is_looped) is loop
        and len(path.stations) == len(stations)
        and all(old is new for old, new in zip(path.stations, stations))
    ):
        return True

    if not within_tunnel_budget(host, stations, loop, exclude=path):
        return False

    candidate = build_candidate(
        path,
        stations,
        loop,
        get_path_factory(),
        tuple(host.paths),
        lane_spacing,
        stroke_width,
        live_storage_ids,
        live_geometry_ids,
    )
    bindings = []
    for motion in motions:
        binding = _choose_binding(candidate, motion)
        if binding is None:
            return False
        bindings.append(binding)

    state = snapshot_state(host, path)
    try:
        path.stations[:] = candidate.stations
        path.segments[:] = candidate.segments
        path.path_segments[:] = candidate.path_segments
        path.padding_segments[:] = candidate.padding_segments
        path.is_looped = loop
        for binding in bindings:
            binding.metro.current_segment = binding.segment
            binding.metro.current_segment_idx = binding.index
            binding.metro.is_forward = binding.is_forward
        graph = get_graph_builder()(host.stations, host.paths)
        markers = []
        for passenger, owner, plan, station in onboard:
            node = exact_graph_value(graph, station)
            if not any(value is owner for value in node.paths):
                raise ValueError("fresh marker node does not contain the owning path")
            markers.append((plan, owner, station, node))
        for plan, owner, station, node in markers:
            plan.node_path[:] = [node]
            plan.next_station_idx = 0
            plan.next_station = station
            plan.next_path = owner
        for station, passenger in waiting:
            get_scoped_replanner()(passenger, station, graph)
        finalize_replacement(host, state)
    except BaseException as error:
        traceback = error.__traceback__
        try:
            restore_state(host, path, state)
        finally:
            raise error.with_traceback(traceback)
    return True

"""Exact rollback state for carriage and whole-consist owner transactions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fleet_validation import identity_union

_MISSING = object()


def _point_state(point: Any) -> tuple[Any, tuple[Any, Any]]:
    return point, (point.left, point.top)


def _collection_state(collection: list[Any]) -> tuple[list[Any], tuple[Any, ...]]:
    return collection, tuple(collection)


def _same_identity(actual: Any, expected: tuple[Any, ...]) -> bool:
    return (
        isinstance(actual, list)
        and len(actual) == len(expected)
        and all(current is prior for current, prior in zip(actual, expected))
    )


def snapshot_transaction_state(host: Any) -> dict[str, Any]:
    paths = tuple(host.paths)
    metros = identity_union(host.metros, *(path.metros for path in paths))
    segments = identity_union(
        *(
            collection
            for path in paths
            for collection in (path.segments, path.path_segments, path.padding_segments)
        )
    )
    plans = identity_union(host.travel_plans.values())
    carriages = identity_union(*(metro.carriages for metro in metros))
    return {
        "host": {
            "num_carriages": getattr(host, "num_carriages", _MISSING),
            "is_game_over": host.is_game_over,
            "time_ms": host.time_ms,
            "is_creating_path": host.is_creating_path,
            "path_being_created": host.path_being_created,
            "paths": _collection_state(host.paths),
            "stations": _collection_state(host.stations),
            "metros": _collection_state(host.metros),
            "travel_plans": (host.travel_plans, tuple(host.travel_plans.items())),
        },
        "python_rng": host.context.python_random.getstate(),
        "numpy_rng": deepcopy(host.context.numpy_random.bit_generator.state),
        "paths": tuple(
            (
                path,
                path.id,
                path.color,
                path.path_order,
                path.is_looped,
                path.is_being_created,
                path.temp_point,
                *(
                    _collection_state(collection)
                    for collection in (
                        path.stations,
                        path.segments,
                        path.path_segments,
                        path.padding_segments,
                        path.metros,
                    )
                ),
            )
            for path in paths
        ),
        "stations": tuple(
            (station, *_point_state(station.position)) for station in host.stations
        ),
        "segments": tuple(
            (
                segment,
                getattr(segment, "start_station", _MISSING),
                getattr(segment, "end_station", _MISSING),
                getattr(segment, "path_order", _MISSING),
                segment.color,
                *_point_state(segment.segment_start),
                *_point_state(segment.segment_end),
                segment.line,
                segment.line.color,
                *_point_state(segment.line.start),
                *_point_state(segment.line.end),
                segment.line.width,
            )
            for segment in segments
        ),
        "metros": tuple(
            (
                metro,
                *_collection_state(metro.carriages),
                *_collection_state(metro.passengers),
                metro._base_capacity,
                metro.is_unassignment_queued,
                metro.path_id,
                metro.current_segment,
                metro.current_segment_idx,
                metro.current_station,
                *_point_state(metro.position),
                metro.is_forward,
                metro.stop_time_remaining_ms,
                metro.boarding_progress_ms,
                metro.speed,
                getattr(metro, "_station_service_action", _MISSING),
            )
            for metro in metros
        ),
        "carriages": tuple(
            (
                carriage,
                carriage.id,
                carriage.capacity,
                carriage.shape,
                getattr(carriage, "_capacity", _MISSING),
            )
            for carriage in carriages
        ),
        "plans": tuple(
            (
                plan,
                plan.next_path,
                plan.next_station,
                plan.next_station_idx,
                *_collection_state(plan.node_path),
            )
            for plan in plans
        ),
    }


def restore_transaction_state(host: Any, state: dict[str, Any]) -> None:
    host_state = state["host"]
    for name in ("paths", "stations", "metros"):
        collection, contents = host_state[name]
        setattr(host, name, collection)
        list.clear(collection)
        list.extend(collection, contents)
    mapping, items = host_state["travel_plans"]
    host.travel_plans = mapping
    dict.clear(mapping)
    dict.update(mapping, items)
    for name in (
        "num_carriages",
        "is_game_over",
        "time_ms",
        "is_creating_path",
        "path_being_created",
    ):
        value = host_state[name]
        if value is not _MISSING:
            setattr(host, name, value)

    for record in state["paths"]:
        path, path_id, color, order, looped, creating, temp, *collections = record
        path.id = path_id
        path.color = color
        path.path_order = order
        path.is_looped = looped
        path.is_being_created = creating
        path.temp_point = temp
        for name, (collection, contents) in zip(
            ("stations", "segments", "path_segments", "padding_segments", "metros"),
            collections,
        ):
            setattr(path, name, collection)
            list.clear(collection)
            list.extend(collection, contents)

    for station, position, coordinates in state["stations"]:
        station.position = position
        position.left, position.top = coordinates

    for record in state["segments"]:
        (
            segment,
            start_station,
            end_station,
            order,
            color,
            start,
            start_xy,
            end,
            end_xy,
            line,
            line_color,
            line_start,
            line_start_xy,
            line_end,
            line_end_xy,
            width,
        ) = record
        if start_station is not _MISSING:
            segment.start_station = start_station
        if end_station is not _MISSING:
            segment.end_station = end_station
        if order is not _MISSING:
            segment.path_order = order
        segment.color = color
        segment.segment_start = start
        start.left, start.top = start_xy
        segment.segment_end = end
        end.left, end.top = end_xy
        segment.line = line
        line.color = line_color
        line.start = line_start
        line_start.left, line_start.top = line_start_xy
        line.end = line_end
        line_end.left, line_end.top = line_end_xy
        line.width = width

    for record in state["metros"]:
        (
            metro,
            carriage_list,
            carriages,
            passenger_list,
            passengers,
            base,
            queued,
            path_id,
            segment,
            index,
            station,
            position,
            position_xy,
            forward,
            stop,
            progress,
            speed,
            service,
        ) = record
        metro.carriages = carriage_list
        list.clear(carriage_list)
        list.extend(carriage_list, carriages)
        metro.passengers = passenger_list
        list.clear(passenger_list)
        list.extend(passenger_list, passengers)
        metro._base_capacity = base
        metro.is_unassignment_queued = queued
        metro.path_id = path_id
        metro.current_segment = segment
        metro.current_segment_idx = index
        metro.current_station = station
        metro.position = position
        position.left, position.top = position_xy
        metro.is_forward = forward
        metro.stop_time_remaining_ms = stop
        metro.boarding_progress_ms = progress
        metro.speed = speed
        if service is _MISSING:
            try:
                del metro._station_service_action
            except AttributeError:
                pass
        else:
            metro._station_service_action = service

    for carriage, identifier, _capacity, shape, private_capacity in state["carriages"]:
        carriage.id = identifier
        carriage.shape = shape
        if private_capacity is not _MISSING:
            carriage._capacity = private_capacity

    for plan, next_path, next_station, cursor, nodes, node_items in state["plans"]:
        plan.next_path = next_path
        plan.next_station = next_station
        plan.next_station_idx = cursor
        plan.node_path = nodes
        list.clear(nodes)
        list.extend(nodes, node_items)

    host.context.python_random.setstate(state["python_rng"])
    host.context.numpy_random.bit_generator.state = deepcopy(state["numpy_rng"])


def transaction_state_matches(
    host: Any,
    state: dict[str, Any],
    *,
    carriage_override: tuple[Any, tuple[Any, ...]] | None = None,
    allow_service_change: Any | None = None,
    removed_owner: tuple[Any, Any] | None = None,
    added_owner: tuple[Any, Any] | None = None,
) -> bool:
    """Check the complete snapshot, allowing one exact composition transition.

    ``removed_owner=(path, metro)`` expects that exact Metro gone from the
    global and owning-path fleets; ``added_owner=(path, metro)`` expects it
    appended to both (the snapshot must predate the append, so the new Metro
    has no per-record entry to check). The two are mutually exclusive per call.
    """

    try:
        host_state = state["host"]
        if any(
            getattr(host, name) != host_state[name]
            for name in ("num_carriages", "time_ms")
            if host_state[name] is not _MISSING
        ):
            return False
        if (
            host.is_game_over is not host_state["is_game_over"]
            or host.is_creating_path is not host_state["is_creating_path"]
            or host.path_being_created is not host_state["path_being_created"]
            or host.context.python_random.getstate() != state["python_rng"]
            or host.context.numpy_random.bit_generator.state != state["numpy_rng"]
        ):
            return False
        for name in ("paths", "stations", "metros"):
            collection, contents = host_state[name]
            if name == "metros" and removed_owner is not None:
                _path, removed_metro = removed_owner
                contents = tuple(item for item in contents if item is not removed_metro)
            if name == "metros" and added_owner is not None:
                contents = (*contents, added_owner[1])
            if getattr(host, name) is not collection or not _same_identity(
                collection, contents
            ):
                return False
        mapping, items = host_state["travel_plans"]
        if host.travel_plans is not mapping or len(mapping) != len(items):
            return False
        if any(
            actual_key is not key or actual_value is not value
            for (actual_key, actual_value), (key, value) in zip(mapping.items(), items)
        ):
            return False

        for record in state["paths"]:
            path, path_id, color, order, looped, creating, temp, *collections = record
            if (
                path.id != path_id
                or path.color != color
                or path.path_order != order
                or path.is_looped is not looped
                or path.is_being_created is not creating
                or path.temp_point is not temp
            ):
                return False
            for name, (collection, contents) in zip(
                ("stations", "segments", "path_segments", "padding_segments", "metros"),
                collections,
            ):
                if (
                    name == "metros"
                    and removed_owner is not None
                    and path is removed_owner[0]
                ):
                    contents = tuple(
                        item for item in contents if item is not removed_owner[1]
                    )
                if (
                    name == "metros"
                    and added_owner is not None
                    and path is added_owner[0]
                ):
                    contents = (*contents, added_owner[1])
                if getattr(path, name) is not collection or not _same_identity(
                    collection, contents
                ):
                    return False

        for station, position, coordinates in state["stations"]:
            if (
                station.position is not position
                or (position.left, position.top) != coordinates
            ):
                return False

        for record in state["segments"]:
            (
                segment,
                start_station,
                end_station,
                order,
                color,
                start,
                start_xy,
                end,
                end_xy,
                line,
                line_color,
                line_start,
                line_start_xy,
                line_end,
                line_end_xy,
                width,
            ) = record
            if (
                getattr(segment, "start_station", _MISSING) is not start_station
                or getattr(segment, "end_station", _MISSING) is not end_station
                or getattr(segment, "path_order", _MISSING) != order
                or segment.color != color
                or segment.segment_start is not start
                or (start.left, start.top) != start_xy
                or segment.segment_end is not end
                or (end.left, end.top) != end_xy
                or segment.line is not line
                or line.color != line_color
                or line.start is not line_start
                or (line_start.left, line_start.top) != line_start_xy
                or line.end is not line_end
                or (line_end.left, line_end.top) != line_end_xy
                or line.width != width
            ):
                return False

        override_metro, override_items = carriage_override or (None, ())
        for record in state["metros"]:
            (
                metro,
                carriage_list,
                carriages,
                passenger_list,
                passengers,
                base,
                queued,
                path_id,
                segment,
                index,
                station,
                position,
                position_xy,
                forward,
                stop,
                progress,
                speed,
                service,
            ) = record
            expected_carriages = (
                override_items if metro is override_metro else carriages
            )
            if (
                metro.carriages is not carriage_list
                or not _same_identity(metro.carriages, expected_carriages)
                or metro.passengers is not passenger_list
                or not _same_identity(metro.passengers, passengers)
                or metro._base_capacity != base
                or metro.is_unassignment_queued is not queued
                or metro.path_id != path_id
                or metro.current_segment is not segment
                or metro.current_segment_idx != index
                or metro.current_station is not station
                or metro.position is not position
                or (position.left, position.top) != position_xy
                or metro.is_forward is not forward
            ):
                return False
            if metro is not allow_service_change and (
                metro.stop_time_remaining_ms != stop
                or metro.boarding_progress_ms != progress
                or metro.speed != speed
                or getattr(metro, "_station_service_action", _MISSING) is not service
            ):
                return False

        for carriage, identifier, capacity, shape, private_capacity in state[
            "carriages"
        ]:
            if (
                carriage.id != identifier
                or carriage.capacity != capacity
                or carriage.shape is not shape
                or getattr(carriage, "_capacity", _MISSING) != private_capacity
            ):
                return False
        for plan, next_path, next_station, cursor, nodes, node_items in state["plans"]:
            if (
                plan.next_path is not next_path
                or plan.next_station is not next_station
                or plan.next_station_idx != cursor
                or plan.node_path is not nodes
                or not _same_identity(nodes, node_items)
            ):
                return False
        return True
    except (AttributeError, TypeError, ValueError):
        return False

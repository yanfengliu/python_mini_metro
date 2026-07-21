"""Rollback snapshots for the dependency-light path replacement transaction."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_MISSING = object()


def _point(value: Any) -> tuple[Any, Any]:
    return (value.left, value.top)


def identity_unique(values: Any) -> bool:
    items = tuple(values)
    return len({id(value) for value in items}) == len(items)


def exact_graph_value(graph: Any, station: Any) -> Any:
    matches = [value for key, value in graph.items() if key is station]
    if len(matches) != 1 or getattr(matches[0], "station", None) is not station:
        raise ValueError("fresh graph does not contain the exact active station")
    return matches[0]


def snapshot_state(host: Any, path: Any):
    host_names = ("stations", "paths", "metros", "passengers", "travel_plans")
    host_state = {
        name: (
            getattr(host, name),
            tuple(getattr(host, name).items())
            if name == "travel_plans"
            else tuple(getattr(host, name)),
        )
        for name in host_names
    }
    path_names = ("stations", "segments", "path_segments", "padding_segments", "metros")
    path_state = {
        name: (getattr(path, name), tuple(getattr(path, name))) for name in path_names
    }
    plan_state = [
        (
            plan,
            plan.next_path,
            plan.next_station,
            plan.next_station_idx,
            plan.node_path,
            tuple(plan.node_path),
        )
        for plan in host.travel_plans.values()
    ]
    holder_state = [
        (holder, holder.passengers, tuple(holder.passengers))
        for holder in (*host.stations, *host.metros)
    ]
    passenger_state = [
        (
            passenger,
            passenger.is_at_destination,
            passenger.wait_ms,
            passenger.position,
            _point(passenger.position),
        )
        for passenger in host.passengers
    ]
    metro_state = [
        (metro, metro.current_segment, metro.current_segment_idx, metro.is_forward)
        for metro in path.metros
    ]
    composition_state = [
        (
            metro,
            metro.carriages,
            tuple(metro.carriages),
            metro.passengers,
            tuple(metro.passengers),
            metro._base_capacity,
            metro.is_unassignment_queued,
            getattr(metro, "_station_service_action", None),
            metro.stop_time_remaining_ms,
            metro.boarding_progress_ms,
            metro.speed,
        )
        for metro in host.metros
        if hasattr(metro, "carriages")
    ]
    carriage_state = [
        (carriage, carriage.id, carriage._capacity, carriage.shape)
        for record in composition_state
        for carriage in record[2]
    ]
    carriage_total = (
        hasattr(host, "num_carriages"),
        getattr(host, "num_carriages", _MISSING),
    )
    return (
        host_state,
        path_state,
        path.is_looped,
        plan_state,
        holder_state,
        passenger_state,
        metro_state,
        composition_state,
        carriage_state,
        carriage_total,
        host.context.python_random.getstate(),
        deepcopy(host.context.numpy_random.bit_generator.state),
    )


def restore_state(host: Any, path: Any, state: Any) -> None:
    (
        host_state,
        path_state,
        is_looped,
        plans,
        holders,
        passengers,
        metros,
        compositions,
        carriage_records,
        carriage_total,
        python_rng,
        numpy_rng,
    ) = state
    for name, (collection, contents) in host_state.items():
        setattr(host, name, collection)
        collection.clear()
        collection.update(contents) if name == "travel_plans" else collection.extend(
            contents
        )
    for name, (collection, contents) in path_state.items():
        setattr(path, name, collection)
        collection[:] = contents
    path.is_looped = is_looped
    for plan, next_path, next_station, cursor, nodes, node_items in plans:
        plan.next_path, plan.next_station, plan.next_station_idx = (
            next_path,
            next_station,
            cursor,
        )
        plan.node_path = nodes
        nodes[:] = node_items
    for holder, collection, contents in holders:
        holder.passengers = collection
        collection[:] = contents
    for passenger, flag, wait, position, coordinates in passengers:
        passenger.is_at_destination, passenger.wait_ms = flag, wait
        passenger.position = position
        position.left, position.top = coordinates
    for metro, segment, index, direction in metros:
        metro.current_segment, metro.current_segment_idx, metro.is_forward = (
            segment,
            index,
            direction,
        )
    for (
        metro,
        carriage_list,
        carriage_items,
        passenger_list,
        passenger_items,
        base,
        queued,
        service,
        stop,
        progress,
        speed,
    ) in compositions:
        metro.carriages = carriage_list
        list.clear(carriage_list)
        list.extend(carriage_list, carriage_items)
        metro.passengers = passenger_list
        list.clear(passenger_list)
        list.extend(passenger_list, passenger_items)
        metro._base_capacity = base
        metro.is_unassignment_queued = queued
        metro._station_service_action = service
        metro.stop_time_remaining_ms = stop
        metro.boarding_progress_ms = progress
        metro.speed = speed
    for carriage, identifier, capacity, shape in carriage_records:
        carriage.id = identifier
        carriage._capacity = capacity
        carriage.shape = shape
    had_total, total = carriage_total
    if had_total:
        host.num_carriages = total
    else:
        try:
            del host.num_carriages
        except AttributeError:
            pass
    host.context.python_random.setstate(python_rng)
    host.context.numpy_random.bit_generator.state = deepcopy(numpy_rng)


def composition_state_matches(
    host: Any, state: Any, *, service_changes: tuple[Any, ...] = ()
) -> bool:
    """Check that every globally snapshotted consist remains identity-exact."""

    compositions = state[7]
    carriage_records = state[8]
    had_total, total = state[9]
    try:
        if hasattr(host, "num_carriages") is not had_total:
            return False
        if had_total and (
            type(host.num_carriages) is not type(total) or host.num_carriages != total
        ):
            return False
        for carriage, identifier, capacity, shape in carriage_records:
            if (
                type(carriage.id) is not type(identifier)
                or carriage.id != identifier
                or type(carriage._capacity) is not type(capacity)
                or carriage._capacity != capacity
                or carriage.shape is not shape
            ):
                return False
        for (
            metro,
            carriage_list,
            carriage_items,
            passenger_list,
            passengers,
            base,
            queued,
            service,
            stop,
            progress,
            speed,
        ) in compositions:
            service_changed = any(metro is item for item in service_changes)
            if (
                metro.carriages is not carriage_list
                or len(metro.carriages) != len(carriage_items)
                or any(
                    current is not expected
                    for current, expected in zip(metro.carriages, carriage_items)
                )
                or metro.passengers is not passenger_list
                or len(metro.passengers) != len(passengers)
                or any(
                    current is not expected
                    for current, expected in zip(metro.passengers, passengers)
                )
                or metro._base_capacity != base
                or metro.is_unassignment_queued is not queued
                or (
                    not service_changed
                    and (
                        getattr(metro, "_station_service_action", None) is not service
                        or metro.stop_time_remaining_ms != stop
                        or metro.boarding_progress_ms != progress
                        or metro.speed != speed
                    )
                )
                or (
                    service_changed
                    and metro.speed
                    != (
                        0
                        if getattr(metro, "_station_service_action", None) is not None
                        else speed
                    )
                )
            ):
                return False
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def validated_carriage_storage(
    host: Any, mutable_collections: list[Any]
) -> tuple[list[Any], ...] | None:
    """Validate and return carriage lists without importing entities at startup."""

    if not hasattr(host, "num_carriages"):
        return ()
    from fleet_validation import carriage_state_is_canonical, identity_unique

    if not carriage_state_is_canonical(host):
        return None
    carriage_lists = tuple(
        metro.carriages for metro in host.metros if hasattr(metro, "carriages")
    )
    if not identity_unique([*mutable_collections, *carriage_lists]):
        return None
    return carriage_lists


def replacement_composition_matches(
    host: Any, state: Any, *, service_changes: tuple[Any, ...] = ()
) -> bool:
    """Require exact consist preservation plus a canonical postcommit graph."""

    if not composition_state_matches(host, state, service_changes=service_changes):
        return False
    if not hasattr(host, "num_carriages"):
        return True
    from fleet_validation import carriage_state_is_canonical

    return carriage_state_is_canonical(host, require_bound_service=True)


def finalize_replacement(host: Any, state: Any) -> None:
    """Reconcile every stopped Metro and enforce the exact postcommit graph."""

    if not composition_state_matches(host, state):
        raise ValueError("path replacement changed consist composition")
    stopped = tuple(
        metro
        for metro in host.metros
        if getattr(metro, "current_station", None) is not None
    )
    reconcile = getattr(host, "_reconcile_station_service", None)
    if stopped and not callable(reconcile):
        raise ValueError("path replacement cannot reconcile station service")
    for metro in stopped:
        reconcile(metro)
    if not replacement_composition_matches(host, state, service_changes=stopped):
        raise ValueError("path replacement changed consist composition")

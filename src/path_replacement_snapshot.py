"""Rollback snapshots for the dependency-light path replacement transaction."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _point(value: Any) -> tuple[Any, Any]:
    return (value.left, value.top)


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
    return (
        host_state,
        path_state,
        path.is_looped,
        plan_state,
        holder_state,
        passenger_state,
        metro_state,
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
    host.context.python_random.setstate(python_rng)
    host.context.numpy_random.bit_generator.state = deepcopy(numpy_rng)

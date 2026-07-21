"""Shared canonical fleet and carriage-composition validation."""

from __future__ import annotations

from typing import Any, Iterable

from entity.carriage import Carriage
from graph.graph_algo import build_station_nodes_dict
from passenger_capacity import (
    BOARD,
    DESTINATION,
    TRANSFER,
    pure_service_action,
    same_service_action,
)

_MISSING = object()


def identity_unique(values: Iterable[Any]) -> bool:
    items = tuple(values)
    return len({id(item) for item in items}) == len(items)


def identity_union(*groups: Iterable[Any]) -> tuple[Any, ...]:
    result: list[Any] = []
    for group in groups:
        for item in group:
            if all(item is not prior for prior in result):
                result.append(item)
    return tuple(result)


def canonical_metros(host: Any) -> tuple[Any, ...] | None:
    global_metros = getattr(host, "metros", None)
    paths = getattr(host, "paths", None)
    if not isinstance(global_metros, list) or not isinstance(paths, list):
        return None
    path_lists = tuple(getattr(path, "metros", None) for path in paths)
    if any(not isinstance(items, list) for items in path_lists):
        return None
    return identity_union(global_metros, *path_lists)


def assigned_carriage_count(host: Any) -> int:
    metros = getattr(host, "metros", ())
    if not isinstance(metros, list):
        return 0
    return sum(
        len(carriages)
        for metro in metros
        if isinstance((carriages := getattr(metro, "carriages", None)), list)
    )


def service_cache_is_canonical(host: Any, metro: Any, *, allow_unbound: bool) -> bool:
    action = getattr(metro, "_station_service_action", None)
    station = getattr(metro, "current_station", None)
    remaining = getattr(metro, "stop_time_remaining_ms", _MISSING)
    progress = getattr(metro, "boarding_progress_ms", _MISSING)
    zero_timing = (
        type(remaining) is int
        and remaining == 0
        and type(progress) is int
        and progress == 0
    )
    if station is None:
        return action is None and zero_timing
    if action is None:
        if not zero_timing:
            return False
        if allow_unbound:
            return True
        return (
            pure_service_action(
                host,
                metro,
                station,
                build_station_nodes_dict(host.stations, host.paths),
            )
            is None
        )
    if (
        not isinstance(action, tuple)
        or len(action) != 2
        or type(action[0]) is not str
        or action[0] not in {DESTINATION, TRANSFER, BOARD}
    ):
        return False
    interval = getattr(metro, "boarding_time_per_passenger_ms", _MISSING)
    if (
        type(interval) is not int
        or interval <= 0
        or type(progress) is not int
        or not 0 <= progress < interval
        or type(remaining) is not int
        or remaining != interval - progress
    ):
        return False
    expected = pure_service_action(
        host,
        metro,
        station,
        build_station_nodes_dict(host.stations, host.paths),
    )
    return same_service_action(action, expected)


def carriage_state_is_canonical(
    host: Any,
    *,
    extra_storage: Iterable[Any] = (),
    require_bound_service: bool = False,
) -> bool:
    """Validate composition without mutating or constructing entity state."""

    try:
        metros = canonical_metros(host)
        if metros is None:
            return False
        paths = tuple(host.paths)
        stations = tuple(getattr(host, "stations", ()))
        travel_plans = getattr(host, "travel_plans", None)
        if not isinstance(travel_plans, dict):
            return False

        topology_storage = [
            host.paths,
            host.stations,
            host.metros,
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
            *(station.passengers for station in stations),
            *(metro.passengers for metro in metros),
            *(plan.node_path for plan in travel_plans.values()),
            *extra_storage,
        ]
        if any(not isinstance(collection, list) for collection in topology_storage):
            return False

        carriage_lists = [getattr(metro, "carriages", None) for metro in metros]
        if any(not isinstance(collection, list) for collection in carriage_lists):
            return False
        if not identity_unique([*topology_storage, *carriage_lists]):
            return False

        all_carriages = [carriage for items in carriage_lists for carriage in items]
        if not identity_unique(all_carriages):
            return False
        identifiers = []
        for carriage in all_carriages:
            if type(carriage) is not Carriage:
                return False
            identifier = getattr(carriage, "id", _MISSING)
            capacity = getattr(carriage, "capacity", _MISSING)
            if (
                type(identifier) is not str
                or not identifier
                or type(capacity) is not int
                or capacity <= 0
                or getattr(carriage, "shape", None) is None
                or hasattr(carriage, "passengers")
            ):
                return False
            identifiers.append(identifier)
        if len(set(identifiers)) != len(identifiers):
            return False

        for metro in metros:
            base = getattr(metro, "_base_capacity", _MISSING)
            passengers = getattr(metro, "passengers", None)
            queued = getattr(metro, "is_unassignment_queued", _MISSING)
            if (
                type(base) is not int
                or base < 0
                or not isinstance(passengers, list)
                or type(queued) is not bool
            ):
                return False
            expected = base + sum(item.capacity for item in metro.carriages)
            capacity = getattr(metro, "capacity", _MISSING)
            if type(capacity) is not int or capacity != expected:
                return False
            if len(passengers) > capacity or not service_cache_is_canonical(
                host, metro, allow_unbound=not require_bound_service
            ):
                return False
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def valid_new_carriage(candidate: Any, existing: Iterable[Any]) -> bool:
    """Require one fresh exact Carriage identity and globally fresh nonempty ID."""

    current = tuple(existing)
    return (
        type(candidate) is Carriage
        and type(getattr(candidate, "id", None)) is str
        and bool(candidate.id)
        and type(getattr(candidate, "capacity", None)) is int
        and candidate.capacity > 0
        and getattr(candidate, "shape", None) is not None
        and not hasattr(candidate, "passengers")
        and all(candidate is not item for item in current)
        and all(candidate.id != getattr(item, "id", None) for item in current)
    )

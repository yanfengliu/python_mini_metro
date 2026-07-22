"""Pure station-service selection and fractional timer reconciliation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DESTINATION = "destination"
TRANSFER = "transfer"
BOARD = "board"

_MISSING = object()
_PLAN_FIELDS = ("next_path", "next_station", "next_station_idx")


def same_service_action(left: Any, right: Any) -> bool:
    return (
        isinstance(left, tuple)
        and isinstance(right, tuple)
        and len(left) == len(right) == 2
        and left[0] == right[0]
        and left[1] is right[1]
    )


def next_service_action(
    host: Any,
    metro: Any,
    station: Any,
    station_nodes_dict: dict[Any, Any],
    *,
    mutate_travel_plans: bool,
) -> tuple[str, Any] | None:
    """Resolve one executable identity in canonical service priority."""

    destination, transfer = host.get_unloading_candidates_for_metro(metro, station)
    if destination:
        return (DESTINATION, destination[0])
    if transfer and station.has_room():
        return (TRANSFER, transfer[0])
    if not host.can_board_at_station(metro, station) or not metro.has_room():
        return None
    boarding = host.get_boarding_candidates_for_metro(
        metro,
        station,
        station_nodes_dict,
        mutate_travel_plans=mutate_travel_plans,
    )
    if boarding:
        return (BOARD, boarding[0])
    return None


def _plan_snapshot(mapping: dict[Any, Any]) -> tuple[Any, ...]:
    plans = []
    seen: set[int] = set()
    for plan in mapping.values():
        if id(plan) in seen:
            continue
        seen.add(id(plan))
        fields = tuple(
            (name, hasattr(plan, name), getattr(plan, name, _MISSING))
            for name in _PLAN_FIELDS
        )
        node_path = getattr(plan, "node_path", _MISSING)
        nodes = tuple(node_path) if isinstance(node_path, list) else _MISSING
        plans.append((plan, fields, node_path, nodes))
    return tuple(plans)


def _holder_snapshot(host: Any, metro: Any, station: Any) -> tuple[Any, ...]:
    holders = [host]
    holders.extend(getattr(host, "stations", ()))
    holders.extend(getattr(host, "metros", ()))
    holders.extend((station, metro))
    result = []
    seen: set[int] = set()
    for holder in holders:
        passengers = getattr(holder, "passengers", _MISSING)
        if not isinstance(passengers, list) or id(passengers) in seen:
            continue
        seen.add(id(passengers))
        result.append((holder, passengers, tuple(passengers)))
    return tuple(result)


def _query_snapshot(host: Any, metro: Any, station: Any) -> dict[str, Any]:
    mapping = host.travel_plans
    python_random = getattr(getattr(host, "context", None), "python_random", None)
    numpy_random = getattr(getattr(host, "context", None), "numpy_random", None)
    python_state = (
        python_random.getstate()
        if callable(getattr(python_random, "getstate", None))
        else _MISSING
    )
    bit_generator = getattr(numpy_random, "bit_generator", None)
    numpy_state = (
        deepcopy(bit_generator.state) if bit_generator is not None else _MISSING
    )
    return {
        "mapping": mapping,
        "items": tuple(mapping.items()),
        "plans": _plan_snapshot(mapping),
        "holders": _holder_snapshot(host, metro, station),
        "python_random": python_random,
        "python_state": python_state,
        "bit_generator": bit_generator,
        "numpy_state": numpy_state,
    }


def _restore_query(host: Any, snapshot: dict[str, Any]) -> None:
    mapping = snapshot["mapping"]
    host.travel_plans = mapping
    dict.clear(mapping)
    dict.update(mapping, snapshot["items"])
    for plan, fields, node_path, nodes in snapshot["plans"]:
        for name, existed, value in fields:
            if existed:
                setattr(plan, name, value)
            else:
                try:
                    delattr(plan, name)
                except AttributeError:
                    pass
        if node_path is not _MISSING:
            plan.node_path = node_path
            list.clear(node_path)
            list.extend(node_path, nodes)
    for holder, passengers, contents in snapshot["holders"]:
        holder.passengers = passengers
        list.clear(passengers)
        list.extend(passengers, contents)
    if snapshot["python_state"] is not _MISSING:
        snapshot["python_random"].setstate(snapshot["python_state"])
    if snapshot["numpy_state"] is not _MISSING:
        snapshot["bit_generator"].state = deepcopy(snapshot["numpy_state"])


def pure_service_action(
    host: Any,
    metro: Any,
    station: Any,
    station_nodes_dict: dict[Any, Any],
) -> tuple[str, Any] | None:
    """Run the live oracle and restore every plan, holder, and seeded RNG effect."""

    snapshot = _query_snapshot(host, metro, station)
    try:
        return next_service_action(
            host,
            metro,
            station,
            station_nodes_dict,
            mutate_travel_plans=False,
        )
    finally:
        _restore_query(host, snapshot)


def _real_station_stop(path: Any, metro: Any) -> Any | None:
    station = getattr(metro, "current_station", None)
    if station is None:
        return None
    stations = getattr(path, "stations", ())
    if any(station is candidate for candidate in stations):
        return station
    return None


def _plan_alight_station(plan: Any) -> Any | None:
    node_path = getattr(plan, "node_path", None)
    index = getattr(plan, "next_station_idx", 0)
    if not isinstance(node_path, list) or not node_path:
        return None
    if type(index) is not int or not 0 <= index < len(node_path):
        return None
    return getattr(node_path[index], "station", None)


def _stranded_riders(host: Any, path: Any, metro: Any, station: Any) -> list[Any]:
    """Riders matching the D-024 drain sub-cases, in exact holder order."""

    stranded = []
    for rider in metro.passengers:
        plan = host.travel_plans.get(rider)
        if plan is None:
            stranded.append(rider)
            continue
        alight = _plan_alight_station(plan)
        # An alight on the stop itself is blocked only by station capacity
        # (the oracle is quiet); any alight off this line can never execute.
        if alight is station or not any(
            alight is candidate for candidate in getattr(path, "stations", ())
        ):
            stranded.append(rider)
    return stranded


def drain_queued_returns(host: Any, *, build_graph: Any) -> None:
    """Force-alight riders stuck aboard queued Metros when the oracle is quiet.

    Ordinary destination/transfer service always runs first through the
    unchanged oracle; the batch fires only when the pure oracle resolves no
    executable action while riders remain, under the D-024 overflow-permitted
    placement. The queued stop-override's ``None`` service cache is untouched.
    """

    candidates = []
    for path in getattr(host, "paths", ()):
        for metro in getattr(path, "metros", ()):
            if getattr(metro, "is_unassignment_queued", False) is not True:
                continue
            riders = getattr(metro, "passengers", None)
            if not isinstance(riders, list) or not riders:
                continue
            station = _real_station_stop(path, metro)
            remaining = getattr(metro, "stop_time_remaining_ms", 0)
            if station is not None and not (type(remaining) is int and remaining > 0):
                candidates.append((path, metro, station))
    if not candidates:
        return
    station_nodes_dict = build_graph()
    for path, metro, station in candidates:
        if pure_service_action(host, metro, station, station_nodes_dict) is not None:
            continue
        for rider in _stranded_riders(host, path, metro, station):
            metro.passengers.remove(rider)
            station.passengers.append(rider)
            host.travel_plans.pop(rider, None)
            rider.wait_ms = 0


def reconcile_service_action(
    host: Any,
    metro: Any,
    station: Any,
    station_nodes_dict: dict[Any, Any],
) -> tuple[str, Any] | None:
    """Bind the pure current action, preserving only an exact identity fraction."""

    action = pure_service_action(host, metro, station, station_nodes_dict)
    current = getattr(metro, "_station_service_action", None)
    if action is None:
        metro._station_service_action = None
        metro.stop_time_remaining_ms = 0
        metro.boarding_progress_ms = 0
        return None
    if not same_service_action(current, action):
        metro.boarding_progress_ms = 0
    interval = metro.boarding_time_per_passenger_ms
    progress = metro.boarding_progress_ms
    if type(interval) is not int or interval <= 0:
        raise ValueError("boarding interval must be a positive integer")
    if type(progress) is not int or not 0 <= progress < interval:
        progress = 0
        metro.boarding_progress_ms = 0
    metro._station_service_action = action
    metro.stop_time_remaining_ms = interval - progress
    metro.speed = 0
    return action

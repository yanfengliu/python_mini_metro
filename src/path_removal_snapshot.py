"""Exact rollback state for the transactional conserving path removal."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_MISSING = object()

_HOST_LISTS = ("paths", "stations", "all_stations", "metros", "passengers")
_HOST_MAPPINGS = ("travel_plans", "path_colors", "path_to_color", "path_to_button")
_PROGRESSION_FIELDS = (
    "deliveries",
    "line_credits",
    "purchased_num_paths",
    "unlocked_num_paths",
    "unlocked_num_stations",
)
_HOST_FIELDS = ("unlocked_num_paths", "unlocked_num_stations")
_METRO_FIELDS = (
    "is_unassignment_queued",
    "path_id",
    "current_station",
    "current_segment",
    "current_segment_idx",
    "is_forward",
    "stop_time_remaining_ms",
    "boarding_progress_ms",
    "speed",
    "_station_service_action",
)
_RIDER_FIELDS = ("wait_ms", "is_at_destination")
_STATION_FIELDS = ("unlock_blink_start_time_ms",)
_BUTTON_FIELDS = (
    "path",
    "cross",
    "show_cross",
    "is_locked",
    "unlock_blink_start_time_ms",
)
_PLAN_FIELDS = ("next_path", "next_station", "next_station_idx")


def _list_state(owner: Any, name: str) -> tuple[Any, ...] | None:
    collection = getattr(owner, name, _MISSING)
    if not isinstance(collection, list):
        return None
    return (owner, name, collection, tuple(collection))


def _mapping_state(owner: Any, name: str) -> tuple[Any, ...] | None:
    mapping = getattr(owner, name, _MISSING)
    if not isinstance(mapping, dict):
        return None
    return (owner, name, mapping, tuple(mapping.items()))


def _field_states(owner: Any, names: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple((owner, name, getattr(owner, name, _MISSING)) for name in names)


def _iter_unique(*collections: Any) -> list[Any]:
    result: list[Any] = []
    seen: set[int] = set()
    for collection in collections:
        if not isinstance(collection, (list, tuple)):
            continue
        for item in collection:
            if id(item) in seen:
                continue
            seen.add(id(item))
            result.append(item)
    return result


def snapshot_removal_state(host: Any) -> dict[str, Any]:
    paths = tuple(getattr(host, "paths", None) or ())
    stations = _iter_unique(
        getattr(host, "stations", None), getattr(host, "all_stations", None)
    )
    metros = _iter_unique(
        getattr(host, "metros", None),
        *(getattr(path, "metros", None) for path in paths),
    )
    riders = _iter_unique(
        getattr(host, "passengers", None),
        *(getattr(metro, "passengers", None) for metro in metros),
        *(getattr(station, "passengers", None) for station in stations),
    )
    plan_mapping = getattr(host, "travel_plans", None)
    plans = _iter_unique(
        tuple(plan_mapping.values()) if isinstance(plan_mapping, dict) else None
    )
    buttons = tuple(getattr(host, "path_buttons", None) or ())

    lists = [
        entry
        for entry in (
            *(_list_state(host, name) for name in _HOST_LISTS),
            *(_list_state(path, "metros") for path in paths),
            *(_list_state(metro, "passengers") for metro in metros),
            *(_list_state(metro, "carriages") for metro in metros),
            *(_list_state(station, "passengers") for station in stations),
        )
        if entry is not None
    ]
    mappings = [
        entry
        for entry in (_mapping_state(host, name) for name in _HOST_MAPPINGS)
        if entry is not None
    ]
    progression = getattr(host, "_progression", None)
    fields = [
        *(
            _field_states(progression, _PROGRESSION_FIELDS)
            if progression is not None
            else ()
        ),
        *_field_states(host, _HOST_FIELDS),
        *(state for metro in metros for state in _field_states(metro, _METRO_FIELDS)),
        *(state for rider in riders for state in _field_states(rider, _RIDER_FIELDS)),
        *(
            state
            for station in stations
            for state in _field_states(station, _STATION_FIELDS)
        ),
        *(
            state
            for button in buttons
            for state in _field_states(button, _BUTTON_FIELDS)
        ),
    ]
    button_shapes = tuple(
        (button, shape, getattr(shape, "color", _MISSING))
        for button in buttons
        for shape in (getattr(button, "shape", None),)
        if shape is not None
    )
    plan_states = tuple(
        (
            plan,
            _field_states(plan, _PLAN_FIELDS),
            node_path if isinstance(node_path, list) else None,
            tuple(node_path) if isinstance(node_path, list) else (),
        )
        for plan in plans
        for node_path in (getattr(plan, "node_path", None),)
    )

    context = getattr(host, "context", None)
    python_random = getattr(context, "python_random", None)
    python_state = (
        python_random.getstate()
        if callable(getattr(python_random, "getstate", None))
        else _MISSING
    )
    bit_generator = getattr(
        getattr(context, "numpy_random", None), "bit_generator", None
    )
    numpy_state = (
        deepcopy(bit_generator.state) if bit_generator is not None else _MISSING
    )
    return {
        "lists": tuple(lists),
        "mappings": tuple(mappings),
        "fields": tuple(fields),
        "button_shapes": button_shapes,
        "plans": plan_states,
        "python_random": python_random,
        "python_state": python_state,
        "bit_generator": bit_generator,
        "numpy_state": numpy_state,
    }


def restore_removal_state(host: Any, state: dict[str, Any]) -> None:
    for owner, name, mapping, items in state["mappings"]:
        setattr(owner, name, mapping)
        dict.clear(mapping)
        dict.update(mapping, items)
    for owner, name, collection, contents in state["lists"]:
        setattr(owner, name, collection)
        list.clear(collection)
        list.extend(collection, contents)
    for owner, name, value in state["fields"]:
        if value is not _MISSING:
            setattr(owner, name, value)
    for plan, fields, node_path, nodes in state["plans"]:
        for owner, name, value in fields:
            if value is not _MISSING:
                setattr(owner, name, value)
        if node_path is not None:
            plan.node_path = node_path
            list.clear(node_path)
            list.extend(node_path, nodes)
    for button, shape, color in state["button_shapes"]:
        button.shape = shape
        if color is not _MISSING:
            shape.color = color
    if state["python_state"] is not _MISSING:
        state["python_random"].setstate(state["python_state"])
    if state["numpy_state"] is not _MISSING:
        state["bit_generator"].state = deepcopy(state["numpy_state"])

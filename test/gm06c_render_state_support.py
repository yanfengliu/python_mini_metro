from __future__ import annotations

from typing import Any

_MISSING = ("<missing>",)


def _freeze(value: Any):
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    if isinstance(value, dict):
        return tuple((_freeze(key), _freeze(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    if (
        hasattr(value, "dtype")
        and hasattr(value, "shape")
        and hasattr(value, "tobytes")
    ):
        return (str(value.dtype), tuple(value.shape), value.tobytes())
    if hasattr(value, "left") and hasattr(value, "top"):
        return _point(value)
    return (id(value), getattr(value, "id", None), type(value).__qualname__)


def _attribute(value: Any, name: str):
    return _freeze(getattr(value, name)) if hasattr(value, name) else _MISSING


def _point(value: Any):
    if value is None:
        return None
    return (id(value), float(value.left), float(value.top))


def _rectangle(value: Any):
    if value is None:
        return None
    return (
        id(value),
        int(value.x),
        int(value.y),
        int(value.width),
        int(value.height),
    )


def _sequence(value: Any):
    return (id(value), tuple(id(item) for item in value))


def _shape(shape: Any):
    if shape is None:
        return None
    points = getattr(shape, "points", ())
    return (
        id(shape),
        getattr(shape, "id", None),
        type(shape).__qualname__,
        _attribute(shape, "type"),
        _attribute(shape, "color"),
        _attribute(shape, "degrees"),
        _attribute(shape, "radius"),
        _attribute(shape, "width"),
        _attribute(shape, "height"),
        _point(getattr(shape, "position", None)),
        id(points),
        tuple(_point(point) for point in points),
    )


def _passenger(passenger: Any):
    return (
        id(passenger),
        getattr(passenger, "id", None),
        _point(getattr(passenger, "position", None)),
        _shape(getattr(passenger, "destination_shape", None)),
        _attribute(passenger, "is_at_destination"),
        _attribute(passenger, "wait_ms"),
    )


def _station(station: Any):
    passengers = getattr(station, "passengers", ())
    blips = getattr(station, "snap_blips", ())
    return (
        id(station),
        getattr(station, "id", None),
        _point(getattr(station, "position", None)),
        _shape(getattr(station, "shape", None)),
        _attribute(station, "capacity"),
        _attribute(station, "size"),
        _attribute(station, "passengers_per_row"),
        _attribute(station, "unlock_blink_start_time_ms"),
        _sequence(passengers),
        tuple(_passenger(item) for item in passengers),
        (id(blips), _freeze(blips)),
    )


def _carriage(carriage: Any):
    return (
        id(carriage),
        getattr(carriage, "id", None),
        _attribute(carriage, "capacity"),
        _attribute(carriage, "size"),
        _attribute(carriage, "passengers_per_row"),
        _point(getattr(carriage, "position", None)),
        _shape(getattr(carriage, "shape", None)),
    )


def _metro(metro: Any):
    passengers = getattr(metro, "passengers", ())
    carriages = getattr(metro, "carriages", ())
    names = (
        "_base_capacity",
        "capacity",
        "size",
        "path_id",
        "current_segment_idx",
        "is_forward",
        "is_unassignment_queued",
        "stop_time_remaining_ms",
        "boarding_progress_ms",
        "boarding_time_per_passenger_ms",
        "_station_service_action",
        "speed",
        "max_speed",
        "acceleration_per_ms",
        "deceleration_per_ms",
        "just_arrived_and_stopped",
        "passengers_per_row",
    )
    return (
        id(metro),
        getattr(metro, "id", None),
        _point(getattr(metro, "position", None)),
        _shape(getattr(metro, "shape", None)),
        tuple((name, _attribute(metro, name)) for name in names),
        id(getattr(metro, "current_segment", None)),
        id(getattr(metro, "current_station", None)),
        _sequence(passengers),
        tuple(_passenger(item) for item in passengers),
        _sequence(carriages),
        tuple(_carriage(item) for item in carriages),
    )


def _segment(segment: Any):
    line = getattr(segment, "line", None)
    return (
        id(segment),
        getattr(segment, "id", None),
        type(segment).__qualname__,
        _attribute(segment, "color"),
        _attribute(segment, "path_order"),
        id(getattr(segment, "start_station", None)),
        id(getattr(segment, "end_station", None)),
        _point(getattr(segment, "segment_start", None)),
        _point(getattr(segment, "segment_end", None)),
        id(line),
        _attribute(line, "id") if line is not None else None,
        _attribute(line, "color") if line is not None else None,
        _point(getattr(line, "start", None)),
        _point(getattr(line, "end", None)),
        _attribute(line, "width") if line is not None else None,
    )


def _path(path: Any):
    names = (
        "stations",
        "metros",
        "segments",
        "path_segments",
        "padding_segments",
    )
    collections = tuple((name, _sequence(getattr(path, name, ()))) for name in names)
    return (
        id(path),
        getattr(path, "id", None),
        _attribute(path, "color"),
        _attribute(path, "path_order"),
        _attribute(path, "is_looped"),
        _attribute(path, "is_being_created"),
        _point(getattr(path, "temp_point", None)),
        collections,
        tuple(_segment(item) for item in getattr(path, "segments", ())),
    )


def _button(button: Any):
    cross = getattr(button, "cross", None)
    names = (
        "operation",
        "is_hovered",
        "show_cross",
        "is_locked",
        "unlock_blink_start_time_ms",
    )
    return (
        id(button),
        type(button).__qualname__,
        _point(getattr(button, "position", None)),
        _shape(getattr(button, "shape", None)),
        id(getattr(button, "path_button", None)),
        id(getattr(button, "path", None)),
        tuple((name, _attribute(button, name)) for name in names),
        id(cross),
        _shape(cross),
    )


def _travel_plan(passenger: Any, plan: Any):
    node_path = getattr(plan, "node_path", ())
    return (
        id(passenger),
        id(plan),
        id(getattr(plan, "next_path", None)),
        id(getattr(plan, "next_station", None)),
        _attribute(plan, "next_station_idx"),
        _sequence(node_path),
        tuple(
            (
                id(node),
                getattr(node, "id", None),
                id(getattr(node, "station", None)),
                _freeze(getattr(node, "neighbors", ())),
                _freeze(getattr(node, "paths", ())),
            )
            for node in node_path
        ),
    )


def render_state_signature(mediator: Any) -> tuple[Any, ...]:
    scalar_names = (
        "time_ms",
        "steps",
        "is_paused",
        "is_game_over",
        "game_speed_multiplier",
        "deliveries",
        "line_credits",
        "num_metros",
        "available_locomotives",
        "num_carriages",
        "assigned_carriages",
        "available_carriages",
        "num_paths",
        "path_unlock_milestones",
        "path_purchase_prices",
        "num_stations",
        "initial_num_stations",
        "station_unlock_milestones",
        "unlocked_num_paths",
        "unlocked_num_stations",
        "passenger_spawning_step",
        "passenger_spawning_interval_step",
        "passenger_max_wait_time_ms",
        "overdue_passenger_threshold",
        "is_mouse_down",
        "is_creating_path",
        "_layout_size",
    )
    sequence_names = (
        "paths",
        "metros",
        "stations",
        "all_stations",
        "passengers",
        "buttons",
        "path_buttons",
        "fleet_buttons",
        "carriage_buttons",
        "speed_buttons",
    )
    mapping_names = (
        "travel_plans",
        "path_to_button",
        "path_to_color",
        "path_colors",
        "station_steps_since_last_spawn",
        "station_spawn_interval_steps",
    )
    button_registry_names = (
        "buttons",
        "path_buttons",
        "fleet_buttons",
        "carriage_buttons",
        "speed_buttons",
    )
    passengers = tuple(getattr(mediator, "passengers", ()))
    return (
        tuple((name, _attribute(mediator, name)) for name in scalar_names),
        tuple(
            (name, _sequence(getattr(mediator, name, ()))) for name in sequence_names
        ),
        tuple(
            (
                name,
                id(getattr(mediator, name, {})),
                _freeze(getattr(mediator, name, {})),
            )
            for name in mapping_names
        ),
        _freeze(mediator.context.python_random.getstate()),
        _freeze(mediator.context.numpy_random.bit_generator.state),
        (
            id(getattr(mediator, "path_being_created", None)),
            _freeze(getattr(mediator, "path_redraw", None)),
            _freeze(getattr(mediator, "path_edit_selection", None)),
            id(getattr(mediator, "_compat_renderer", None)),
            _rectangle(getattr(mediator, "game_over_restart_rect", None)),
            _rectangle(getattr(mediator, "game_over_exit_rect", None)),
        ),
        tuple(_path(item) for item in getattr(mediator, "paths", ())),
        tuple(_metro(item) for item in getattr(mediator, "metros", ())),
        tuple(_station(item) for item in getattr(mediator, "all_stations", ())),
        tuple(_passenger(item) for item in passengers),
        tuple(
            _travel_plan(passenger, plan)
            for passenger, plan in getattr(mediator, "travel_plans", {}).items()
        ),
        tuple(
            (
                name,
                id(getattr(mediator, name, ())),
                tuple(_button(item) for item in getattr(mediator, name, ())),
            )
            for name in button_registry_names
        ),
    )

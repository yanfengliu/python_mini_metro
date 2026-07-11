from __future__ import annotations

import math
from enum import Enum
from typing import Any, Sequence

import numpy as np

from env import MiniMetroEnv


def _safe(value: Any) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isfinite(number):
            return number
        label = (
            "NaN" if math.isnan(number) else ("Infinity" if number > 0 else "-Infinity")
        )
        return {"$nonFinite": label}
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Enum):
        return _safe(value.value)
    if isinstance(value, np.ndarray):
        return _safe(value.tolist())
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    raise TypeError(f"checkpoint contains unsupported {type(value).__name__}")


def _position(value: Any) -> list[Any] | None:
    return None if value is None else [_safe(value.left), _safe(value.top)]


def _unique(objects: Sequence[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[int] = set()
    for item in objects:
        if id(item) not in seen:
            seen.add(id(item))
            result.append(item)
    return result


def _normalize_observation(observation: dict[str, Any]) -> tuple[dict, dict]:
    structured = observation["structured"]
    station_ids = {
        item["id"]: index for index, item in enumerate(structured["stations"])
    }
    path_ids = {item["id"]: index for index, item in enumerate(structured["paths"])}
    metro_ids = {item["id"]: index for index, item in enumerate(structured["metros"])}
    passenger_ids = {
        item["id"]: index for index, item in enumerate(structured["passengers"])
    }

    def lookup(mapping: dict[str, int], key: Any) -> int | None:
        return mapping.get(key) if key is not None else None

    stations = [
        {
            "position": _safe(item["position"]),
            "shape_type": _safe(item["shape_type"]),
            "passenger_indices": [
                passenger_ids.get(key) for key in item["passenger_ids"]
            ],
            "passenger_count": item["passenger_count"],
        }
        for item in structured["stations"]
    ]
    paths = [
        {
            "station_indices": [station_ids.get(key) for key in item["station_ids"]],
            "is_looped": item["is_looped"],
            "color": _safe(item["color"]),
        }
        for item in structured["paths"]
    ]
    metros = [
        {
            "path_index": lookup(path_ids, item["path_id"]),
            "position": _safe(item["position"]),
            "current_station_index": lookup(station_ids, item["current_station_id"]),
            "passenger_indices": [
                passenger_ids.get(key) for key in item["passenger_ids"]
            ],
        }
        for item in structured["metros"]
    ]
    passengers = []
    for item in structured["passengers"]:
        normalized_location = None
        if item["location"] is not None:
            kind, key = item["location"]
            mapping = station_ids if kind == "station" else metro_ids
            normalized_location = {"kind": kind, "index": mapping.get(key)}
        passengers.append(
            {
                "destination_shape_type": _safe(item["destination_shape_type"]),
                "is_at_destination": item["is_at_destination"],
                "location": normalized_location,
            }
        )
    normalized = {
        "stations": stations,
        "paths": paths,
        "metros": metros,
        "passengers": passengers,
        "score": structured["score"],
        "time_ms": structured["time_ms"],
        "steps": structured["steps"],
        "is_paused": structured["is_paused"],
        "is_game_over": structured["is_game_over"],
    }
    return _safe(normalized), _safe(observation["arrays"])


def canonical_checkpoint(
    env: MiniMetroEnv, observation: dict[str, Any] | None = None
) -> dict[str, Any]:
    mediator = env.mediator
    observation = env.observe() if observation is None else observation
    structured, arrays = _normalize_observation(observation)
    stations = _unique([*mediator.all_stations, *mediator.stations])
    paths = _unique(mediator.paths)
    metros = _unique(
        [*mediator.metros, *(metro for path in paths for metro in path.metros)]
    )
    passengers = _unique(
        [
            *mediator.passengers,
            *(item for station in stations for item in station.passengers),
            *(item for metro in metros for item in metro.passengers),
            *mediator.travel_plans.keys(),
        ]
    )
    station_index = {id(item): index for index, item in enumerate(stations)}
    path_index = {id(item): index for index, item in enumerate(paths)}
    metro_index = {id(item): index for index, item in enumerate(metros)}
    passenger_index = {id(item): index for index, item in enumerate(passengers)}

    def ref(mapping: dict[int, int], value: Any) -> int | None:
        return mapping.get(id(value)) if value is not None else None

    locations: dict[int, dict[str, Any]] = {}
    for station in stations:
        for passenger in station.passengers:
            locations[id(passenger)] = {
                "kind": "station",
                "index": ref(station_index, station),
            }
    for metro in metros:
        for passenger in metro.passengers:
            locations[id(passenger)] = {
                "kind": "metro",
                "index": ref(metro_index, metro),
            }

    station_pool = [
        {
            "position": _position(station.position),
            "shape_type": _safe(station.shape.type),
            "active": station in mediator.stations,
            "capacity": station.capacity,
            "passenger_indices": [
                ref(passenger_index, item) for item in station.passengers
            ],
            "unlock_blink_start_time_ms": station.unlock_blink_start_time_ms,
            "snap_blips": _safe(station.snap_blips),
        }
        for station in stations
    ]
    topology_paths = []
    for path in paths:
        topology_paths.append(
            {
                "station_indices": [ref(station_index, item) for item in path.stations],
                "metro_indices": [ref(metro_index, item) for item in path.metros],
                "is_looped": path.is_looped,
                "is_being_created": path.is_being_created,
                "temp_position": _position(path.temp_point),
                "color": _safe(path.color),
                "path_order": path.path_order,
                "segments": [
                    {
                        "kind": type(segment).__name__,
                        "start_station_index": ref(
                            station_index, segment.start_station
                        ),
                        "end_station_index": ref(station_index, segment.end_station),
                        "start": _position(segment.segment_start),
                        "end": _position(segment.segment_end),
                    }
                    for segment in path.segments
                ],
            }
        )
    passenger_state = [
        {
            "destination_shape_type": _safe(passenger.destination_shape.type),
            "position": _position(passenger.position),
            "is_at_destination": passenger.is_at_destination,
            "wait_ms": passenger.wait_ms,
            "location": locations.get(id(passenger)),
        }
        for passenger in passengers
    ]
    travel_plans = []
    for passenger in passengers:
        plan = mediator.travel_plans.get(passenger)
        if plan is None:
            continue
        node_path = []
        for node in plan.node_path:
            station = getattr(node, "station", node)
            node_paths = getattr(node, "paths", ())
            node_path.append(
                {
                    "station_index": ref(station_index, station),
                    "path_indices": sorted(
                        index
                        for item in node_paths
                        if (index := ref(path_index, item)) is not None
                    ),
                }
            )
        travel_plans.append(
            {
                "passenger_index": ref(passenger_index, passenger),
                "next_path_index": ref(path_index, plan.next_path),
                "next_station_index": ref(station_index, plan.next_station),
                "next_station_cursor": plan.next_station_idx,
                "node_path": node_path,
            }
        )
    metro_motion = []
    for metro in metros:
        owner = next((path for path in paths if metro in path.metros), None)
        declared_owner = next(
            (path for path in paths if path.id == metro.path_id), None
        )
        segment_relation = None
        if owner is not None and metro.current_segment is not None:
            segment_relation = next(
                (
                    index
                    for index, segment in enumerate(owner.segments)
                    if segment is metro.current_segment
                ),
                None,
            )
        current_segment = metro.current_segment
        metro_motion.append(
            {
                "path_index": ref(path_index, owner),
                "declared_path_index": ref(path_index, declared_owner),
                "position": _position(metro.position),
                "current_station_index": ref(station_index, metro.current_station),
                "current_segment_index": metro.current_segment_idx,
                "current_segment_relation_index": segment_relation,
                "current_segment": (
                    {
                        "kind": type(current_segment).__name__,
                        "start_station_index": ref(
                            station_index, current_segment.start_station
                        ),
                        "end_station_index": ref(
                            station_index, current_segment.end_station
                        ),
                        "start": _position(current_segment.segment_start),
                        "end": _position(current_segment.segment_end),
                    }
                    if current_segment is not None
                    else None
                ),
                "capacity": metro.capacity,
                "passenger_indices": [
                    ref(passenger_index, item) for item in metro.passengers
                ],
                "speed": _safe(metro.speed),
                "max_speed": _safe(metro.max_speed),
                "acceleration_per_ms": _safe(metro.acceleration_per_ms),
                "deceleration_per_ms": _safe(metro.deceleration_per_ms),
                "is_forward": metro.is_forward,
                "stop_time_remaining_ms": metro.stop_time_remaining_ms,
                "boarding_progress_ms": metro.boarding_progress_ms,
                "boarding_time_per_passenger_ms": metro.boarding_time_per_passenger_ms,
                "just_arrived_and_stopped": metro.just_arrived_and_stopped,
            }
        )
    checkpoint = {
        "schemaVersion": 1,
        "environment": {
            "dt_ms_default": env.dt_ms_default,
            "last_score": env.last_score,
        },
        "structured": structured,
        "arrays": arrays,
        "stationPool": station_pool,
        "topology": {
            "active_station_indices": [
                ref(station_index, item) for item in mediator.stations
            ],
            "paths": topology_paths,
            "path_being_created_index": ref(path_index, mediator.path_being_created),
            "is_creating_path": mediator.is_creating_path,
            "path_colors": [
                {"color": _safe(color), "taken": taken}
                for color, taken in mediator.path_colors.items()
            ],
            "path_to_color": [
                _safe(mediator.path_to_color.get(path)) for path in paths
            ],
            "path_to_button": [
                (
                    mediator.path_buttons.index(mediator.path_to_button[path])
                    if path in mediator.path_to_button
                    else None
                )
                for path in paths
            ],
        },
        "passengers": passenger_state,
        "travelPlans": travel_plans,
        "progression": {
            "score": mediator.score,
            "total_travels_handled": mediator.total_travels_handled,
            "purchased_num_paths": mediator.purchased_num_paths,
            "unlocked_num_paths": mediator.unlocked_num_paths,
            "unlocked_num_stations": mediator.unlocked_num_stations,
            "path_purchase_prices": mediator.path_purchase_prices,
            "path_unlock_milestones": mediator.path_unlock_milestones,
            "station_unlock_milestones": mediator.station_unlock_milestones,
            "time_ms": mediator.time_ms,
            "steps": mediator.steps,
            "is_paused": mediator.is_paused,
            "is_game_over": mediator.is_game_over,
            "game_speed_multiplier": mediator.game_speed_multiplier,
            "limits": {
                "num_paths": mediator.num_paths,
                "num_metros": mediator.num_metros,
                "num_stations": mediator.num_stations,
                "initial_num_stations": mediator.initial_num_stations,
                "passenger_max_wait_time_ms": mediator.passenger_max_wait_time_ms,
                "max_waiting_passengers": mediator.max_waiting_passengers,
            },
            "path_buttons": [
                {
                    "is_locked": button.is_locked,
                    "path_index": ref(path_index, button.path),
                    "unlock_blink_start_time_ms": button.unlock_blink_start_time_ms,
                }
                for button in mediator.path_buttons
            ],
        },
        "spawning": {
            "start_step": mediator.passenger_spawning_step,
            "base_interval_steps": mediator.passenger_spawning_interval_step,
            "stations": [
                {
                    "station_index": ref(station_index, station),
                    "steps_since_last_spawn": mediator.station_steps_since_last_spawn.get(
                        station
                    ),
                    "interval_steps": mediator.station_spawn_interval_steps.get(
                        station
                    ),
                }
                for station in stations
            ],
        },
        "metroMotion": metro_motion,
        "rng": {
            "python": _safe(mediator.context.python_random.getstate()),
            "numpy": _safe(mediator.context.numpy_random.bit_generator.state),
        },
    }
    return _safe(checkpoint)

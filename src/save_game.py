"""GM-07b saver: pure quiescent-boundary state capture and atomic saves.

serialize_game reads live state through attributes only (never through
mutating getters), rejects mid-gesture boundaries, and returns a strict
schema-v1 document; save_game writes its canonical ASCII bytes through a
save-local mkstemp -> fsync -> os.replace atomic writer, so a failed
save leaves the destination untouched and no temporary file behind.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path as FilesystemPath
from typing import Any

from recursive_checkpoint_schema import safe_checkpoint_value
from save_load import deserialize_game, load_game
from save_schema import (
    SAVE_RULES_VERSION,
    SAVE_SCHEMA_VERSION,
    SAVE_STATE_CONTRACT,
    canonical_save_bytes,
    validate_save,
)

__all__ = ["serialize_game", "save_game", "deserialize_game", "load_game"]


def _require_quiescent(mediator: Any) -> None:
    # The clock-reset-safe boundary: no creation, redraw, or edit gesture
    # may be active. A bare is_mouse_down does not block saving.
    if mediator.is_creating_path:
        raise ValueError("cannot save while a path-creation gesture is active")
    if mediator.path_being_created is not None:
        raise ValueError("cannot save while a path draft exists")
    if mediator.path_redraw is not None:
        raise ValueError("cannot save during a path redraw gesture")
    if mediator.path_edit_selection is not None:
        raise ValueError("cannot save during a path edit selection")


def _require_canonical_fleet(mediator: Any) -> None:
    owners: dict[int, Any] = {}
    for path in mediator.paths:
        for metro in path.metros:
            if id(metro) in owners:
                raise ValueError("cannot save a Metro owned by two paths")
            owners[id(metro)] = path
    global_ids = [id(metro) for metro in mediator.metros]
    if len(set(global_ids)) != len(global_ids) or set(owners) != set(global_ids):
        raise ValueError("cannot save without canonical dual Metro ownership")
    for metro in mediator.metros:
        if metro.path_id != owners[id(metro)].id:
            raise ValueError("cannot save a Metro whose path binding disagrees")


def _station_records(mediator: Any) -> list[dict[str, Any]]:
    active_count = len(mediator.stations)
    prefix = mediator.all_stations[:active_count]
    if len(prefix) != active_count or any(
        live is not pooled for live, pooled in zip(mediator.stations, prefix)
    ):
        # Position-derived activity is only faithful for a prefix; a
        # non-prefix live list would be silently normalized, so reject it.
        raise ValueError("cannot save a non-prefix active station list")
    return [
        {
            "id": station.id,
            "position": [station.position.left, station.position.top],
            "shapeType": station.shape.type,
            "active": index < active_count,
            "capacity": station.capacity,
            "waitingPassengerIds": [rider.id for rider in station.passengers],
            "unlockBlinkStartTimeMs": station.unlock_blink_start_time_ms,
            "snapBlips": station.snap_blips,
        }
        for index, station in enumerate(mediator.all_stations)
    ]


def _passenger_records(mediator: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": passenger.id,
            "destinationShapeType": passenger.destination_shape.type,
            "isAtDestination": passenger.is_at_destination,
            "waitMs": passenger.wait_ms,
        }
        for passenger in mediator.passengers
    ]


def _path_records(mediator: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": path.id,
            "color": path.color,
            "stationIds": [station.id for station in path.stations],
            "metroIds": [metro.id for metro in path.metros],
            "isLooped": path.is_looped,
            "pathOrder": path.path_order,
        }
        for path in mediator.paths
    ]


def _service_action_record(metro: Any) -> dict[str, Any] | None:
    # The bound cache persists VERBATIM, including the stale-reset boundary
    # where it no longer matches the re-derivable action: that staleness is
    # real game state (the next reconcile resets boarding progress), so the
    # loader must be able to restore it without re-deriving anything.
    action = metro._station_service_action
    if action is None:
        return None
    kind, passenger = action
    return {
        "kind": kind,
        "passengerId": passenger.id if passenger is not None else None,
    }


def _metro_records(mediator: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": metro.id,
            "pathId": metro.path_id,
            "position": [metro.position.left, metro.position.top],
            "currentSegmentIdx": metro.current_segment_idx,
            "currentStationId": (
                metro.current_station.id if metro.current_station is not None else None
            ),
            "isForward": metro.is_forward,
            "speed": metro.speed,
            "maxSpeed": metro.max_speed,
            "accelerationPerMs": metro.acceleration_per_ms,
            "decelerationPerMs": metro.deceleration_per_ms,
            "stopTimeRemainingMs": metro.stop_time_remaining_ms,
            "boardingProgressMs": metro.boarding_progress_ms,
            "boardingTimePerPassengerMs": metro.boarding_time_per_passenger_ms,
            "justArrivedAndStopped": metro.just_arrived_and_stopped,
            "isUnassignmentQueued": metro.is_unassignment_queued,
            "serviceAction": _service_action_record(metro),
            "baseCapacity": metro._base_capacity,
            "carriages": [
                {"id": carriage.id, "capacity": carriage.capacity}
                for carriage in metro.carriages
            ],
            "onboardPassengerIds": [rider.id for rider in metro.passengers],
        }
        for metro in mediator.metros
    ]


def _travel_plan_records(mediator: Any) -> dict[str, Any]:
    live_paths = {id(path) for path in mediator.paths}
    records: dict[str, Any] = {}
    for passenger, plan in mediator.travel_plans.items():
        records[passenger.id] = {
            # Attribute read on purpose: the get_next_station getter
            # mutates its cache and would break saver purity.
            "nextPathId": plan.next_path.id if plan.next_path is not None else None,
            "nextStationId": (
                plan.next_station.id if plan.next_station is not None else None
            ),
            "nextStationIdx": plan.next_station_idx,
            "nodePath": [
                {
                    "stationId": node.station.id,
                    # Ref-filter to document-live paths, mirroring the
                    # checkpoint: already-removed members are invisible.
                    "pathIds": sorted(
                        path.id for path in node.paths if id(path) in live_paths
                    ),
                }
                for node in plan.node_path
            ],
        }
    return records


def _spawn_timer_records(mediator: Any) -> list[list[Any]]:
    records: list[list[Any]] = []
    for station in mediator.all_stations:
        since = mediator.station_steps_since_last_spawn.get(station)
        interval = mediator.station_spawn_interval_steps.get(station)
        if since is None or interval is None:
            raise ValueError("cannot save without spawn state for every pool station")
        records.append([station.id, since, interval])
    return records


def serialize_game(mediator: Any) -> dict[str, Any]:
    """Capture one strict v1 save document without mutating the Mediator."""

    _require_quiescent(mediator)
    _require_canonical_fleet(mediator)
    raw = {
        "schemaVersion": SAVE_SCHEMA_VERSION,
        "stateContract": SAVE_STATE_CONTRACT,
        "rulesVersion": SAVE_RULES_VERSION,
        "timeMs": mediator.time_ms,
        "steps": mediator.steps,
        "gameSpeedMultiplier": mediator.game_speed_multiplier,
        "isGameOver": mediator.is_game_over,
        "pauseReasons": sorted(getattr(mediator, "_pause_reasons", ())),
        "passengerSpawningStep": mediator.passenger_spawning_step,
        "passengerSpawningIntervalStep": mediator.passenger_spawning_interval_step,
        "passengerMaxWaitTimeMs": mediator.passenger_max_wait_time_ms,
        "overduePassengerThreshold": mediator.overdue_passenger_threshold,
        "deliveries": mediator.deliveries,
        "lineCredits": mediator.line_credits,
        "purchasedNumPaths": mediator.purchased_num_paths,
        "unlockedNumPaths": mediator.unlocked_num_paths,
        "unlockedNumStations": mediator.unlocked_num_stations,
        "numPaths": mediator.num_paths,
        "numStations": mediator.num_stations,
        "initialNumStations": mediator.initial_num_stations,
        "pathPurchasePrices": list(mediator.path_purchase_prices),
        "pathUnlockMilestones": list(mediator.path_unlock_milestones),
        "stationUnlockMilestones": list(mediator.station_unlock_milestones),
        "numMetros": mediator.num_metros,
        "numCarriages": mediator.num_carriages,
        "stations": _station_records(mediator),
        "passengers": _passenger_records(mediator),
        "paths": _path_records(mediator),
        "metros": _metro_records(mediator),
        "travelPlans": _travel_plan_records(mediator),
        "pathColors": [[color, taken] for color, taken in mediator.path_colors.items()],
        "pathToColor": [
            [path.id, color] for path, color in mediator.path_to_color.items()
        ],
        "spawnTimers": _spawn_timer_records(mediator),
        "pathButtons": [
            {
                "isLocked": button.is_locked,
                "unlockBlinkStartTimeMs": button.unlock_blink_start_time_ms,
            }
            for button in mediator.path_buttons
        ],
        "rng": {
            "python": mediator.context.python_random.getstate(),
            "numpy": mediator.context.numpy_random.bit_generator.state,
        },
    }
    document = safe_checkpoint_value(raw)
    validate_save(document)
    return document


def save_game(mediator: Any, path: Any) -> FilesystemPath:
    """Serialize and atomically write canonical save bytes to ``path``."""

    payload = canonical_save_bytes(serialize_game(mediator))
    destination = FilesystemPath(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = FilesystemPath(temporary_name)
    handle_opened = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle_opened = True
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if not handle_opened:
            # os.fdopen never returned, so the with block never took ownership
            # of the descriptor and never closed it. Close the raw fd here so a
            # failing fdopen (OOM/EMFILE) cannot leak it and -- on Windows -- so
            # the still-open temporary can be unlinked below without a
            # PermissionError masking the original failure. Tolerate an already
            # closed fd: some fdopen failure paths close it before raising.
            try:
                os.close(descriptor)
            except OSError:
                pass
        temporary.unlink(missing_ok=True)
    return destination

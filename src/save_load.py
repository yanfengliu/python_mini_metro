"""GM-07b loader: strict JSON-to-Mediator reconstruction of save documents.

The loader is fail-closed: every reconstruction step revalidates what it
binds, any failure raises ValueError, and no partially constructed
Mediator ever escapes. Derived state (segments, button assignment, metro
shape color) is rebuilt, never trusted; the bound station-service cache
is restored VERBATIM from the document (including a legitimately stale
cache at the save boundary) and is never re-derived at load, so the next
tick's reconcile behaves exactly like the never-saved game.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path as FilesystemPath
from typing import Any

from config import num_carriages as config_num_carriages
from config import num_metros as config_num_metros
from config import num_paths as config_num_paths
from config import passenger_color, passenger_size, station_color, station_size
from entity.carriage import Carriage
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.point import Point
from geometry.type import ShapeType
from graph.node import Node
from mediator import Mediator
from recursive_checkpoint_schema import safe_checkpoint_value
from save_schema import (
    SAVE_SCHEMA_VERSION_V3,
    SAVE_SCHEMA_VERSION_V4,
    validate_save,
)
from travel_plan import TravelPlan
from utils import get_shape_from_type

__all__ = ["deserialize_game", "load_game"]


def _fail(message: str) -> None:
    raise ValueError(f"save load {message}")


def _require_running_config(document: dict[str, Any]) -> None:
    # numPaths (the total line SLOTS) is pinned for EVERY version -- a NEW_LINE upgrade
    # grows purchased_num_paths, not the ceiling. GM-10h (D-045): v1/v2 strictly reject
    # any fleet divergence (no upgrade mechanism existed, so numMetros != config is
    # corrupt), but v3 may carry a GROWN fleet from a locomotive/carriage upgrade, so
    # numMetros/numCarriages need only be >= config (a total an upgrade only grows; the
    # serialize-time guard already rejected a below-config total before writing). The
    # bonus keys do NOT exist -- the fleet total IS the state -- so there is no v1/v2
    # KeyError. A further relaxation is a future schema version's business (D-026).
    if document["numPaths"] != config_num_paths:
        _fail("numPaths disagrees with the running config")
    # GM-10h relaxed the fleet pin for v3; GM-10i (D-047) EXTENDS it to v4 -- the grown
    # fleet is a v3-and-later capability, so a v4 mid-offer save made AFTER a locomotive/
    # carriage upgrade (numMetros/numCarriages ABOVE config) must load, not be rejected by
    # the legacy exact-equality branch.
    grown_fleet_ok = document["schemaVersion"] in (
        SAVE_SCHEMA_VERSION_V3,
        SAVE_SCHEMA_VERSION_V4,
    )
    for key, expected in (
        ("numMetros", config_num_metros),
        ("numCarriages", config_num_carriages),
    ):
        actual = document[key]
        if grown_fleet_ok:
            if actual < expected:
                _fail(f"{key} is below the running config")
        elif actual != expected:
            _fail(f"{key} disagrees with the running config")


def _restore_rng(mediator: Mediator, rng: dict[str, Any]) -> None:
    python_state = rng["python"]
    try:
        # Deep tuple reconstruction: the outer-tuple-only form raises inside
        # random.setstate, so the inner word list is tuple-ified explicitly.
        mediator.context.python_random.setstate(
            (python_state[0], tuple(python_state[1]), python_state[2])
        )
        mediator.context.numpy_random.bit_generator.state = deepcopy(rng["numpy"])
    except Exception as error:
        # Schema validation pins the numeric domains, so this is a residual
        # guard: any native setter failure keeps the ValueError contract.
        raise ValueError(f"save load rng state is not restorable: {error}") from error


def _restore_stations(
    mediator: Mediator, document: dict[str, Any]
) -> dict[str, Station]:
    stations_by_id: dict[str, Station] = {}
    pool: list[Station] = []
    for record in document["stations"]:
        shape = get_shape_from_type(
            ShapeType(record["shapeType"]), station_color, station_size
        )
        left, top = record["position"]
        station = Station(shape, Point(left, top))
        station.id = record["id"]
        station.capacity = record["capacity"]
        station.unlock_blink_start_time_ms = record["unlockBlinkStartTimeMs"]
        station.snap_blips = [
            (time_ms, tuple(color)) for time_ms, color in record["snapBlips"]
        ]
        pool.append(station)
        stations_by_id[station.id] = station
    mediator.all_stations = pool
    mediator.stations = pool[: document["unlockedNumStations"]]
    steps_since: dict[Station, int] = {}
    intervals: dict[Station, int] = {}
    for identifier, since, interval in document["spawnTimers"]:
        station = stations_by_id[identifier]
        steps_since[station] = since
        intervals[station] = interval
    mediator.station_steps_since_last_spawn = steps_since
    mediator.station_spawn_interval_steps = intervals
    return stations_by_id


def _restore_scalars(mediator: Mediator, document: dict[str, Any]) -> None:
    mediator.num_paths = document["numPaths"]
    mediator.path_unlock_milestones = list(document["pathUnlockMilestones"])
    mediator.path_purchase_prices = list(document["pathPurchasePrices"])
    mediator.num_stations = document["numStations"]
    mediator.initial_num_stations = document["initialNumStations"]
    mediator.station_unlock_milestones = list(document["stationUnlockMilestones"])
    mediator.deliveries = document["deliveries"]
    mediator.line_credits = document["lineCredits"]
    mediator.purchased_num_paths = document["purchasedNumPaths"]
    mediator.unlocked_num_paths = document["unlockedNumPaths"]
    mediator.unlocked_num_stations = document["unlockedNumStations"]
    mediator.num_metros = document["numMetros"]
    mediator.num_carriages = document["numCarriages"]
    # GM-10h: v3 persists the TUNNEL-upgrade bonus; a v1/v2 doc has no such key, so
    # default on ABSENCE. (For this field `.get(...,0)` and `x or 0` happen to agree --
    # 0 is the only falsy valid value -- but `.get` is the clearer form and follows the
    # GM-09f rule that a real falsy persisted value must not be coerced by `or DEFAULT`.)
    mediator.tunnel_bonus = document.get("tunnelBonus", 0)
    mediator.time_ms = document["timeMs"]
    mediator.steps = document["steps"]
    mediator.game_speed_multiplier = document["gameSpeedMultiplier"]
    mediator.is_game_over = document["isGameOver"]
    mediator.passenger_spawning_step = document["passengerSpawningStep"]
    mediator.passenger_spawning_interval_step = document[
        "passengerSpawningIntervalStep"
    ]
    mediator.passenger_max_wait_time_ms = document["passengerMaxWaitTimeMs"]
    mediator.overdue_passenger_threshold = document["overduePassengerThreshold"]
    # Persisted pause reasons restore verbatim; GM-07c owns screen
    # reconciliation and release_pause_reason("menu") is the API lever.
    mediator._pause_reasons = set(document["pauseReasons"])


def _restore_passengers(
    mediator: Mediator, document: dict[str, Any]
) -> dict[str, Passenger]:
    passengers_by_id: dict[str, Passenger] = {}
    riders: list[Passenger] = []
    for record in document["passengers"]:
        shape = get_shape_from_type(
            ShapeType(record["destinationShapeType"]), passenger_color, passenger_size
        )
        passenger = Passenger(shape)
        passenger.id = record["id"]
        passenger.is_at_destination = record["isAtDestination"]
        passenger.wait_ms = record["waitMs"]
        riders.append(passenger)
        passengers_by_id[passenger.id] = passenger
    mediator.passengers = riders
    return passengers_by_id


def _restore_station_queues(
    document: dict[str, Any],
    stations_by_id: dict[str, Station],
    passengers_by_id: dict[str, Passenger],
) -> None:
    for record in document["stations"]:
        station = stations_by_id[record["id"]]
        # D-024 over-capacity queues are canonical, so riders append
        # directly instead of through add_passenger's has_room assertion.
        station.passengers.extend(
            passengers_by_id[identifier] for identifier in record["waitingPassengerIds"]
        )


def _restore_paths(
    mediator: Mediator,
    document: dict[str, Any],
    stations_by_id: dict[str, Station],
) -> dict[str, Path]:
    paths_by_id: dict[str, Path] = {}
    paths: list[Path] = []
    for record in document["paths"]:
        path = Path(tuple(record["color"]))
        path.id = record["id"]
        path.is_looped = record["isLooped"]
        path.path_order = record["pathOrder"]
        path.stations = [
            stations_by_id[identifier] for identifier in record["stationIds"]
        ]
        # Segments rebuild while path.metros is still empty so the metro
        # rebind loop cannot clobber persisted kinematic state.
        path.update_segments()
        paths.append(path)
        paths_by_id[path.id] = path
    mediator.paths = paths
    mediator.path_colors = {
        tuple(color): taken for color, taken in document["pathColors"]
    }
    mediator.path_to_color = {
        paths_by_id[identifier]: tuple(color)
        for identifier, color in document["pathToColor"]
    }
    return paths_by_id


def _restore_metros(
    mediator: Mediator,
    document: dict[str, Any],
    stations_by_id: dict[str, Station],
    paths_by_id: dict[str, Path],
    passengers_by_id: dict[str, Passenger],
) -> None:
    metros: list[Metro] = []
    for record in document["metros"]:
        metro = Metro()
        metro.id = record["id"]
        metro._base_capacity = record["baseCapacity"]
        carriages: list[Carriage] = []
        for entry in record["carriages"]:
            carriage = Carriage()
            carriage.id = entry["id"]
            # The public capacity property is read-only; restore the
            # private field directly.
            carriage._capacity = entry["capacity"]
            carriages.append(carriage)
        metro.carriages = carriages
        left, top = record["position"]
        metro.position = Point(left, top)
        metro.speed = record["speed"]
        metro.max_speed = record["maxSpeed"]
        metro.acceleration_per_ms = record["accelerationPerMs"]
        metro.deceleration_per_ms = record["decelerationPerMs"]
        metro.is_forward = record["isForward"]
        metro.current_segment_idx = record["currentSegmentIdx"]
        metro.stop_time_remaining_ms = record["stopTimeRemainingMs"]
        metro.boarding_progress_ms = record["boardingProgressMs"]
        metro.boarding_time_per_passenger_ms = record["boardingTimePerPassengerMs"]
        metro.just_arrived_and_stopped = record["justArrivedAndStopped"]
        metro.is_unassignment_queued = record["isUnassignmentQueued"]
        metro.path_id = record["pathId"]
        current_station_id = record["currentStationId"]
        metro.current_station = (
            None if current_station_id is None else stations_by_id[current_station_id]
        )
        # The service cache restores VERBATIM (never re-derived): a stale
        # cache at the boundary is real game state whose next-tick
        # reconcile resets boarding progress exactly like the live game.
        action = record["serviceAction"]
        if action is None:
            metro._station_service_action = None
        else:
            passenger_id = action["passengerId"]
            metro._station_service_action = (
                action["kind"],
                None if passenger_id is None else passengers_by_id[passenger_id],
            )
        metro.passengers.extend(
            passengers_by_id[identifier] for identifier in record["onboardPassengerIds"]
        )
        metros.append(metro)
    mediator.metros = metros
    metros_by_id = {metro.id: metro for metro in metros}
    for record in document["paths"]:
        # Manual dual-list binding: add_metro would clobber persisted
        # position, so membership is restored directly in metroIds order.
        paths_by_id[record["id"]].metros.extend(
            metros_by_id[identifier] for identifier in record["metroIds"]
        )
    for metro in metros:
        owner = paths_by_id[metro.path_id]
        if not 0 <= metro.current_segment_idx < len(owner.segments):
            _fail(f"metro {metro.id} currentSegmentIdx is outside its path segments")
        metro.current_segment = owner.segments[metro.current_segment_idx]
        # Re-derive the one visual side effect only add_metro performs;
        # shape.degrees self-corrects on the first tick.
        metro.shape.color = owner.color


def _restore_travel_plans(
    mediator: Mediator,
    document: dict[str, Any],
    stations_by_id: dict[str, Station],
    paths_by_id: dict[str, Path],
    passengers_by_id: dict[str, Passenger],
) -> None:
    for identifier, record in document["travelPlans"].items():
        nodes: list[Node] = []
        for entry in record["nodePath"]:
            node = Node(stations_by_id[entry["stationId"]])
            node.paths = {paths_by_id[path_id] for path_id in entry["pathIds"]}
            nodes.append(node)
        plan = TravelPlan(nodes)
        if record["nextPathId"] is not None:
            plan.next_path = paths_by_id[record["nextPathId"]]
        if record["nextStationId"] is not None:
            plan.next_station = stations_by_id[record["nextStationId"]]
        plan.next_station_idx = record["nextStationIdx"]
        mediator.travel_plans[passengers_by_id[identifier]] = plan


def _restore_buttons(mediator: Mediator, document: dict[str, Any]) -> None:
    # Synchronous rebuild: prepare_layout neither assigns buttons nor
    # re-fires reliably, so assignment happens here, then blink state is
    # restored directly and the persisted lock is validated equal.
    mediator.assign_paths_to_buttons()
    for button, record in zip(
        mediator.path_buttons, document["pathButtons"], strict=True
    ):
        button.unlock_blink_start_time_ms = record["unlockBlinkStartTimeMs"]
        if button.is_locked != record["isLocked"]:
            _fail("pathButtons lock state disagrees with the derived lock state")


def _require_legal_map_state(mediator: Any, map_def: Any) -> None:
    """Reject a state ILLEGAL under its own map (GM-09f, review Codex): every station
    (active + pool) must sit on the map's land, and committed river crossings must not
    exceed the tunnel budget. Tunnel counts are DERIVED (no persisted counter), so this
    needs no stored field -- it refuses a forged/tampered save that a legitimate game
    could never reach (e.g. a CLASSIC state relabeled `river@1`, whose stations are in
    the water). Shared by serialize (pre-save) and deserialize (post-load)."""
    regions = map_def.spawn_regions
    if regions:
        for station in mediator.all_stations:
            x, y = station.position.left, station.position.top
            if not any(
                left <= x <= right and top <= y <= bottom
                for (left, top, right, bottom) in regions
            ):
                raise ValueError(
                    f"map {map_def.map_id!r}: a station at ({round(x)}, {round(y)}) "
                    "is not on the map's land"
                )
    num_tunnels = getattr(mediator, "num_tunnels", None)
    if num_tunnels is not None and mediator.consumed_tunnels > num_tunnels:
        raise ValueError(
            f"map {map_def.map_id!r}: {mediator.consumed_tunnels} river crossings "
            f"exceed the map's tunnel budget of {num_tunnels}"
        )
    # GM-10h: a nonzero TUNNEL bonus is REACHABLE only on a bounded map (CLASSIC never
    # offers TUNNEL and ignores the bonus); reject a forged v3 doc that carries one on
    # an unbounded map -- matches the serialize-time guard so both save surfaces agree.
    tunnel_bonus = getattr(mediator, "tunnel_bonus", 0)
    if tunnel_bonus and map_def.tunnel_budget is None:
        raise ValueError(
            f"map {map_def.map_id!r}: a nonzero tunnel bonus ({tunnel_bonus}) is "
            "unreachable on an unbounded-tunnel map"
        )


def deserialize_game(document: Any) -> Mediator:
    """Reconstruct one Mediator from a validated v1/v2/v3/v4 save document.

    v2 adds the map identity (GM-09f), v3 the fleet/tunnel upgrade totals (GM-10h), and
    v4 a HELD week-boundary offer (GM-10i) -- restored so a mid-offer Continue re-enters
    the modal. Older shapes load unchanged (synthesizing classic@1 / a 0 bonus / no
    pending boundary), so the byte-frozen fixtures stay valid."""

    from maps import resolve_map

    validate_save(document)
    coerced = safe_checkpoint_value(document)
    _require_running_config(coerced)
    # v2 records the map identity; a v1 doc (no map keys) synthesizes classic@1, so the
    # frozen save-v1.json still loads as CLASSIC. resolve_map fails closed on an unknown
    # id / unsupported version -- never a silent fallback to Classic.
    map_definition = resolve_map(
        coerced.get("mapId", "classic"), coerced.get("mapDefinitionVersion", 1)
    )
    mediator = Mediator(seed=0, map_definition=map_definition)
    # Every construction-time draw precedes this overwrite.
    _restore_rng(mediator, coerced["rng"])
    stations_by_id = _restore_stations(mediator, coerced)
    _restore_scalars(mediator, coerced)
    passengers_by_id = _restore_passengers(mediator, coerced)
    _restore_station_queues(coerced, stations_by_id, passengers_by_id)
    paths_by_id = _restore_paths(mediator, coerced, stations_by_id)
    _restore_metros(mediator, coerced, stations_by_id, paths_by_id, passengers_by_id)
    _restore_travel_plans(
        mediator, coerced, stations_by_id, paths_by_id, passengers_by_id
    )
    _restore_buttons(mediator, coerced)
    # The reconstructed state must be legal under its own map (rejects a forged save).
    _require_legal_map_state(mediator, map_definition)
    _restore_pending_offers(mediator, coerced, map_definition)
    return mediator


def _restore_pending_offers(
    mediator: Mediator, document: dict[str, Any], map_def: Any
) -> None:
    # GM-10i (D-047): restore a HELD week boundary's offers VERBATIM from `pendingOffers`
    # (never re-derived -- the derivation inputs WEEK_LENGTH_STEPS/OFFERS_PER_WEEK/pool are
    # provisional balance defaults (GM-11), so a re-derive could diverge from what the save
    # actually showed). The schema already pinned each kind valid+distinct and non-empty
    # exactly when a "week" boundary is held (and not on a finished game). The one map-aware
    # check needs the resolved map: a TUNNEL offer is impossible on an unbounded map (its
    # pool excludes it), so reject it fail-closed like the map-legality guard.
    from offers import OfferKind, describe

    kinds = document.get("pendingOffers", ())
    if not kinds:
        return
    bounded = map_def.tunnel_budget is not None
    restored = []
    for value in kinds:
        kind = OfferKind(value)
        if kind is OfferKind.TUNNEL and not bounded:
            raise ValueError(
                f"cannot load a TUNNEL offer on the unbounded map {map_def.map_id!r}: "
                "its offer pool excludes TUNNEL"
            )
        restored.append(describe(kind))
    mediator.current_offers = tuple(restored)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    # Default json.loads collapses duplicate keys before exact-key
    # validation ever sees them; strict loading rejects every level.
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"save file repeats the JSON object key {key!r}")
        mapping[key] = value
    return mapping


def load_game(path: Any) -> Mediator:
    """Read, strictly validate, and deserialize one save file."""

    payload = FilesystemPath(path).read_bytes()
    try:
        document = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ValueError(f"save file is not valid JSON: {error}") from error
    validate_save(document)
    return deserialize_game(document)

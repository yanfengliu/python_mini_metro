"""GM-07b save-schema v1 record sections: entities, references, colors.

Split out of ``save_schema`` to keep both modules under the size budget;
``save_schema.validate_save`` composes these section validators and owns
the public schema surface. Every rejection raises ValueError.
"""

from __future__ import annotations

from typing import Any

from geometry.type import ShapeType
from passenger_capacity import BOARD, DESTINATION, TRANSFER

_SHORTUUID_ALPHABET = frozenset(
    "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
)
_SHORTUUID_LENGTH = 22
_STATION_SHAPE_BY_LITERAL = {str(member): member.value for member in ShapeType}
_SHAPE_TYPE_VALUES = frozenset(member.value for member in ShapeType)
_SERVICE_ACTION_KINDS = frozenset({DESTINATION, TRANSFER, BOARD})
_PATH_ORDER_BOUND = 32

_STATION_KEYS = frozenset(
    """id position shapeType active capacity waitingPassengerIds
    unlockBlinkStartTimeMs snapBlips""".split()
)
_PASSENGER_KEYS = frozenset("id destinationShapeType isAtDestination waitMs".split())
_PATH_KEYS = frozenset("id color stationIds metroIds isLooped pathOrder".split())
_METRO_KEYS = frozenset(
    """id pathId position currentSegmentIdx currentStationId isForward
    speed maxSpeed accelerationPerMs decelerationPerMs
    stopTimeRemainingMs boardingProgressMs boardingTimePerPassengerMs
    justArrivedAndStopped isUnassignmentQueued baseCapacity
    serviceAction carriages onboardPassengerIds""".split()
)
_SERVICE_ACTION_KEYS = frozenset("kind passengerId".split())
_CARRIAGE_KEYS = frozenset("id capacity".split())
_TRAVEL_PLAN_KEYS = frozenset(
    "nextPathId nextStationId nextStationIdx nodePath".split()
)
_NODE_KEYS = frozenset("stationId pathIds".split())


def _fail(label: str, message: str) -> None:
    raise ValueError(f"save {label} {message}")


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(label, "must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        _fail(label, "must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if type(value) is not str:
        _fail(label, "must be a string")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        _fail(label, "must be a boolean")
    return value


def _int(value: Any, label: str) -> int:
    if type(value) is not int:
        _fail(label, "must be an integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if _int(value, label) < 0:
        _fail(label, "must be nonnegative")
    return value


def _positive_int(value: Any, label: str) -> int:
    if _int(value, label) <= 0:
        _fail(label, "must be positive")
    return value


def _number(value: Any, label: str) -> float:
    if type(value) not in (int, float):
        _fail(label, "must be a number")
    return value


def _nonnegative_number(value: Any, label: str) -> float:
    if _number(value, label) < 0:
        _fail(label, "must be nonnegative")
    return value


def _positive_number(value: Any, label: str) -> float:
    if _number(value, label) <= 0:
        _fail(label, "must be positive")
    return value


def _optional(validator: Any, value: Any, label: str) -> Any:
    if value is None:
        return None
    return validator(value, label)


def _exact_keys(mapping: dict[str, Any], keys: frozenset[str], label: str) -> None:
    actual = set(mapping)
    if actual != keys:
        unknown = sorted(actual - keys)
        missing = sorted(keys - actual)
        _fail(label, f"has wrong keys (unknown {unknown}, missing {missing})")


def _color(value: Any, label: str) -> tuple[float, ...]:
    if type(value) is not list or len(value) != 3:
        _fail(label, "must be an [r, g, b] array")
    return tuple(
        float(_number(part, f"{label}[{index}]")) for index, part in enumerate(value)
    )


def _point(value: Any, label: str) -> None:
    if type(value) is not list or len(value) != 2:
        _fail(label, "must be a [left, top] array")
    for index, part in enumerate(value):
        _number(part, f"{label}[{index}]")


def _uuid_token(token: str, label: str) -> None:
    if len(token) != _SHORTUUID_LENGTH or not set(token) <= _SHORTUUID_ALPHABET:
        _fail(label, "must embed one 22-character base57 token")


def _plain_id(value: Any, prefix: str, label: str) -> str:
    _string(value, label)
    if not value.startswith(prefix):
        _fail(label, f"must use the {prefix} ID prefix")
    _uuid_token(value[len(prefix) :], label)
    return value


def _station_id(value: Any, label: str) -> str:
    """Validate one station ID and return its embedded shape-type value."""

    _string(value, label)
    prefix = "Station-"
    if not value.startswith(prefix):
        _fail(label, f"must use the {prefix} ID prefix")
    remainder = value[len(prefix) :]
    _uuid_token(remainder[:_SHORTUUID_LENGTH], label)
    literal = remainder[_SHORTUUID_LENGTH:]
    if not literal.startswith("-") or literal[1:] not in _STATION_SHAPE_BY_LITERAL:
        _fail(label, "must end with a known ShapeType literal")
    return _STATION_SHAPE_BY_LITERAL[literal[1:]]


def _register(registry: set[str], identifier: str, label: str) -> None:
    if identifier in registry:
        _fail(label, "duplicates another entity ID")
    registry.add(identifier)


def _reference(identifier: Any, pool: set[str], label: str) -> str:
    _string(identifier, label)
    if identifier not in pool:
        _fail(label, "does not resolve to a live entity")
    return identifier


def validate_station_records(document: dict[str, Any], registry: set[str]) -> list[str]:
    records = _array(document["stations"], "stations")
    if len(records) != document["numStations"]:
        _fail("stations", "must hold exactly numStations records")
    unlocked = document["unlockedNumStations"]
    identifiers: list[str] = []
    for index, item in enumerate(records):
        label = f"stations[{index}]"
        record = _object(item, label)
        _exact_keys(record, _STATION_KEYS, label)
        shape_value = _station_id(record["id"], f"{label}.id")
        _register(registry, record["id"], f"{label}.id")
        identifiers.append(record["id"])
        _point(record["position"], f"{label}.position")
        declared = _string(record["shapeType"], f"{label}.shapeType")
        if declared not in _SHAPE_TYPE_VALUES or declared != shape_value:
            _fail(f"{label}.shapeType", "disagrees with the station ID shape literal")
        if _bool(record["active"], f"{label}.active") != (index < unlocked):
            _fail(f"{label}.active", "disagrees with the unlocked-station prefix")
        _positive_int(record["capacity"], f"{label}.capacity")
        waiting = _array(record["waitingPassengerIds"], f"{label}.waitingPassengerIds")
        for slot, rider in enumerate(waiting):
            _string(rider, f"{label}.waitingPassengerIds[{slot}]")
        _optional(
            _nonnegative_int,
            record["unlockBlinkStartTimeMs"],
            f"{label}.unlockBlinkStartTimeMs",
        )
        for slot, blip in enumerate(_array(record["snapBlips"], f"{label}.snapBlips")):
            blip_label = f"{label}.snapBlips[{slot}]"
            if type(blip) is not list or len(blip) != 2:
                _fail(blip_label, "must be a [timeMs, color] pair")
            _nonnegative_int(blip[0], f"{blip_label}[0]")
            _color(blip[1], f"{blip_label}[1]")
    return identifiers


def validate_passenger_records(
    document: dict[str, Any], registry: set[str]
) -> list[str]:
    identifiers: list[str] = []
    for index, item in enumerate(_array(document["passengers"], "passengers")):
        label = f"passengers[{index}]"
        record = _object(item, label)
        _exact_keys(record, _PASSENGER_KEYS, label)
        _plain_id(record["id"], "Passenger-", f"{label}.id")
        _register(registry, record["id"], f"{label}.id")
        identifiers.append(record["id"])
        shape = _string(record["destinationShapeType"], f"{label}.destinationShapeType")
        if shape not in _SHAPE_TYPE_VALUES:
            _fail(f"{label}.destinationShapeType", "is not a known shape type")
        _bool(record["isAtDestination"], f"{label}.isAtDestination")
        _nonnegative_int(record["waitMs"], f"{label}.waitMs")
    return identifiers


def validate_path_records(document: dict[str, Any], registry: set[str]) -> list[str]:
    records = _array(document["paths"], "paths")
    if len(records) > document["unlockedNumPaths"]:
        _fail("paths", "must not exceed unlockedNumPaths")
    identifiers: list[str] = []
    for index, item in enumerate(records):
        label = f"paths[{index}]"
        record = _object(item, label)
        _exact_keys(record, _PATH_KEYS, label)
        _plain_id(record["id"], "Path-", f"{label}.id")
        _register(registry, record["id"], f"{label}.id")
        identifiers.append(record["id"])
        _color(record["color"], f"{label}.color")
        stations = _array(record["stationIds"], f"{label}.stationIds")
        if len(stations) < 2:
            _fail(f"{label}.stationIds", "must reference at least two stations")
        for slot, station in enumerate(stations):
            _string(station, f"{label}.stationIds[{slot}]")
            if slot and station == stations[slot - 1]:
                _fail(f"{label}.stationIds[{slot}]", "repeats the previous station")
        for slot, metro in enumerate(_array(record["metroIds"], f"{label}.metroIds")):
            _string(metro, f"{label}.metroIds[{slot}]")
        looped = _bool(record["isLooped"], f"{label}.isLooped")
        if looped and stations[0] == stations[-1]:
            _fail(f"{label}.stationIds", "repeats the loop endpoint station")
        order = _int(record["pathOrder"], f"{label}.pathOrder")
        if not -_PATH_ORDER_BOUND <= order <= _PATH_ORDER_BOUND:
            _fail(f"{label}.pathOrder", "is outside the sane path-order range")
    return identifiers


def _validate_service_action(record: dict[str, Any], label: str) -> None:
    """Validate the persisted bound service cache against the live invariant.

    A bound action requires an at-station metro at speed zero with timers
    on the boarding invariant; an unbound cache requires exactly (0, 0).
    The cache may legitimately disagree with the re-derivable action (the
    stale-reset boundary), so no derivation happens here or at load.
    """

    action = record["serviceAction"]
    stop_time = record["stopTimeRemainingMs"]
    progress = record["boardingProgressMs"]
    if action is None:
        if stop_time != 0 or progress != 0:
            _fail(f"{label}.serviceAction", "must be bound when timers are nonzero")
        return
    action_label = f"{label}.serviceAction"
    bound = _object(action, action_label)
    _exact_keys(bound, _SERVICE_ACTION_KEYS, action_label)
    if _string(bound["kind"], f"{action_label}.kind") not in _SERVICE_ACTION_KINDS:
        _fail(f"{action_label}.kind", "is not a known service-action kind")
    _optional(_string, bound["passengerId"], f"{action_label}.passengerId")
    if record["currentStationId"] is None:
        _fail(action_label, "requires the Metro to be at a station")
    if record["speed"] != 0:
        _fail(f"{label}.speed", "must be zero while a service action is bound")
    interval = record["boardingTimePerPassengerMs"]
    if not 0 <= progress < interval or stop_time != interval - progress:
        _fail(f"{label}.serviceAction", "timers violate the boarding invariant")


def validate_metro_records(document: dict[str, Any], registry: set[str]) -> list[str]:
    identifiers: list[str] = []
    for index, item in enumerate(_array(document["metros"], "metros")):
        label = f"metros[{index}]"
        record = _object(item, label)
        _exact_keys(record, _METRO_KEYS, label)
        _plain_id(record["id"], "Metro-", f"{label}.id")
        _register(registry, record["id"], f"{label}.id")
        identifiers.append(record["id"])
        _string(record["pathId"], f"{label}.pathId")
        _point(record["position"], f"{label}.position")
        _nonnegative_int(record["currentSegmentIdx"], f"{label}.currentSegmentIdx")
        _optional(_string, record["currentStationId"], f"{label}.currentStationId")
        _bool(record["isForward"], f"{label}.isForward")
        _nonnegative_number(record["speed"], f"{label}.speed")
        _positive_number(record["maxSpeed"], f"{label}.maxSpeed")
        _positive_number(record["accelerationPerMs"], f"{label}.accelerationPerMs")
        _positive_number(record["decelerationPerMs"], f"{label}.decelerationPerMs")
        _nonnegative_int(record["stopTimeRemainingMs"], f"{label}.stopTimeRemainingMs")
        _nonnegative_int(record["boardingProgressMs"], f"{label}.boardingProgressMs")
        _positive_int(
            record["boardingTimePerPassengerMs"], f"{label}.boardingTimePerPassengerMs"
        )
        _bool(record["justArrivedAndStopped"], f"{label}.justArrivedAndStopped")
        _bool(record["isUnassignmentQueued"], f"{label}.isUnassignmentQueued")
        _validate_service_action(record, label)
        capacity = _nonnegative_int(record["baseCapacity"], f"{label}.baseCapacity")
        for slot, entry in enumerate(_array(record["carriages"], f"{label}.carriages")):
            carriage_label = f"{label}.carriages[{slot}]"
            carriage = _object(entry, carriage_label)
            _exact_keys(carriage, _CARRIAGE_KEYS, carriage_label)
            _plain_id(carriage["id"], "Carriage-", f"{carriage_label}.id")
            _register(registry, carriage["id"], f"{carriage_label}.id")
            capacity += _positive_int(
                carriage["capacity"], f"{carriage_label}.capacity"
            )
        onboard = _array(record["onboardPassengerIds"], f"{label}.onboardPassengerIds")
        for slot, rider in enumerate(onboard):
            _string(rider, f"{label}.onboardPassengerIds[{slot}]")
        if len(onboard) > capacity:
            _fail(f"{label}.onboardPassengerIds", "exceeds the derived Metro capacity")
    return identifiers


def _validate_locations(document: dict[str, Any], passengers: list[str]) -> None:
    counts = {identifier: 0 for identifier in passengers}
    holders = [
        (f"stations[{index}].waitingPassengerIds", record["waitingPassengerIds"])
        for index, record in enumerate(document["stations"])
    ] + [
        (f"metros[{index}].onboardPassengerIds", record["onboardPassengerIds"])
        for index, record in enumerate(document["metros"])
    ]
    for label, riders in holders:
        for slot, rider in enumerate(riders):
            if rider not in counts:
                _fail(f"{label}[{slot}]", "does not resolve to a live passenger")
            counts[rider] += 1
            if counts[rider] > 1:
                _fail(f"{label}[{slot}]", "locates one passenger more than once")
    for identifier, count in counts.items():
        if count == 0:
            _fail("passengers", f"{identifier} is not located in any holder")


def validate_references(
    document: dict[str, Any],
    stations: list[str],
    passengers: list[str],
    paths: list[str],
    metros: list[str],
) -> None:
    station_pool = set(stations)
    # Graph construction and metro binding consume only the unlocked
    # prefix, so graph-consumed references must resolve to ACTIVE stations.
    active_pool = set(stations[: document["unlockedNumStations"]])
    passenger_pool = set(passengers)
    path_pool = set(paths)
    metro_pool = set(metros)
    owner_by_metro: dict[str, str] = {}
    stations_by_path: dict[str, set[str]] = {}
    for index, record in enumerate(document["paths"]):
        label = f"paths[{index}]"
        for slot, station in enumerate(record["stationIds"]):
            _reference(station, station_pool, f"{label}.stationIds[{slot}]")
            if station not in active_pool:
                _fail(f"{label}.stationIds[{slot}]", "references a locked station")
        stations_by_path[record["id"]] = set(record["stationIds"])
        for slot, metro in enumerate(record["metroIds"]):
            _reference(metro, metro_pool, f"{label}.metroIds[{slot}]")
            if metro in owner_by_metro:
                _fail(f"{label}.metroIds[{slot}]", "assigns one Metro to two paths")
            owner_by_metro[metro] = record["id"]
    for index, record in enumerate(document["metros"]):
        label = f"metros[{index}]"
        _reference(record["pathId"], path_pool, f"{label}.pathId")
        if owner_by_metro.get(record["id"]) != record["pathId"]:
            _fail(f"{label}.pathId", "disagrees with the owning path's metroIds")
        current = record["currentStationId"]
        if current is not None:
            _reference(current, active_pool, f"{label}.currentStationId")
            if current not in stations_by_path[record["pathId"]]:
                _fail(f"{label}.currentStationId", "is not on the owning path")
        action = record["serviceAction"]
        if action is not None and action["passengerId"] is not None:
            _reference(
                action["passengerId"],
                passenger_pool,
                f"{label}.serviceAction.passengerId",
            )
    _validate_locations(document, passengers)
    plans = _object(document["travelPlans"], "travelPlans")
    for key, item in plans.items():
        label = f"travelPlans[{key}]"
        _plain_id(key, "Passenger-", f"{label} key")
        _reference(key, passenger_pool, f"{label} key")
        plan = _object(item, label)
        _exact_keys(plan, _TRAVEL_PLAN_KEYS, label)
        if plan["nextPathId"] is not None:
            _reference(plan["nextPathId"], path_pool, f"{label}.nextPathId")
        if plan["nextStationId"] is not None:
            _reference(plan["nextStationId"], station_pool, f"{label}.nextStationId")
        nodes = _array(plan["nodePath"], f"{label}.nodePath")
        cursor = _nonnegative_int(plan["nextStationIdx"], f"{label}.nextStationIdx")
        if (nodes and cursor >= len(nodes)) or (not nodes and cursor != 0):
            _fail(f"{label}.nextStationIdx", "is outside the node path")
        for slot, entry in enumerate(nodes):
            node_label = f"{label}.nodePath[{slot}]"
            node = _object(entry, node_label)
            _exact_keys(node, _NODE_KEYS, node_label)
            _reference(node["stationId"], station_pool, f"{node_label}.stationId")
            node_paths = _array(node["pathIds"], f"{node_label}.pathIds")
            for path_slot, path in enumerate(node_paths):
                _reference(path, path_pool, f"{node_label}.pathIds[{path_slot}]")
            if len(set(node_paths)) != len(node_paths):
                _fail(f"{node_label}.pathIds", "must not repeat a path")


def validate_color_allocation(document: dict[str, Any]) -> None:
    flags: dict[tuple[float, ...], bool] = {}
    pairs = _array(document["pathColors"], "pathColors")
    if len(pairs) != document["numPaths"]:
        _fail("pathColors", "must hold one color slot per path")
    for index, pair in enumerate(pairs):
        label = f"pathColors[{index}]"
        if type(pair) is not list or len(pair) != 2:
            _fail(label, "must be a [color, taken] pair")
        color = _color(pair[0], f"{label}[0]")
        if color in flags:
            _fail(f"{label}[0]", "duplicates another color slot")
        flags[color] = _bool(pair[1], f"{label}[1]")
    path_colors = {
        record["id"]: _color(record["color"], f"paths[{index}].color")
        for index, record in enumerate(document["paths"])
    }
    assigned: dict[str, tuple[float, ...]] = {}
    for index, pair in enumerate(_array(document["pathToColor"], "pathToColor")):
        label = f"pathToColor[{index}]"
        if type(pair) is not list or len(pair) != 2:
            _fail(label, "must be a [pathId, color] pair")
        identifier = _reference(pair[0], set(path_colors), f"{label}[0]")
        if identifier in assigned:
            _fail(f"{label}[0]", "assigns one path twice")
        color = _color(pair[1], f"{label}[1]")
        if color != path_colors[identifier]:
            _fail(f"{label}[1]", "disagrees with the path's own color")
        if not flags.get(color, False):
            _fail(f"{label}[1]", "is not marked taken in pathColors")
        assigned[identifier] = color
    if set(assigned) != set(path_colors):
        _fail("pathToColor", "must assign every live path exactly once")
    taken = {color for color, flag in flags.items() if flag}
    values = list(assigned.values())
    if len(set(values)) != len(values) or taken != set(values):
        _fail("pathColors", "taken flags disagree with assigned path colors")

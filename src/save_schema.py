"""GM-07b save-document schema v1: strict fail-closed validation and bytes.

The save schema deliberately retains real entity ID strings, so the
UUID-free checkpoint validators are never reused here; the checkpoint
verifier stays one-way and this module only shares its safe value
coercion so serialized documents use exact plain JSON scalar types.
Record-section and reference validation lives in ``save_schema_records``.
"""

from __future__ import annotations

import json
from typing import Any

from recursive_checkpoint_schema import safe_checkpoint_value
from save_schema_records import (
    _array,
    _bool,
    _exact_keys,
    _fail,
    _int,
    _nonnegative_int,
    _number,
    _object,
    _optional,
    _positive_int,
    _reference,
    _string,
    validate_color_allocation,
    validate_metro_records,
    validate_passenger_records,
    validate_path_records,
    validate_references,
    validate_station_records,
)

SAVE_SCHEMA_VERSION_V1 = 1
# GM-09f: v2 is a strict SUPERSET of v1 -- it adds an additive map identity
# (`mapId`/`mapDefinitionVersion`) so a non-Classic map (river/delta/lake) can be
# saved/loaded. A v1 document (no map keys) still loads by synthesizing `classic@1`,
# so the byte-frozen `save-v1.json` stays valid. New saves are v2. `stateContract`
# and `rulesVersion` are STABLE across v1/v2 -- only `schemaVersion` and the two map
# keys change (D-038).
SAVE_SCHEMA_VERSION_V2 = 2
SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V2
SUPPORTED_SAVE_SCHEMA_VERSIONS = {SAVE_SCHEMA_VERSION_V1, SAVE_SCHEMA_VERSION_V2}
SAVE_STATE_CONTRACT = "mini-metro-save-v1"
SAVE_RULES_VERSION = "rules-v1"

_PAUSE_REASON_VOCABULARY = frozenset({"menu", "user"})
_GAME_SPEED_MULTIPLIERS = frozenset({1, 2, 4})
_PYTHON_RNG_VERSION = 3
_PYTHON_RNG_WORDS = 625
_PYTHON_RNG_WORD_BOUND = 2**32
_PYTHON_RNG_INDEX_MAX = 624
_NUMPY_BIT_GENERATOR = "PCG64"
_PCG64_STATE_BOUND = 2**128
_UINT32_BOUND = 2**32

_TOP_LEVEL_KEYS_V1 = frozenset(
    """schemaVersion stateContract rulesVersion timeMs steps gameSpeedMultiplier
    isGameOver pauseReasons passengerSpawningStep passengerSpawningIntervalStep
    passengerMaxWaitTimeMs overduePassengerThreshold deliveries lineCredits
    purchasedNumPaths unlockedNumPaths unlockedNumStations numPaths numStations
    initialNumStations pathPurchasePrices pathUnlockMilestones
    stationUnlockMilestones numMetros numCarriages stations passengers paths
    metros travelPlans pathColors pathToColor spawnTimers pathButtons rng""".split()
)
# GM-09f: v2 adds exactly the two map-identity keys; the exact-key set is chosen by
# the document's schemaVersion, so a v1 doc carrying map keys OR a v2 doc missing
# them both fail closed.
_MAP_IDENTITY_KEYS = frozenset({"mapId", "mapDefinitionVersion"})
_TOP_LEVEL_KEYS_V2 = _TOP_LEVEL_KEYS_V1 | _MAP_IDENTITY_KEYS


def _top_level_keys_for(version: int) -> frozenset[str]:
    if version == SAVE_SCHEMA_VERSION_V2:
        return _TOP_LEVEL_KEYS_V2
    return _TOP_LEVEL_KEYS_V1


_PATH_BUTTON_KEYS = frozenset("isLocked unlockBlinkStartTimeMs".split())
_RNG_KEYS = frozenset("python numpy".split())
_NUMPY_RNG_KEYS = frozenset("bit_generator state has_uint32 uinteger".split())
_NUMPY_RNG_STATE_KEYS = frozenset("state inc".split())


def _read_schema_version(document: dict[str, Any]) -> int:
    """Read + validate `schemaVersion` BEFORE the exact-key set is chosen (GM-09f).

    A missing key fails with a named ValueError (never a KeyError from a later
    exact-key check), a non-exact-int (incl. bool) is rejected by `_int`, and a
    forward version is rejected -- so the key set is only selected for a supported
    version."""
    if "schemaVersion" not in document:
        _fail("schemaVersion", "is required")
    version = _int(document["schemaVersion"], "schemaVersion")
    if version not in SUPPORTED_SAVE_SCHEMA_VERSIONS:
        _fail("schemaVersion", "is unsupported (forward versions are rejected)")
    return version


def _validate_header(document: dict[str, Any]) -> None:
    # schemaVersion is validated up front by _read_schema_version; the contract and
    # rules version are STABLE across v1/v2 (only the additive map keys differ).
    if _string(document["stateContract"], "stateContract") != SAVE_STATE_CONTRACT:
        _fail("stateContract", f"must be {SAVE_STATE_CONTRACT!r}")
    if _string(document["rulesVersion"], "rulesVersion") != SAVE_RULES_VERSION:
        _fail("rulesVersion", f"must be {SAVE_RULES_VERSION!r}")


def _validate_map_identity(document: dict[str, Any]) -> None:
    """Validate the v2 map-identity scalars (GM-09f): a non-empty ASCII `mapId` with no
    whitespace + a positive non-bool `mapDefinitionVersion`. Well-typed but UNKNOWN ids
    are deferred to `resolve_map` at load (fail-closed there); this pins the SHAPE, a
    true mirror of `rl.manifest_schema._validate_map_identity` (registry ids are ASCII
    and whitespace-free, so this only rejects a hand-forged doc -- D-038)."""
    map_id = _string(document["mapId"], "mapId")
    if not map_id:
        _fail("mapId", "must be a non-empty string")
    if not map_id.isascii():
        _fail("mapId", "must be ASCII")
    if any(character.isspace() for character in map_id):
        _fail("mapId", "must not contain whitespace")
    _positive_int(document["mapDefinitionVersion"], "mapDefinitionVersion")


def _validate_scalars(document: dict[str, Any]) -> None:
    _nonnegative_int(document["timeMs"], "timeMs")
    _nonnegative_int(document["steps"], "steps")
    speed = _int(document["gameSpeedMultiplier"], "gameSpeedMultiplier")
    if speed not in _GAME_SPEED_MULTIPLIERS:
        _fail("gameSpeedMultiplier", "must be 1, 2, or 4")
    _bool(document["isGameOver"], "isGameOver")
    _nonnegative_int(document["passengerSpawningStep"], "passengerSpawningStep")
    _nonnegative_int(
        document["passengerSpawningIntervalStep"], "passengerSpawningIntervalStep"
    )
    _nonnegative_int(document["passengerMaxWaitTimeMs"], "passengerMaxWaitTimeMs")
    _nonnegative_int(document["overduePassengerThreshold"], "overduePassengerThreshold")
    _nonnegative_int(document["numMetros"], "numMetros")
    _nonnegative_int(document["numCarriages"], "numCarriages")
    reasons = _array(document["pauseReasons"], "pauseReasons")
    for index, reason in enumerate(reasons):
        if _string(reason, f"pauseReasons[{index}]") not in _PAUSE_REASON_VOCABULARY:
            _fail(f"pauseReasons[{index}]", "is not a known pause reason")
    if any(left >= right for left, right in zip(reasons, reasons[1:])):
        _fail("pauseReasons", "must be strictly sorted without duplicates")


def _validate_progression(document: dict[str, Any]) -> None:
    _nonnegative_int(document["deliveries"], "deliveries")
    _nonnegative_int(document["lineCredits"], "lineCredits")
    num_paths = _positive_int(document["numPaths"], "numPaths")
    num_stations = _positive_int(document["numStations"], "numStations")
    initial = _positive_int(document["initialNumStations"], "initialNumStations")
    if initial > num_stations:
        _fail("initialNumStations", "must not exceed numStations")
    purchased = _positive_int(document["purchasedNumPaths"], "purchasedNumPaths")
    unlocked_paths = _positive_int(document["unlockedNumPaths"], "unlockedNumPaths")
    if unlocked_paths != min(max(1, purchased), num_paths):
        _fail("unlockedNumPaths", "disagrees with purchasedNumPaths")
    path_milestones = _array(document["pathUnlockMilestones"], "pathUnlockMilestones")
    if len(path_milestones) != num_paths:
        _fail("pathUnlockMilestones", "must hold one milestone per path")
    for index, milestone in enumerate(path_milestones):
        _nonnegative_int(milestone, f"pathUnlockMilestones[{index}]")
    if any(a > b for a, b in zip(path_milestones, path_milestones[1:])):
        _fail("pathUnlockMilestones", "must be sorted")
    prices = _array(document["pathPurchasePrices"], "pathPurchasePrices")
    expected_prices = [
        path_milestones[index] - path_milestones[index - 1]
        for index in range(1, num_paths)
    ]
    if prices != expected_prices:
        _fail("pathPurchasePrices", "disagrees with pathUnlockMilestones")
    station_milestones = _array(
        document["stationUnlockMilestones"], "stationUnlockMilestones"
    )
    if len(station_milestones) != num_stations - initial:
        _fail("stationUnlockMilestones", "must hold one milestone per locked station")
    for index, milestone in enumerate(station_milestones):
        _nonnegative_int(milestone, f"stationUnlockMilestones[{index}]")
    if any(a > b for a, b in zip(station_milestones, station_milestones[1:])):
        _fail("stationUnlockMilestones", "must be sorted")
    unlocked_stations = _positive_int(
        document["unlockedNumStations"], "unlockedNumStations"
    )
    deliveries = document["deliveries"]
    reached = sum(1 for milestone in station_milestones if deliveries >= milestone)
    if unlocked_stations != min(initial + reached, num_stations):
        _fail("unlockedNumStations", "disagrees with deliveries and milestones")


def _validate_spawn_timers(document: dict[str, Any], stations: list[str]) -> None:
    pool = set(stations)
    seen: set[str] = set()
    for index, entry in enumerate(_array(document["spawnTimers"], "spawnTimers")):
        label = f"spawnTimers[{index}]"
        if type(entry) is not list or len(entry) != 3:
            _fail(label, "must be a [stationId, stepsSince, intervalSteps] triple")
        identifier = _reference(entry[0], pool, f"{label}[0]")
        if identifier in seen:
            _fail(f"{label}[0]", "covers one station twice")
        seen.add(identifier)
        _nonnegative_int(entry[1], f"{label}[1]")
        _positive_int(entry[2], f"{label}[2]")
    if seen != pool:
        _fail("spawnTimers", "must cover every pool station exactly once")


def _validate_buttons(document: dict[str, Any]) -> None:
    records = _array(document["pathButtons"], "pathButtons")
    if len(records) != document["numPaths"]:
        _fail("pathButtons", "must hold one slot per path")
    unlocked = document["unlockedNumPaths"]
    for index, item in enumerate(records):
        label = f"pathButtons[{index}]"
        record = _object(item, label)
        _exact_keys(record, _PATH_BUTTON_KEYS, label)
        if _bool(record["isLocked"], f"{label}.isLocked") != (index >= unlocked):
            _fail(f"{label}.isLocked", "disagrees with unlockedNumPaths")
        _optional(
            _nonnegative_int,
            record["unlockBlinkStartTimeMs"],
            f"{label}.unlockBlinkStartTimeMs",
        )


def _validate_rng(document: dict[str, Any]) -> None:
    rng = _object(document["rng"], "rng")
    _exact_keys(rng, _RNG_KEYS, "rng")
    python_state = _array(rng["python"], "rng.python")
    if len(python_state) != 3:
        _fail("rng.python", "must be a [version, words, gauss] triple")
    if _int(python_state[0], "rng.python[0]") != _PYTHON_RNG_VERSION:
        _fail("rng.python[0]", "must be Mersenne Twister state version 3")
    words = _array(python_state[1], "rng.python[1]")
    if len(words) != _PYTHON_RNG_WORDS:
        _fail("rng.python[1]", "must hold exactly 625 state words")
    for index, word in enumerate(words[:-1]):
        if not 0 <= _int(word, f"rng.python[1][{index}]") < _PYTHON_RNG_WORD_BOUND:
            _fail(f"rng.python[1][{index}]", "is outside the 32-bit word domain")
    position_label = f"rng.python[1][{_PYTHON_RNG_WORDS - 1}]"
    if not 0 <= _int(words[-1], position_label) <= _PYTHON_RNG_INDEX_MAX:
        _fail(position_label, "is outside the Mersenne Twister index domain")
    if python_state[2] is not None:
        _number(python_state[2], "rng.python[2]")
    numpy_state = _object(rng["numpy"], "rng.numpy")
    _exact_keys(numpy_state, _NUMPY_RNG_KEYS, "rng.numpy")
    generator = _string(numpy_state["bit_generator"], "rng.numpy.bit_generator")
    if generator != _NUMPY_BIT_GENERATOR:
        _fail("rng.numpy.bit_generator", f"must be {_NUMPY_BIT_GENERATOR!r}")
    inner = _object(numpy_state["state"], "rng.numpy.state")
    _exact_keys(inner, _NUMPY_RNG_STATE_KEYS, "rng.numpy.state")
    for key in ("state", "inc"):
        if not 0 <= _int(inner[key], f"rng.numpy.state.{key}") < _PCG64_STATE_BOUND:
            _fail(f"rng.numpy.state.{key}", "is outside the 128-bit PCG64 domain")
    if _int(numpy_state["has_uint32"], "rng.numpy.has_uint32") not in (0, 1):
        _fail("rng.numpy.has_uint32", "must be exactly 0 or 1")
    if not 0 <= _int(numpy_state["uinteger"], "rng.numpy.uinteger") < _UINT32_BOUND:
        _fail("rng.numpy.uinteger", "is outside the 32-bit cache domain")


def validate_save(document: Any) -> None:
    """Strictly validate one save document; any rejection raises ValueError."""

    if type(document) is not dict:
        raise ValueError("save document must be an object")
    try:
        coerced = safe_checkpoint_value(document)
    except TypeError as error:
        raise ValueError(f"save document holds unsupported values: {error}") from error
    # GM-09f two-phase: read + support-check the version, THEN choose the version-aware
    # exact-key set, so a v1 doc carrying map keys and a v2 doc missing them both fail.
    version = _read_schema_version(coerced)
    _exact_keys(coerced, _top_level_keys_for(version), "document")
    _validate_header(coerced)
    if version == SAVE_SCHEMA_VERSION_V2:
        _validate_map_identity(coerced)
    _validate_scalars(coerced)
    _validate_progression(coerced)
    registry: set[str] = set()
    stations = validate_station_records(coerced, registry)
    passengers = validate_passenger_records(coerced, registry)
    paths = validate_path_records(coerced, registry)
    metros = validate_metro_records(coerced, registry)
    validate_references(coerced, stations, passengers, paths, metros)
    validate_color_allocation(coerced)
    _validate_spawn_timers(coerced, stations)
    _validate_buttons(coerced)
    _validate_rng(coerced)


def canonical_save_bytes(document: Any) -> bytes:
    """Encode one save document with the pinned ASCII recipe plus trailing LF."""

    coerced = safe_checkpoint_value(document)
    payload = json.dumps(
        coerced,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return payload.encode("ascii") + b"\n"

"""GM-07b save-schema v1 strictness reds minting the save-document contract."""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
SAVE_SCHEMA_MODULE = "save_schema"
SAVE_GAME_MODULE = "save_game"
UNKNOWN_STATION_ID = "Station-" + "2" * 22 + "-ShapeType.RECT"
UNKNOWN_PASSENGER_ID = "Passenger-" + "2" * 22
UNKNOWN_PATH_ID = "Path-" + "2" * 22
TOP_LEVEL_KEYS = frozenset(
    """schemaVersion stateContract rulesVersion timeMs steps gameSpeedMultiplier
    isGameOver pauseReasons passengerSpawningStep passengerSpawningIntervalStep
    passengerMaxWaitTimeMs overduePassengerThreshold deliveries lineCredits
    purchasedNumPaths unlockedNumPaths unlockedNumStations numPaths numStations
    initialNumStations pathPurchasePrices pathUnlockMilestones
    stationUnlockMilestones numMetros numCarriages stations passengers paths
    metros travelPlans pathColors pathToColor spawnTimers pathButtons rng""".split()
)
STATION_KEYS = frozenset(
    """id position shapeType active capacity waitingPassengerIds
    unlockBlinkStartTimeMs snapBlips""".split()
)
PASSENGER_KEYS = frozenset("id destinationShapeType isAtDestination waitMs".split())
PATH_KEYS = frozenset("id color stationIds metroIds isLooped pathOrder".split())
METRO_KEYS = frozenset(
    """id pathId position currentSegmentIdx currentStationId isForward
    speed maxSpeed accelerationPerMs decelerationPerMs
    stopTimeRemainingMs boardingProgressMs boardingTimePerPassengerMs
    justArrivedAndStopped isUnassignmentQueued baseCapacity
    serviceAction carriages onboardPassengerIds""".split()
)
CARRIAGE_KEYS = frozenset("id capacity".split())
TRAVEL_PLAN_KEYS = frozenset("nextPathId nextStationId nextStationIdx nodePath".split())
NODE_KEYS = frozenset("stationId pathIds".split())
PATH_BUTTON_KEYS = frozenset("isLocked unlockBlinkStartTimeMs".split())
RNG_KEYS = frozenset("python numpy".split())


def _module(testcase, name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        testcase.fail(f"GM-07b product module is missing: {name} ({error})")


def _symbol(testcase, module_name, name):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-07b product symbol is missing: {module_name}.{name}"
    )
    return value


def _apply(env, action):
    _, _, _, info = env.step(action, dt_ms=0)
    if not info["action_ok"]:
        raise AssertionError(f"scenario action was rejected: {action!r}")


def _rich_env(seed=7101):
    env = MiniMetroEnv(dt_ms=250)
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    _apply(env, {"type": "attach_carriage", "path_index": 0})
    for _ in range(120):
        env.step({"type": "noop"})
        mediator = env.mediator
        if (
            mediator.metros[0].passengers
            and any(station.passengers for station in mediator.stations)
            and mediator.travel_plans
        ):
            return env
    raise AssertionError("rich scenario did not converge")


def _document(testcase):
    serialize_game = _symbol(testcase, SAVE_GAME_MODULE, "serialize_game")
    env = _rich_env()
    document = serialize_game(env.mediator)
    testcase.assertIsInstance(document, dict)
    return env, document


def _walk_dicts(value, path=()):
    if type(value) is dict:
        yield path, value
        for key, item in value.items():
            yield from _walk_dicts(item, (*path, key))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _walk_dicts(item, (*path, index))


def _resolve(document, path):
    node = document
    for step in path:
        node = node[step]
    return node


def _replace_everywhere(value, old, new):
    if type(value) is dict:
        return {
            (new if key == old else key): _replace_everywhere(item, old, new)
            for key, item in value.items()
        }
    if type(value) is list:
        return [_replace_everywhere(item, old, new) for item in value]
    return new if value == old else value


def _station_with_waiting(document):
    for record in document["stations"]:
        if record["waitingPassengerIds"]:
            return record
    raise AssertionError("scenario needs a waiting rider")


def _assert_each_mutation_rejected(testcase, validate_save, document, mutations):
    for name, mutate in mutations.items():
        candidate = deepcopy(document)
        mutate(candidate)
        with testcase.subTest(name=name), testcase.assertRaises(ValueError):
            validate_save(candidate)


def _setter(path, key, value):
    def mutate(document):
        _resolve(document, path)[key] = value

    return mutate


class TestGM07bSaveSchemaVersioning(unittest.TestCase):
    def test_versioned_constants_and_serialized_header(self):
        schema = _module(self, SAVE_SCHEMA_MODULE)
        for name, expected in (
            ("SAVE_SCHEMA_VERSION_V1", 1),
            ("SAVE_SCHEMA_VERSION", 1),
            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1}),
            ("SAVE_STATE_CONTRACT", "mini-metro-save-v1"),
            ("SAVE_RULES_VERSION", "rules-v1"),
        ):
            self.assertEqual(getattr(schema, name, None), expected, name)
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        self.assertEqual(document["schemaVersion"], 1)
        self.assertEqual(document["stateContract"], "mini-metro-save-v1")
        self.assertEqual(document["rulesVersion"], "rules-v1")
        self.assertIsNone(validate_save(document))

    def test_schema_version_and_pinned_literal_strictness(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        mutations = {
            "bool-true schemaVersion": _setter((), "schemaVersion", True),
            "bool-false schemaVersion": _setter((), "schemaVersion", False),
            "forward schemaVersion": _setter((), "schemaVersion", 2),
            "zero schemaVersion": _setter((), "schemaVersion", 0),
            "string schemaVersion": _setter((), "schemaVersion", "1"),
            "float schemaVersion": _setter((), "schemaVersion", 1.0),
            "null schemaVersion": _setter((), "schemaVersion", None),
            "wrong stateContract": _setter((), "stateContract", "mini-metro-save-v2"),
            "empty stateContract": _setter((), "stateContract", ""),
            "null stateContract": _setter((), "stateContract", None),
            "wrong rulesVersion": _setter((), "rulesVersion", "rules-v2"),
            "integer rulesVersion": _setter((), "rulesVersion", 1),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_save_directory_config_and_gitignore_entry(self):
        self.assertTrue(
            hasattr(config, "save_dir_name"),
            "GM-07b product attribute is missing: config.save_dir_name",
        )
        self.assertEqual(config.save_dir_name, "saves")
        lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("/saves/", lines)


class TestGM07bSaveSchemaExactKeys(unittest.TestCase):
    def test_top_level_and_record_key_sets_are_exact(self):
        env, document = _document(self)
        mediator = env.mediator
        self.assertEqual(set(document), TOP_LEVEL_KEYS)
        self.assertEqual(set(document["stations"][0]), STATION_KEYS)
        self.assertEqual(set(document["passengers"][0]), PASSENGER_KEYS)
        self.assertEqual(set(document["paths"][0]), PATH_KEYS)
        self.assertEqual(set(document["metros"][0]), METRO_KEYS)
        self.assertEqual(set(document["metros"][0]["carriages"][0]), CARRIAGE_KEYS)
        self.assertEqual(set(document["pathButtons"][0]), PATH_BUTTON_KEYS)
        self.assertEqual(set(document["rng"]), RNG_KEYS)
        self.assertEqual(document["rng"], canonical_checkpoint(env)["rng"])
        self.assertTrue(document["travelPlans"])
        for entry, plan in document["travelPlans"].items():
            self.assertTrue(entry.startswith("Passenger-"))
            self.assertEqual(set(plan), TRAVEL_PLAN_KEYS)
            for record in plan["nodePath"]:
                self.assertEqual(set(record), NODE_KEYS)
        # Pair-array order fidelity is pinned in test_gm07b_save_roundtrip.
        self.assertEqual(len(document["pathColors"]), len(mediator.path_colors))
        self.assertTrue(all(len(pair) == 2 for pair in document["pathColors"]))
        self.assertEqual(len(document["pathToColor"]), len(mediator.paths))
        self.assertEqual(len(document["spawnTimers"]), len(mediator.all_stations))
        self.assertTrue(all(len(entry) == 3 for entry in document["spawnTimers"]))
        self.assertEqual(
            [record["id"] for record in document["stations"]],
            [station.id for station in mediator.all_stations],
        )
        self.assertEqual(
            document["metros"][0]["onboardPassengerIds"],
            [rider.id for rider in mediator.metros[0].passengers],
        )

    def test_every_section_rejects_unknown_keys(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        seen = set()
        for path, node in _walk_dicts(document):
            signature = frozenset(node)
            if signature in seen:
                continue
            seen.add(signature)
            candidate = deepcopy(document)
            _resolve(candidate, path)["gm07bUnknownKey"] = 1
            with self.subTest(section=path), self.assertRaises(ValueError):
                validate_save(candidate)

    def test_every_section_rejects_missing_keys(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        seen = set()
        for path, node in _walk_dicts(document):
            if path and path[-1] == "travelPlans":
                continue  # ID-keyed map: absence of one plan is legal.
            signature = frozenset(node)
            if signature in seen:
                continue
            seen.add(signature)
            for key in node:
                candidate = deepcopy(document)
                del _resolve(candidate, path)[key]
                with self.subTest(section=path, key=key), self.assertRaises(ValueError):
                    validate_save(candidate)

    def test_document_uses_plain_json_types_only(self):
        _, document = _document(self)
        stack = [("document", document)]
        while stack:
            path, value = stack.pop()
            if value is None or type(value) in (bool, int, float, str):
                continue
            if type(value) is list:
                stack.extend((f"{path}[{i}]", item) for i, item in enumerate(value))
            elif type(value) is dict:
                for key, item in value.items():
                    self.assertIs(type(key), str, f"{path} key {key!r}")
                    stack.append((f"{path}.{key}", item))
            else:
                self.fail(f"non-JSON {type(value).__name__} at {path}")


class TestGM07bSaveSchemaValues(unittest.TestCase):
    def test_wrong_scalar_types_are_rejected(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        metro = ("metros", 0)
        mutations = {
            "bool timeMs": _setter((), "timeMs", True),
            "bool steps": _setter((), "steps", True),
            "bool spawningStep": _setter((), "passengerSpawningStep", True),
            "bool spawningInterval": _setter((), "passengerSpawningIntervalStep", True),
            "bool maxWait": _setter((), "passengerMaxWaitTimeMs", True),
            "bool overdueThreshold": _setter((), "overduePassengerThreshold", True),
            "bool deliveries": _setter((), "deliveries", True),
            "bool numMetros": _setter((), "numMetros", True),
            "int isGameOver": _setter((), "isGameOver", 1),
            "string steps": _setter((), "steps", "3"),
            "float timeMs": _setter((), "timeMs", 1.5),
            "bool boarding interval": _setter(
                metro, "boardingTimePerPassengerMs", True
            ),
            "bool station capacity": _setter(("stations", 0), "capacity", True),
            "bool passenger waitMs": _setter(("passengers", 0), "waitMs", True),
            "int path isLooped": _setter(("paths", 0), "isLooped", 0),
            "int button isLocked": _setter(("pathButtons", 0), "isLocked", 0),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_pause_and_speed_vocabularies(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        for reasons in ([], ["user"], ["menu"], ["menu", "user"]):
            candidate = deepcopy(document)
            candidate["pauseReasons"] = reasons
            with self.subTest(valid_pause=reasons):
                self.assertIsNone(validate_save(candidate))
        for speed in (1, 2, 4):
            candidate = deepcopy(document)
            candidate["gameSpeedMultiplier"] = speed
            with self.subTest(valid_speed=speed):
                self.assertIsNone(validate_save(candidate))
        mutations = {
            "unknown reason": _setter((), "pauseReasons", ["weird"]),
            "capitalized reason": _setter((), "pauseReasons", ["User"]),
            "duplicate reason": _setter((), "pauseReasons", ["user", "user"]),
            "unsorted reasons": _setter((), "pauseReasons", ["user", "menu"]),
            "string reasons": _setter((), "pauseReasons", "user"),
            "integer reason": _setter((), "pauseReasons", [1]),
            "speed 3": _setter((), "gameSpeedMultiplier", 3),
            "speed 0": _setter((), "gameSpeedMultiplier", 0),
            "speed -1": _setter((), "gameSpeedMultiplier", -1),
            "speed bool": _setter((), "gameSpeedMultiplier", True),
            "speed float": _setter((), "gameSpeedMultiplier", 1.0),
            "speed string": _setter((), "gameSpeedMultiplier", "1"),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_spawn_timers_cover_every_pool_station_exactly_once(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        mutations = {
            "missing entry": lambda value: value["spawnTimers"].pop(),
            "duplicate entry": lambda value: value["spawnTimers"].append(
                list(value["spawnTimers"][0])
            ),
            "unknown station": _setter(("spawnTimers", 0), 0, UNKNOWN_STATION_ID),
            "duplicated station": lambda value: value["spawnTimers"][0].__setitem__(
                0, value["spawnTimers"][1][0]
            ),
            "wrong arity": lambda value: value["spawnTimers"].__setitem__(
                0, value["spawnTimers"][0][:2]
            ),
            "bool steps-since": _setter(("spawnTimers", 0), 1, True),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_malformed_rng_states_are_rejected(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        python_state = document["rng"]["python"]
        self.assertEqual(len(python_state), 3)
        self.assertEqual(len(python_state[1]), 625)
        mutations = {
            "outer-only python state": _setter(("rng",), "python", [python_state[0]]),
            "python inner not array": _setter(
                ("rng",), "python", [python_state[0], "state", python_state[2]]
            ),
            "python inner truncated": _setter(
                ("rng",),
                "python",
                [python_state[0], python_state[1][:5], python_state[2]],
            ),
            "python inner bool word": _setter(("rng", "python", 1), 0, True),
            "python bool version": _setter(("rng", "python"), 0, True),
            "python string gauss": _setter(("rng", "python"), 2, "x"),
            "numpy wrong generator": _setter(
                ("rng", "numpy"), "bit_generator", "MT19937"
            ),
            "numpy float state word": _setter(("rng", "numpy", "state"), "state", 1.5),
            "numpy bool has_uint32": _setter(("rng", "numpy"), "has_uint32", True),
            "numpy missing inc": lambda value: value["rng"]["numpy"]["state"].pop(
                "inc"
            ),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)


class TestGM07bSaveSchemaReferences(unittest.TestCase):
    def test_id_grammar_and_global_uniqueness(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        station_id = document["stations"][0]["id"]
        passenger_id = document["passengers"][0]["id"]
        metro_id = document["metros"][0]["id"]
        grammar = {
            "wrong class prefix": (station_id, "Wrong-" + station_id.split("-", 1)[1]),
            "empty suffix": (passenger_id, "Passenger-"),
            "non-base57 characters": (metro_id, "Metro-not base57!!"),
            "unknown shape suffix": (
                station_id,
                station_id.rsplit("-", 1)[0] + "-ShapeType.HEXAGON",
            ),
        }
        for name, (old, new) in grammar.items():
            candidate = _replace_everywhere(document, old, new)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_save(candidate)
        duplicates = {
            "duplicate passenger id": _setter(
                ("passengers", 1), "id", document["passengers"][0]["id"]
            ),
            "duplicate station id": _setter(
                ("stations", 1), "id", document["stations"][0]["id"]
            ),
            "duplicate carriage id": lambda value: value["metros"][0][
                "carriages"
            ].append(dict(value["metros"][0]["carriages"][0])),
        }
        _assert_each_mutation_rejected(self, validate_save, document, duplicates)

    def test_dangling_and_duplicate_references(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        onboard_id = document["metros"][0]["onboardPassengerIds"][0]
        plan_key = next(iter(document["travelPlans"]))
        routed = next(
            key for key, plan in document["travelPlans"].items() if plan["nodePath"]
        )

        def rekey_plan(value):
            value["travelPlans"][UNKNOWN_PASSENGER_ID] = value["travelPlans"].pop(
                plan_key
            )

        mutations = {
            "dangling path station": _setter(
                ("paths", 0, "stationIds"), 0, UNKNOWN_STATION_ID
            ),
            "cross-class station reference": _setter(
                ("paths", 0, "stationIds"), 0, document["metros"][0]["id"]
            ),
            "dangling onboard rider": lambda value: value["metros"][0][
                "onboardPassengerIds"
            ].append(UNKNOWN_PASSENGER_ID),
            "dangling metro path": _setter(("metros", 0), "pathId", UNKNOWN_PATH_ID),
            "dangling plan key": rekey_plan,
            "dangling plan node station": _setter(
                ("travelPlans", routed, "nodePath", 0), "stationId", UNKNOWN_STATION_ID
            ),
            "dangling next path": _setter(
                ("travelPlans", plan_key), "nextPathId", UNKNOWN_PATH_ID
            ),
            "dangling path-to-color path": _setter(
                ("pathToColor", 0), 0, UNKNOWN_PATH_ID
            ),
            "duplicate waiting reference": lambda value: _station_with_waiting(value)[
                "waitingPassengerIds"
            ].append(_station_with_waiting(value)["waitingPassengerIds"][0]),
            "waiting and onboard duplicate": lambda value: _station_with_waiting(value)[
                "waitingPassengerIds"
            ].append(onboard_id),
            "unlocated passenger definition": lambda value: value["passengers"].append(
                {
                    "id": UNKNOWN_PASSENGER_ID,
                    "destinationShapeType": value["passengers"][0][
                        "destinationShapeType"
                    ],
                    "isAtDestination": False,
                    "waitMs": 0,
                }
            ),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)


class TestGM07bCanonicalBytes(unittest.TestCase):
    def test_canonical_bytes_follow_the_frozen_fixture_recipe(self):
        canonical_save_bytes = _symbol(self, SAVE_SCHEMA_MODULE, "canonical_save_bytes")
        _, document = _document(self)
        payload = canonical_save_bytes(document)
        recipe = dict(
            allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
        expected = json.dumps(document, **recipe).encode("ascii") + b"\n"
        self.assertEqual(payload, expected)
        self.assertNotIn(b"\r", payload)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(payload.count(b"\n"), 1)
        payload.decode("ascii")
        reparsed = json.loads(payload)
        self.assertEqual(reparsed, document)
        self.assertEqual(canonical_save_bytes(reparsed), payload)


if __name__ == "__main__":
    unittest.main()

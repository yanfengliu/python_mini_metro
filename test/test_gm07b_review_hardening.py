"""GM-07b review hardening: RNG domains, duplicate keys, active-prefix refs.

Covers the non-blocker adversarial-review findings: numeric-domain
validation for both persisted RNG streams (native setter failures can no
longer escape as OverflowError), duplicate-JSON-key rejection at every
object level, active-station-prefix reference validation for
graph-consumed references, the saver's non-prefix live-list rejection,
and path-record hardening (consecutive duplicate stations, pathOrder
range).
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from mediator import Mediator

SAVE_GAME_MODULE = "save_game"
SAVE_SCHEMA_MODULE = "save_schema"
SAVE_LOAD_MODULE = "save_load"


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


def _line_env(seed, dt_ms=250):
    env = MiniMetroEnv(dt_ms=dt_ms)
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    return env


def _document(testcase, seed=8301):
    serialize_game = _symbol(testcase, SAVE_GAME_MODULE, "serialize_game")
    env = _line_env(seed)
    return env, serialize_game(env.mediator)


def _assert_each_mutation_rejected(testcase, validate_save, document, mutations):
    for name, mutate in mutations.items():
        candidate = deepcopy(document)
        mutate(candidate)
        with testcase.subTest(name=name), testcase.assertRaises(ValueError):
            validate_save(candidate)


class TestGM07bRngDomains(unittest.TestCase):
    def test_out_of_domain_rng_values_are_rejected(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)

        def python_word(index, value):
            def mutate(doc):
                doc["rng"]["python"][1][index] = value

            return mutate

        def numpy_field(key, value):
            def mutate(doc):
                doc["rng"]["numpy"][key] = value

            return mutate

        def numpy_state(key, value):
            def mutate(doc):
                doc["rng"]["numpy"]["state"][key] = value

            return mutate

        mutations = {
            "negative python word": python_word(0, -1),
            "oversized python word": python_word(0, 2**32),
            "huge python word": python_word(613, 2**64),
            "negative python index": python_word(624, -1),
            "python index 625": python_word(624, 625),
            "python index 999": python_word(624, 999),
            "negative numpy state": numpy_state("state", -1),
            "oversized numpy state": numpy_state("state", 2**128),
            "huge numpy state": numpy_state("state", 2**200),
            "negative numpy inc": numpy_state("inc", -1),
            "oversized numpy inc": numpy_state("inc", 2**128),
            "negative uinteger": numpy_field("uinteger", -1),
            "oversized uinteger": numpy_field("uinteger", 2**32),
            "has_uint32 of 2": numpy_field("has_uint32", 2),
            "has_uint32 of 7": numpy_field("has_uint32", 7),
            "negative has_uint32": numpy_field("has_uint32", -1),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_domain_boundary_values_are_accepted(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        candidate = deepcopy(document)
        candidate["rng"]["python"][1][0] = 2**32 - 1
        candidate["rng"]["python"][1][624] = 624
        candidate["rng"]["numpy"]["state"]["state"] = 2**128 - 1
        candidate["rng"]["numpy"]["state"]["inc"] = 2**128 - 1
        candidate["rng"]["numpy"]["uinteger"] = 2**32 - 1
        candidate["rng"]["numpy"]["has_uint32"] = 1
        self.assertIsNone(validate_save(candidate))

    def test_residual_setter_failures_normalize_to_value_error(self):
        # Belt-and-braces behind the schema domains: a native setter
        # failure inside the loader re-raises as the contract ValueError.
        save_load = _module(self, SAVE_LOAD_MODULE)
        env, document = _document(self)
        del env
        for name, words in (
            ("negative word", [-1] + [0] * 623 + [0]),
            ("invalid index", [0] * 624 + [999]),
        ):
            with self.subTest(name=name):
                rng = deepcopy(document["rng"])
                rng["python"] = [3, words, None]
                mediator = Mediator(seed=0)
                with self.assertRaises(ValueError):
                    save_load._restore_rng(mediator, rng)


class TestGM07bDuplicateJsonKeys(unittest.TestCase):
    def _payload(self):
        canonical_save_bytes = _symbol(self, SAVE_SCHEMA_MODULE, "canonical_save_bytes")
        _, document = _document(self)
        return canonical_save_bytes(document)

    def test_duplicate_keys_are_rejected_at_every_level(self):
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        payload = self._payload()
        top_level = payload[:1] + b'"schemaVersion":999,' + payload[1:]
        nested = payload.replace(b'"numpy":{', b'"numpy":{"has_uint32":7,', 1)
        self.assertNotEqual(nested, payload)
        with tempfile.TemporaryDirectory() as directory:
            for name, doctored in (("top", top_level), ("nested", nested)):
                target = Path(directory) / f"dup-{name}.save.json"
                target.write_bytes(doctored)
                with self.subTest(level=name), self.assertRaises(ValueError):
                    load_game(target)

    def test_unmodified_payload_still_loads(self):
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        payload = self._payload()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "clean.save.json"
            target.write_bytes(payload)
            loaded = load_game(target)
        self.assertEqual(len(loaded.paths), 1)


class TestGM07bActivePrefixReferences(unittest.TestCase):
    def test_locked_station_references_are_rejected(self):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        # A two-station path leaves at least one ACTIVE station off the
        # path, so both rejection lanes are reachable from one document.
        env = MiniMetroEnv(dt_ms=250)
        env.reset(seed=8303)
        _apply(env, {"type": "create_path", "stations": [0, 1], "loop": False})
        _apply(env, {"type": "assign_locomotive", "path_index": 0})
        document = serialize_game(env.mediator)
        unlocked = document["unlockedNumStations"]
        self.assertLess(unlocked, len(document["stations"]))
        locked_id = document["stations"][unlocked]["id"]
        path_station_ids = set(document["paths"][0]["stationIds"])
        active_off_path = next(
            record["id"]
            for record in document["stations"][:unlocked]
            if record["id"] not in path_station_ids
        )
        mutations = {
            "locked station on a path": lambda doc: doc["paths"][0][
                "stationIds"
            ].__setitem__(0, locked_id),
            "locked current station": lambda doc: doc["metros"][0].__setitem__(
                "currentStationId", locked_id
            ),
            "current station off its path": lambda doc: doc["metros"][0].__setitem__(
                "currentStationId", active_off_path
            ),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_serializer_rejects_a_non_prefix_live_station_list(self):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        env = _line_env(8302)
        mediator = env.mediator
        mediator.stations = [mediator.stations[1], mediator.stations[0]] + list(
            mediator.stations[2:]
        )
        with self.assertRaises(ValueError):
            serialize_game(mediator)


class TestGM07bPathRecordHardening(unittest.TestCase):
    def test_consecutive_duplicate_and_out_of_range_order_are_rejected(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        first = document["paths"][0]["stationIds"][0]

        def dup_consecutive(doc):
            doc["paths"][0]["stationIds"][1] = doc["paths"][0]["stationIds"][0]

        def dup_loop_endpoint(doc):
            doc["paths"][0]["isLooped"] = True
            doc["paths"][0]["stationIds"] = doc["paths"][0]["stationIds"] + [first]

        mutations = {
            "consecutive duplicate station": dup_consecutive,
            "looped endpoint duplicate": dup_loop_endpoint,
            "pathOrder above range": lambda doc: doc["paths"][0].__setitem__(
                "pathOrder", 33
            ),
            "pathOrder below range": lambda doc: doc["paths"][0].__setitem__(
                "pathOrder", -33
            ),
        }
        _assert_each_mutation_rejected(self, validate_save, document, mutations)

    def test_path_order_range_bounds_are_accepted(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        _, document = _document(self)
        for order in (-32, 0, 32):
            candidate = deepcopy(document)
            candidate["paths"][0]["pathOrder"] = order
            with self.subTest(order=order):
                self.assertIsNone(validate_save(candidate))


if __name__ == "__main__":
    unittest.main()

"""GM-07b review blocker: the bound service action persists verbatim.

Ordinary multi-metro play reaches boundaries where a metro's bound
``_station_service_action`` no longer matches the re-derivable pure action
(a later metro consumed its passenger inside the same tick). Schema v1
persists that cache verbatim (nullable per-metro ``serviceAction``), the
validator pins its timing/speed invariant, and the loader restores it
without re-deriving — so the exact review repros (codex seed-127; harness
seed-4501 and seed-9001) save, load, and continue in lockstep with a
never-saved control under a UUID-normalized save-document oracle.
``canonical_checkpoint`` itself raises on these states (a known
pre-existing defect), so the oracle masks entity IDs positionally and
compares re-serialized documents instead.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import passenger_color, passenger_size
from entity.passenger import Passenger
from env import MiniMetroEnv
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from passenger_capacity import pure_service_action, same_service_action
from travel_plan import TravelPlan
from utils import get_shape_from_type

SAVE_GAME_MODULE = "save_game"
SAVE_SCHEMA_MODULE = "save_schema"
UNKNOWN_PASSENGER_ID = "Passenger-" + "2" * 22


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


def _canonical_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _normalize_document(document):
    """Mask every entity ID positionally so branch-minted IDs compare equal."""

    mapping = {}
    for index, record in enumerate(document["stations"]):
        mapping[record["id"]] = f"Station#{index}"
    for index, record in enumerate(document["passengers"]):
        mapping[record["id"]] = f"Passenger#{index}"
    for index, record in enumerate(document["paths"]):
        mapping[record["id"]] = f"Path#{index}"
    for index, record in enumerate(document["metros"]):
        mapping[record["id"]] = f"Metro#{index}"
        for slot, carriage in enumerate(record["carriages"]):
            mapping[carriage["id"]] = f"Carriage#{index}.{slot}"

    def rewrite(value):
        if type(value) is str:
            return mapping.get(value, value)
        if type(value) is list:
            return [rewrite(item) for item in value]
        if type(value) is dict:
            return {mapping.get(key, key): rewrite(item) for key, item in value.items()}
        return value

    return rewrite(document)


def _has_stale_cache(mediator):
    nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
    for metro in mediator.metros:
        cache = metro._station_service_action
        station = metro.current_station
        pure = (
            None
            if station is None
            else pure_service_action(mediator, metro, station, nodes)
        )
        if (cache is None) != (pure is None):
            return True
        if cache is not None and not same_service_action(cache, pure):
            return True
    return False


def _passenger_bound_for(mediator, station):
    for candidate in mediator.stations:
        if candidate.shape.type != station.shape.type:
            shape = get_shape_from_type(
                candidate.shape.type, passenger_color, passenger_size
            )
            return Passenger(shape)
    raise AssertionError("scenario needs two station shape types")


def _line_env(seed, dt_ms=250):
    env = MiniMetroEnv(dt_ms=dt_ms)
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    return env


def _mid_stop_env(seed=6206):
    """A canonically bound mid-boarding stop (cache == pure, timers 250/250).

    Returns the env and the passenger the live game actually bound (the
    first eligible boarding candidate, not necessarily the injected one).
    """

    env = _line_env(seed)
    mediator = env.mediator
    metro = mediator.metros[0]
    start = mediator.paths[0].stations[0]
    metro.current_station = start
    boarder = _passenger_bound_for(mediator, start)
    start.add_passenger(boarder)
    mediator.passengers.append(boarder)
    plan = TravelPlan([Node(mediator.stations[1])])
    plan.next_path = mediator.paths[0]
    mediator.travel_plans[boarder] = plan
    mediator.move_passengers(250)
    cache = metro._station_service_action
    if cache is None or cache[0] != "board":
        raise AssertionError("mid-stop scenario did not bind a boarding action")
    return env, cache[1]


class TestGM07bStaleServiceLockstep(unittest.TestCase):
    """The three review repros: save at a stale boundary, load, continue."""

    def _run_lockstep(self, control, schedule, boundaries, horizon, continuation=10):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        canonical_save_bytes = _symbol(self, SAVE_SCHEMA_MODULE, "canonical_save_bytes")
        normalized = {}
        documents = {}
        stale = {}
        for tick in range(horizon + 1):
            if tick:
                control.step(schedule.get(tick, {"type": "noop"}))
            document = serialize_game(control.mediator)
            normalized[tick] = _canonical_bytes(_normalize_document(document))
            if tick in boundaries:
                documents[tick] = document
                stale[tick] = _has_stale_cache(control.mediator)
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                self.assertTrue(
                    stale[boundary],
                    f"tick {boundary} must exhibit a stale service cache",
                )
                with tempfile.TemporaryDirectory() as directory:
                    target = Path(directory) / "stale.save.json"
                    target.write_bytes(canonical_save_bytes(documents[boundary]))
                    loaded = load_game(target)
                wrapped = MiniMetroEnv(dt_ms=control.dt_ms_default)
                wrapped.mediator = loaded
                wrapped.last_deliveries = loaded.deliveries
                wrapped.last_line_credits = loaded.line_credits
                self.assertEqual(
                    _canonical_bytes(
                        _normalize_document(serialize_game(wrapped.mediator))
                    ),
                    normalized[boundary],
                    f"loaded state differs at the tick-{boundary} boundary",
                )
                for offset in range(1, continuation + 1):
                    tick = boundary + offset
                    if tick > horizon:
                        break
                    wrapped.step(schedule.get(tick, {"type": "noop"}))
                    self.assertEqual(
                        _canonical_bytes(
                            _normalize_document(serialize_game(wrapped.mediator))
                        ),
                        normalized[tick],
                        f"diverged at tick {tick} after loading tick {boundary}",
                    )

    def test_codex_seed_127_stale_board_cache_roundtrips_in_lockstep(self):
        # codex finding 1: seed 127, route [0,1,2], assign, 17 noops,
        # assign, 94 noops at dt 125 -> the first metro keeps a stale BOARD
        # cache with timers (500, 0); before the fix the save could not load.
        control = _line_env(127, dt_ms=125)
        for _ in range(17):
            control.step({"type": "noop"})
        _apply(control, {"type": "assign_locomotive", "path_index": 0})
        for _ in range(93):
            control.step({"type": "noop"})
        # tick 0 of the recorded window is the 94th noop (the boundary).
        self._run_lockstep(control, {}, boundaries=(1,), horizon=13)

    def test_harness_seed_4501_two_locomotive_boundary_roundtrips(self):
        # harness finding 1 (rejection lane): two locomotives on one line,
        # the second assigned at tick 6; tick 26 is the stale boundary.
        control = _line_env(4501)
        schedule = {6: {"type": "assign_locomotive", "path_index": 0}}
        self._run_lockstep(control, schedule, boundaries=(26,), horizon=36)

    def test_harness_seed_9001_two_lines_windows_roundtrip(self):
        # harness finding 1 (rejection at 20; SILENT DIVERGENCE at 55/58):
        # two lines sharing stations under raised spawn pressure with the
        # exact review schedule; before the fix, tick 20 could not load and
        # ticks 55/58 loaded then re-attributed 250 ms of boarding progress.
        control = _line_env(9001)
        mediator = control.mediator
        mediator.purchased_num_paths = 2
        mediator.update_unlocked_num_paths()
        _apply(control, {"type": "create_path", "stations": [0, 2], "loop": False})
        _apply(control, {"type": "assign_locomotive", "path_index": 1})
        mediator.passenger_spawning_interval_step = 6
        for station in mediator.all_stations:
            mediator.station_spawn_interval_steps[station] = 6
            mediator.station_steps_since_last_spawn[station] = 5
        schedule = {
            8: {"type": "assign_locomotive", "path_index": 0},
            14: {"type": "attach_carriage", "path_index": 0},
            20: {"type": "attach_carriage", "path_index": 1},
            60: {"type": "unassign_locomotive", "path_index": 0},
        }
        self._run_lockstep(control, schedule, boundaries=(20, 55, 58), horizon=68)


class TestGM07bServiceActionSchema(unittest.TestCase):
    def _mid_stop_document(self):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        env, boarder = _mid_stop_env()
        document = serialize_game(env.mediator)
        record = document["metros"][0]
        self.assertEqual(
            record["serviceAction"], {"kind": "board", "passengerId": boarder.id}
        )
        self.assertEqual(
            (record["stopTimeRemainingMs"], record["boardingProgressMs"]), (250, 250)
        )
        return document

    def test_bound_service_action_serializes_and_validates(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        document = self._mid_stop_document()
        self.assertIsNone(validate_save(document))

    def test_service_action_strictness_rejections(self):
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        document = self._mid_stop_document()

        def action_setter(key, value):
            def mutate(doc):
                doc["metros"][0]["serviceAction"][key] = value

            return mutate

        def field_setter(key, value):
            def mutate(doc):
                doc["metros"][0][key] = value

            return mutate

        mutations = {
            "dangling passenger": action_setter("passengerId", UNKNOWN_PASSENGER_ID),
            "unknown kind": action_setter("kind", "teleport"),
            "non-string kind": action_setter("kind", 1),
            "non-string passengerId": action_setter("passengerId", 1),
            "unknown action key": action_setter("gm07bUnknown", 1),
            "missing action key": lambda doc: doc["metros"][0]["serviceAction"].pop(
                "passengerId"
            ),
            "string serviceAction": field_setter("serviceAction", "board"),
            "null action with nonzero timers": field_setter("serviceAction", None),
            "bound action away from station": field_setter("currentStationId", None),
            "bound action with nonzero speed": field_setter("speed", 0.123),
            "progress at the interval": lambda doc: (
                doc["metros"][0].__setitem__("boardingProgressMs", 500),
                doc["metros"][0].__setitem__("stopTimeRemainingMs", 0),
            ),
            "timer sum mismatch": field_setter("stopTimeRemainingMs", 100),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(document)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_save(candidate)


class TestGM07bServiceActionRestoration(unittest.TestCase):
    def test_bound_cache_restores_the_exact_tuple_verbatim(self):
        save_game = _symbol(self, SAVE_GAME_MODULE, "save_game")
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        env, boarder = _mid_stop_env()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bound.save.json"
            save_game(env.mediator, target)
            loaded = load_game(target)
        metro = loaded.metros[0]
        cache = metro._station_service_action
        self.assertIsNotNone(cache)
        self.assertEqual(cache[0], "board")
        self.assertEqual(cache[1].id, boarder.id)
        self.assertTrue(any(cache[1] is rider for rider in loaded.passengers))
        station = loaded.paths[0].stations[0]
        self.assertTrue(any(cache[1] is rider for rider in station.passengers))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (250, 250)
        )
        self.assertEqual(metro.speed, 0)

    def test_null_cache_with_derivable_action_stays_null_then_binds_fresh(self):
        # The stale-reset boundary: a persisted null cache with a derivable
        # action must restore as null (NEVER re-derived at load); the next
        # tick's reconcile then binds fresh from zero progress, exactly
        # like the never-saved game.
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        deserialize_game = _symbol(self, SAVE_GAME_MODULE, "deserialize_game")
        env, _ = _mid_stop_env()
        document = serialize_game(env.mediator)
        doctored = deepcopy(document)
        record = doctored["metros"][0]
        record["serviceAction"] = None
        record["stopTimeRemainingMs"] = 0
        record["boardingProgressMs"] = 0
        loaded = deserialize_game(doctored)
        metro = loaded.metros[0]
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
        )
        wrapped = MiniMetroEnv(dt_ms=250)
        wrapped.mediator = loaded
        wrapped.last_deliveries = loaded.deliveries
        wrapped.last_line_credits = loaded.line_credits
        wrapped.step({"type": "noop"})
        self.assertIsNotNone(metro._station_service_action)
        self.assertEqual(metro.boarding_progress_ms, 250)

    def test_unbound_speed_restores_verbatim_without_normalization(self):
        # codex finding 4 complement: with no bound action the persisted
        # speed restores exactly (no reconcile runs at load to zero it).
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        deserialize_game = _symbol(self, SAVE_GAME_MODULE, "deserialize_game")
        env, _ = _mid_stop_env()
        document = serialize_game(env.mediator)
        doctored = deepcopy(document)
        record = doctored["metros"][0]
        record["serviceAction"] = None
        record["stopTimeRemainingMs"] = 0
        record["boardingProgressMs"] = 0
        record["speed"] = 0.123
        loaded = deserialize_game(doctored)
        self.assertEqual(loaded.metros[0].speed, 0.123)


if __name__ == "__main__":
    unittest.main()

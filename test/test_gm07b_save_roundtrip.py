"""GM-07b roundtrip reds: save/load must be checkpoint byte-identical.

Every scenario builds a real ``MiniMetroEnv``, saves, loads, wraps the loaded
Mediator in a harness env with the five accounting fields grafted from the
control env, and asserts ``canonical_checkpoint`` byte equality (RNG included).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import passenger_color, passenger_size
from entity.passenger import Passenger
from env import MiniMetroEnv
from graph.node import Node
from recursive_checkpoint import canonical_checkpoint
from travel_plan import TravelPlan
from utils import get_shape_from_type

SAVE_GAME_MODULE = "save_game"


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


def _canonical_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


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


def _passenger_bound_for(mediator, station):
    for candidate in mediator.stations:
        if candidate.shape.type != station.shape.type:
            shape = get_shape_from_type(
                candidate.shape.type, passenger_color, passenger_size
            )
            return Passenger(shape)
    raise AssertionError("scenario needs two station shape types")


def _unlock_second_path(mediator):
    mediator.purchased_num_paths = 2
    mediator.update_unlocked_num_paths()


def _saved_then_loaded(testcase, env):
    save_game = _symbol(testcase, SAVE_GAME_MODULE, "save_game")
    load_game = _symbol(testcase, SAVE_GAME_MODULE, "load_game")
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "game.save.json"
        save_game(env.mediator, target)
        testcase.assertTrue(target.exists())
        loaded = load_game(target)
    wrapped = MiniMetroEnv(dt_ms=env.dt_ms_default, reward_mode=env.reward_mode)
    wrapped.mediator = loaded
    wrapped.last_deliveries = env.last_deliveries
    wrapped.last_line_credits = env.last_line_credits
    wrapped.last_score = env.last_score
    return wrapped


def _assert_roundtrip(testcase, env):
    wrapped = _saved_then_loaded(testcase, env)
    testcase.assertEqual(
        _canonical_bytes(canonical_checkpoint(env)),
        _canonical_bytes(canonical_checkpoint(wrapped)),
    )
    return wrapped


class TestGM07bRoundtripScenarios(unittest.TestCase):
    def test_riders_aboard_and_waiting(self):
        env = _line_env(7101)
        _apply(env, {"type": "attach_carriage", "path_index": 0})
        for _ in range(120):
            env.step({"type": "noop"})
            mediator = env.mediator
            if (
                mediator.metros[0].passengers
                and any(station.passengers for station in mediator.stations)
                and mediator.travel_plans
            ):
                break
        self.assertTrue(env.mediator.metros[0].passengers)
        self.assertTrue(any(s.passengers for s in env.mediator.stations))
        _assert_roundtrip(self, env)

    def test_queued_occupied_locomotive(self):
        env = _line_env(6201)
        mediator = env.mediator
        rider = _passenger_bound_for(mediator, mediator.stations[0])
        mediator.metros[0].add_passenger(rider)
        mediator.passengers.append(rider)
        _apply(env, {"type": "unassign_locomotive", "path_index": 0})
        self.assertIs(mediator.metros[0].is_unassignment_queued, True)
        wrapped = _assert_roundtrip(self, env)
        self.assertIs(wrapped.mediator.metros[0].is_unassignment_queued, True)

    def test_carriages_attached(self):
        env = _line_env(6202)
        _apply(env, {"type": "attach_carriage", "path_index": 0})
        _apply(env, {"type": "attach_carriage", "path_index": 0})
        self.assertEqual(len(env.mediator.metros[0].carriages), 2)
        wrapped = _assert_roundtrip(self, env)
        self.assertEqual(len(wrapped.mediator.metros[0].carriages), 2)

    def test_over_capacity_station_queue(self):
        env = _line_env(6203)
        mediator = env.mediator
        target = mediator.stations[0]
        while len(target.passengers) <= target.capacity + 1:
            extra = _passenger_bound_for(mediator, target)
            target.passengers.append(extra)
            mediator.passengers.append(extra)
        self.assertGreater(len(target.passengers), target.capacity)
        _assert_roundtrip(self, env)

    def test_active_travel_plans(self):
        env = _line_env(6204)
        for _ in range(3):
            env.step({"type": "noop"})
        self.assertTrue(env.mediator.travel_plans)
        wrapped = _assert_roundtrip(self, env)
        self.assertEqual(
            len(wrapped.mediator.travel_plans), len(env.mediator.travel_plans)
        )

    def test_plan_created_before_newer_path_conserves_stale_node_paths(self):
        env = _line_env(6204)
        for _ in range(3):
            env.step({"type": "noop"})
        mediator = env.mediator
        self.assertTrue(mediator.travel_plans)
        _unlock_second_path(mediator)
        _apply(env, {"type": "create_path", "stations": [1, 2], "loop": False})
        newer = mediator.paths[1]
        stale = [
            plan
            for plan in mediator.travel_plans.values()
            if plan.node_path
            and any(newer not in node.paths for node in plan.node_path)
        ]
        self.assertTrue(stale, "scenario needs a plan older than the newer path")
        _assert_roundtrip(self, env)

    def test_onboard_survivor_plan_outlives_removed_path(self):
        env = _line_env(6205)
        mediator = env.mediator
        path_a = mediator.paths[0]
        _unlock_second_path(mediator)
        _apply(env, {"type": "create_path", "stations": [0, 2], "loop": False})
        path_b = mediator.paths[1]
        survivor = _passenger_bound_for(mediator, mediator.stations[0])
        mediator.metros[0].add_passenger(survivor)
        mediator.passengers.append(survivor)
        node = Node(mediator.stations[2])
        node.paths = {path_a, path_b}
        plan = TravelPlan([node])
        plan.next_path = path_a
        mediator.travel_plans[survivor] = plan
        _apply(env, {"type": "remove_path", "path_id": path_b.id})
        self.assertIn(survivor, mediator.travel_plans)
        self.assertIn(path_b, node.paths)
        _assert_roundtrip(self, env)

    def test_mid_stop_fractional_boarding_progress(self):
        env = _line_env(6206)
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
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (250, 250)
        )
        wrapped = _assert_roundtrip(self, env)
        loaded_metro = wrapped.mediator.metros[0]
        self.assertEqual(
            (loaded_metro.stop_time_remaining_ms, loaded_metro.boarding_progress_ms),
            (250, 250),
        )

    def test_non_default_review_surfaced_scalars(self):
        env = _line_env(6207)
        mediator = env.mediator
        mediator.passenger_spawning_step = 7_777
        mediator.passenger_spawning_interval_step = 1_234
        mediator.passenger_max_wait_time_ms = 55_555
        mediator.overdue_passenger_threshold = 9
        mediator.metros[0].boarding_time_per_passenger_ms = 750
        mediator.set_game_speed(4)
        wrapped = _assert_roundtrip(self, env)
        loaded = wrapped.mediator
        self.assertEqual(loaded.passenger_spawning_step, 7_777)
        self.assertEqual(loaded.passenger_spawning_interval_step, 1_234)
        self.assertEqual(loaded.passenger_max_wait_time_ms, 55_555)
        self.assertEqual(loaded.overdue_passenger_threshold, 9)
        self.assertEqual(loaded.metros[0].boarding_time_per_passenger_ms, 750)
        self.assertEqual(loaded.game_speed_multiplier, 4)

    def test_unlock_blink_and_snap_blips(self):
        env = _line_env(6208)
        for _ in range(2):
            env.step({"type": "noop"})
        mediator = env.mediator
        _unlock_second_path(mediator)
        mediator.stations[0].start_unlock_blink(mediator.time_ms)
        mediator.stations[1].start_snap_blip(mediator.time_ms, mediator.paths[0].color)
        self.assertIsNotNone(mediator.path_buttons[1].unlock_blink_start_time_ms)
        self.assertTrue(mediator.stations[1].snap_blips)
        _assert_roundtrip(self, env)

    def test_pause_reasons_user_menu_and_both(self):
        for index, reasons in enumerate((("user",), ("menu",), ("menu", "user"))):
            with self.subTest(reasons=reasons):
                env = _line_env(6209 + 10 * index)
                for reason in reasons:
                    env.mediator.hold_pause_reason(reason)
                self.assertIs(env.mediator.is_paused, True)
                wrapped = _assert_roundtrip(self, env)
                self.assertEqual(
                    sorted(wrapped.mediator._pause_reasons), sorted(reasons)
                )
                self.assertIs(wrapped.mediator.is_paused, True)

    def test_game_over_state(self):
        env = _line_env(6210)
        env.mediator.is_game_over = True
        wrapped = _assert_roundtrip(self, env)
        self.assertIs(wrapped.mediator.is_game_over, True)


class TestGM07bSaverPurity(unittest.TestCase):
    def _stale_plan_env(self):
        env = _line_env(6211)
        mediator = env.mediator
        rider = _passenger_bound_for(mediator, mediator.stations[0])
        mediator.metros[0].add_passenger(rider)
        mediator.passengers.append(rider)
        plan = TravelPlan([Node(mediator.stations[1]), Node(mediator.stations[2])])
        plan.next_path = mediator.paths[0]
        # Stale cache on purpose: the getter would move it to stations[1], so
        # any saver reading through get_next_station() mutates the Mediator.
        plan.next_station = mediator.stations[2]
        plan.next_station_idx = 0
        mediator.travel_plans[rider] = plan
        return env

    def test_serialize_and_save_never_mutate_the_mediator(self):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        save_game = _symbol(self, SAVE_GAME_MODULE, "save_game")
        env = self._stale_plan_env()
        before = _canonical_bytes(canonical_checkpoint(env))
        serialize_game(env.mediator)
        self.assertEqual(_canonical_bytes(canonical_checkpoint(env)), before)
        with tempfile.TemporaryDirectory() as directory:
            save_game(env.mediator, Path(directory) / "purity.save.json")
        self.assertEqual(_canonical_bytes(canonical_checkpoint(env)), before)

    def test_save_game_writes_exact_canonical_bytes(self):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        save_game = _symbol(self, SAVE_GAME_MODULE, "save_game")
        env = self._stale_plan_env()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bytes.save.json"
            save_game(env.mediator, target)
            payload = target.read_bytes()
        document = serialize_game(env.mediator)
        self.assertEqual(payload, _canonical_bytes(document) + b"\n")
        self.assertNotIn(b"\r", payload)
        self.assertTrue(payload.endswith(b"\n"))
        payload.decode("ascii")

    def test_ordered_array_encodings_preserve_iteration_order(self):
        # sort_keys objects would destroy first-free-color iteration order, so
        # path_colors, path_to_color, and the spawn dicts are arrays of pairs.
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        env = _line_env(6242)
        mediator = env.mediator
        _unlock_second_path(mediator)
        _apply(env, {"type": "create_path", "stations": [1, 2], "loop": False})
        document = serialize_game(mediator)
        expected_colors = [
            [[float(part) for part in color], taken]
            for color, taken in mediator.path_colors.items()
        ]
        self.assertEqual(document["pathColors"], expected_colors)
        expected_path_to_color = [
            [path.id, [float(part) for part in color]]
            for path, color in mediator.path_to_color.items()
        ]
        self.assertEqual(document["pathToColor"], expected_path_to_color)
        expected_timers = [
            [
                station.id,
                mediator.station_steps_since_last_spawn[station],
                mediator.station_spawn_interval_steps[station],
            ]
            for station in mediator.all_stations
        ]
        self.assertEqual(document["spawnTimers"], expected_timers)


if __name__ == "__main__":
    unittest.main()

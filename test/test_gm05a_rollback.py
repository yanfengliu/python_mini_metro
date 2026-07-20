from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import mediator as mediator_module
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint
from test.test_gm05a_passenger_transitions import (
    add_passenger,
    build_mediator,
    create_path,
)
from travel_plan import TravelPlan


def build_waiting_env(kind: str):
    env = MiniMetroEnv()
    mediator, stations = build_mediator(seed=5217)
    env.mediator = mediator
    env.last_deliveries = mediator.deliveries
    env.last_line_credits = mediator.line_credits
    target = create_path(mediator, [0, 1], add_metro=False)
    destination = stations[4] if kind == "arrival" else stations[1]
    passenger = add_passenger(mediator, stations[0], destination)
    plan = TravelPlan([])
    mediator.travel_plans[passenger] = plan
    return env, mediator, stations, target, passenger, plan


def snapshot(env, target, passenger, plan):
    mediator = env.mediator
    return {
        "checkpoint": canonical_checkpoint(env),
        "stations_attr": mediator.stations,
        "paths_attr": mediator.paths,
        "metros_attr": mediator.metros,
        "passengers_attr": mediator.passengers,
        "travel_plans_attr": mediator.travel_plans,
        "target_stations": target.stations,
        "target_segments": target.segments,
        "target_path_segments": target.path_segments,
        "target_padding_segments": target.padding_segments,
        "target_station_items": list(target.stations),
        "target_segment_items": list(target.segments),
        "holder_list": mediator.stations[0].passengers,
        "holder_items": list(mediator.stations[0].passengers),
        "plan": plan,
        "plan_nodes": plan.node_path,
        "plan_fields": (
            plan.next_path,
            plan.next_station,
            plan.next_station_idx,
            list(plan.node_path),
        ),
        "passenger_flag": passenger.is_at_destination,
        "passenger_wait": passenger.wait_ms,
        "python_rng": mediator.context.python_random.getstate(),
        "numpy_rng": deepcopy(mediator.context.numpy_random.bit_generator.state),
    }


def assert_restored(test_case, env, target, passenger, plan, before):
    mediator = env.mediator
    test_case.assertEqual(canonical_checkpoint(env), before["checkpoint"])
    for name in ("stations", "paths", "metros", "passengers", "travel_plans"):
        test_case.assertIs(getattr(mediator, name), before[f"{name}_attr"])
    test_case.assertIs(target.stations, before["target_stations"])
    test_case.assertIs(target.segments, before["target_segments"])
    test_case.assertIs(target.path_segments, before["target_path_segments"])
    test_case.assertIs(target.padding_segments, before["target_padding_segments"])
    test_case.assertEqual(target.stations, before["target_station_items"])
    test_case.assertEqual(target.segments, before["target_segment_items"])
    test_case.assertIs(mediator.stations[0].passengers, before["holder_list"])
    test_case.assertEqual(mediator.stations[0].passengers, before["holder_items"])
    test_case.assertIs(mediator.travel_plans[passenger], before["plan"])
    test_case.assertIs(plan.node_path, before["plan_nodes"])
    test_case.assertIs(plan.next_path, before["plan_fields"][0])
    test_case.assertIs(plan.next_station, before["plan_fields"][1])
    test_case.assertEqual(plan.next_station_idx, before["plan_fields"][2])
    test_case.assertEqual(plan.node_path, before["plan_fields"][3])
    test_case.assertEqual(passenger.is_at_destination, before["passenger_flag"])
    test_case.assertEqual(passenger.wait_ms, before["passenger_wait"])
    test_case.assertEqual(
        mediator.context.python_random.getstate(), before["python_rng"]
    )
    test_case.assertEqual(
        mediator.context.numpy_random.bit_generator.state, before["numpy_rng"]
    )


class TestGM05aRollback(unittest.TestCase):
    def test_effect_free_candidate_factory_failure_preserves_everything(self):
        env, mediator, _, target, passenger, plan = build_waiting_env("route")
        before = snapshot(env, target, passenger, plan)

        with patch.object(
            mediator_module.Path,
            "__init__",
            side_effect=RuntimeError("candidate factory fault"),
        ):
            with self.assertRaisesRegex(RuntimeError, "candidate factory fault"):
                mediator.replace_path(target, [3, 0, 1], False)

        assert_restored(self, env, target, passenger, plan, before)

    def test_fresh_graph_failure_rolls_back_installed_topology_and_identities(self):
        env, mediator, _, target, passenger, plan = build_waiting_env("route")
        before = snapshot(env, target, passenger, plan)

        with patch.object(
            mediator_module,
            "build_station_nodes_dict",
            side_effect=RuntimeError("fresh graph fault"),
        ):
            with self.assertRaisesRegex(RuntimeError, "fresh graph fault"):
                mediator.replace_path(target, [3, 0, 1], False)

        assert_restored(self, env, target, passenger, plan, before)

    def test_arrival_removal_then_failure_restores_holders_plan_and_rng(self):
        env, mediator, stations, target, passenger, plan = build_waiting_env("arrival")
        before = snapshot(env, target, passenger, plan)
        original = mediator._replan_passenger_at_station

        def fail_after_arrival(rider, station, graph):
            original(rider, station, graph)
            self.assertNotIn(passenger, stations[0].passengers)
            self.assertNotIn(passenger, mediator.passengers)
            self.assertTrue(passenger.is_at_destination)
            raise RuntimeError("after arrival removal")

        mediator._replan_passenger_at_station = fail_after_arrival

        with self.assertRaisesRegex(RuntimeError, "after arrival removal"):
            mediator.replace_path(target, [3, 0, 1], False)

        assert_restored(self, env, target, passenger, plan, before)

    def test_partial_route_search_failure_restores_consumed_rng_and_state(self):
        env, mediator, _, target, passenger, plan = build_waiting_env("route")
        before = snapshot(env, target, passenger, plan)

        with patch.object(
            mediator_module,
            "bfs",
            side_effect=RuntimeError("partial route fault"),
        ):
            with self.assertRaisesRegex(RuntimeError, "partial route fault"):
                mediator.replace_path(target, [3, 0, 1], False)

        assert_restored(self, env, target, passenger, plan, before)

    def test_second_waiter_fault_restores_first_plan_and_both_rng_streams(self):
        env, mediator, stations, target, first, first_plan = build_waiting_env("route")
        second = add_passenger(mediator, stations[0], stations[1])
        second_plan = TravelPlan([])
        mediator.travel_plans[second] = second_plan
        before = canonical_checkpoint(env)
        holder = stations[0].passengers
        holder_items = list(holder)
        first_nodes = first_plan.node_path
        second_nodes = second_plan.node_path
        python_rng = mediator.context.python_random.getstate()
        numpy_rng = deepcopy(mediator.context.numpy_random.bit_generator.state)
        original = mediator._replan_passenger_at_station
        calls = []

        def fail_second(rider, station, graph):
            calls.append(rider)
            original(rider, station, graph)
            if rider is second:
                raise RuntimeError("second waiter fault")

        mediator._replan_passenger_at_station = fail_second
        with self.assertRaisesRegex(RuntimeError, "second waiter fault"):
            mediator.replace_path(target, [3, 0, 1], False)

        self.assertEqual(calls, [first, second])
        self.assertEqual(canonical_checkpoint(env), before)
        self.assertIs(stations[0].passengers, holder)
        self.assertEqual(stations[0].passengers, holder_items)
        self.assertIs(mediator.travel_plans[first], first_plan)
        self.assertIs(mediator.travel_plans[second], second_plan)
        self.assertIs(first_plan.node_path, first_nodes)
        self.assertIs(second_plan.node_path, second_nodes)
        self.assertEqual(mediator.context.python_random.getstate(), python_rng)
        self.assertEqual(mediator.context.numpy_random.bit_generator.state, numpy_rng)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.station import Station
from geometry.point import Point
from geometry.rect import Rect
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from test.gm06c_simulation_ui_support import (
    boardable_passenger,
    make_two_station_game,
    onboard_passenger,
    passenger_for,
    require_attribute,
)
from travel_plan import TravelPlan


def _cached_action(testcase: unittest.TestCase, metro):
    action = require_attribute(testcase, metro, "_station_service_action")
    if action is None:
        return None
    testcase.assertIsInstance(action, tuple)
    testcase.assertEqual(len(action), 2)
    return action


def _assert_board_action(
    testcase: unittest.TestCase,
    metro,
    expected_passenger,
) -> None:
    action = _cached_action(testcase, metro)
    testcase.assertIsNotNone(action)
    assert action is not None
    kind, passenger = action
    label = getattr(kind, "value", kind)
    testcase.assertIn("board", str(label).lower())
    testcase.assertIs(passenger, expected_passenger)


def _random_state(mediator):
    return (
        mediator.context.python_random.getstate(),
        copy.deepcopy(mediator.context.numpy_random.bit_generator.state),
    )


class TestGM06cServiceSelection(unittest.TestCase):
    def test_full_station_and_full_train_skip_blocked_transfer(self) -> None:
        mediator, start, end, _path, metro = make_two_station_game(seed=6301)
        transfer = onboard_passenger(
            mediator,
            metro,
            start,
            name="blocked-transfer",
            next_station=end,
        )
        for index in range(metro.capacity - 1):
            onboard_passenger(
                mediator,
                metro,
                start,
                name=f"onboard-{index}",
            )
        for index in range(end.capacity):
            waiting = passenger_for(start, name=f"station-{index}")
            end.add_passenger(waiting)
            mediator.passengers.append(waiting)

        node_map = build_station_nodes_dict(mediator.stations, mediator.paths)

        self.assertFalse(mediator.should_stop_at_next_station(metro, node_map))
        self.assertIs(metro.passengers[0], transfer)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertIsNone(_cached_action(self, metro))

    def test_queued_return_is_a_stop_override_not_a_phantom_service_action(
        self,
    ) -> None:
        mediator, _start, _end, _path, metro = make_two_station_game(seed=6302)
        metro.is_unassignment_queued = True
        node_map = build_station_nodes_dict(mediator.stations, mediator.paths)

        self.assertTrue(mediator.should_stop_at_next_station(metro, node_map))
        self.assertIsNone(_cached_action(self, metro))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (0, 0),
        )

    def test_query_is_pure_for_rng_plan_mapping_and_plan_fields(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6303)
        alternate = Station(Rect((0, 0, 0), 60, 60), Point(900, 500))
        mediator.stations.append(alternate)
        mediator.all_stations.append(alternate)
        waiting = passenger_for(start, name="query-rider")
        end.add_passenger(waiting)
        mediator.passengers.append(waiting)
        existing = TravelPlan([Node(start)])
        existing.next_path = None
        existing.next_station = None
        mediator.travel_plans[waiting] = existing
        node_path_object = existing.node_path
        mapping_object = mediator.travel_plans
        before_fields = (
            existing.next_path,
            existing.next_station,
            existing.next_station_idx,
            tuple(existing.node_path),
        )
        before_rng = _random_state(mediator)

        for _ in range(2):
            self.assertTrue(
                mediator.should_stop_at_next_station(
                    metro,
                    build_station_nodes_dict(mediator.stations, [path]),
                )
            )
            self.assertIs(mediator.travel_plans, mapping_object)
            self.assertIs(existing.node_path, node_path_object)
            self.assertEqual(
                (
                    existing.next_path,
                    existing.next_station,
                    existing.next_station_idx,
                    tuple(existing.node_path),
                ),
                before_fields,
            )
            self.assertEqual(_random_state(mediator), before_rng)

    def test_exceptional_query_restores_rng_mapping_and_touched_plan(self) -> None:
        mediator, start, end, _path, metro = make_two_station_game(seed=6304)
        waiting = passenger_for(start, name="raising-query-rider")
        end.add_passenger(waiting)
        mediator.passengers.append(waiting)
        plan = TravelPlan([Node(start)])
        mediator.travel_plans[waiting] = plan
        mapping_object = mediator.travel_plans
        node_path_object = plan.node_path
        before_rng = _random_state(mediator)
        before_fields = (
            plan.next_path,
            plan.next_station,
            plan.next_station_idx,
            tuple(plan.node_path),
        )

        def raising_plan(*_args, **_kwargs):
            mediator.context.python_random.random()
            mediator.context.numpy_random.random()
            plan.next_path = object()
            plan.next_station = end
            plan.next_station_idx = 7
            plan.node_path.append(Node(end))
            mediator.travel_plans[passenger_for(end)] = TravelPlan([])
            raise RuntimeError("planned query failure")

        mediator.get_travel_plan_starting_with_path = raising_plan

        with self.assertRaisesRegex(RuntimeError, "planned query failure"):
            mediator.should_stop_at_next_station(
                metro,
                build_station_nodes_dict(mediator.stations, mediator.paths),
            )

        self.assertIs(mediator.travel_plans, mapping_object)
        self.assertEqual(set(mediator.travel_plans), {waiting})
        self.assertIs(plan.node_path, node_path_object)
        self.assertEqual(
            (
                plan.next_path,
                plan.next_station,
                plan.next_station_idx,
                tuple(plan.node_path),
            ),
            before_fields,
        )
        self.assertEqual(_random_state(mediator), before_rng)


class TestGM06cJustInTimeService(unittest.TestCase):
    def test_exact_interval_preserves_planned_identity_then_executes_it(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6305)
        riders = [
            boardable_passenger(
                mediator,
                start,
                end,
                path,
                name=f"board-{index}",
            )
            for index in range(3)
        ]

        mediator.move_passengers(499)

        self.assertEqual(metro.passengers, [])
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (1, 499),
        )
        _assert_board_action(self, metro, riders[0])

        mediator.move_passengers(1)

        self.assertEqual(metro.passengers, [riders[0]])
        self.assertEqual(start.passengers, riders[1:])
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (500, 0),
        )
        _assert_board_action(self, metro, riders[1])

    def test_large_dt_consumes_successive_actions_and_keeps_residual(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6306)
        riders = [
            boardable_passenger(
                mediator,
                start,
                end,
                path,
                name=f"large-dt-{index}",
            )
            for index in range(3)
        ]

        mediator.move_passengers(1250)

        self.assertEqual(metro.passengers, riders[:2])
        self.assertEqual(start.passengers, riders[2:])
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (250, 250),
        )
        _assert_board_action(self, metro, riders[2])

    def test_dynamic_priority_change_rebinds_cache_and_resets_fraction(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6307)
        boarder = boardable_passenger(
            mediator,
            start,
            end,
            path,
            name="lower-priority-boarder",
        )
        mediator.move_passengers(250)
        _assert_board_action(self, metro, boarder)

        destination = onboard_passenger(
            mediator,
            metro,
            start,
            name="new-destination-unload",
        )
        mediator.move_passengers(0)

        action = _cached_action(self, metro)
        self.assertIsNotNone(action)
        assert action is not None
        kind, planned = action
        self.assertIn("destination", str(getattr(kind, "value", kind)).lower())
        self.assertIs(planned, destination)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (500, 0),
        )

    def test_no_executable_action_clears_timer_progress_and_cache(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6308)
        rider = boardable_passenger(
            mediator,
            start,
            end,
            path,
            name="only-boarder",
        )
        mediator.move_passengers(500)

        self.assertEqual(metro.passengers, [rider])
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (0, 0),
        )
        self.assertIsNone(_cached_action(self, metro))

    def test_base_and_carriage_capacity_have_no_phantom_final_interval(self) -> None:
        for attach in (False, True):
            with self.subTest(attach=attach):
                mediator, start, end, path, metro = make_two_station_game(
                    seed=6309 + int(attach)
                )
                if attach:
                    method = require_attribute(self, mediator, "attach_carriage")
                    self.assertTrue(method(path))
                expected = 12 if attach else 6
                riders = [
                    boardable_passenger(
                        mediator,
                        start,
                        end,
                        path,
                        name=f"capacity-{attach}-{index}",
                    )
                    for index in range(12)
                ]

                mediator.move_passengers(expected * 500)

                self.assertEqual(metro.passengers, riders[:expected])
                self.assertEqual(start.passengers, riders[expected:])
                self.assertEqual(metro.capacity, expected)
                self.assertEqual(
                    (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
                    (0, 0),
                )
                self.assertIsNone(_cached_action(self, metro))


class TestGM06cCompositionTimerReconciliation(unittest.TestCase):
    def test_attach_and_safe_detach_preserve_same_action_fraction_at_boundaries(
        self,
    ) -> None:
        for mutation_name in ("attach_carriage", "detach_carriage"):
            for elapsed in (249, 250, 499):
                with self.subTest(mutation=mutation_name, elapsed=elapsed):
                    mediator, start, end, path, metro = make_two_station_game(
                        seed=6320 + elapsed
                    )
                    attach = require_attribute(self, mediator, "attach_carriage")
                    if mutation_name == "detach_carriage":
                        self.assertTrue(attach(path))
                    rider = boardable_passenger(
                        mediator,
                        start,
                        end,
                        path,
                        name=f"stable-{mutation_name}-{elapsed}",
                    )
                    mediator.move_passengers(elapsed)
                    _assert_board_action(self, metro, rider)

                    mutate = require_attribute(self, mediator, mutation_name)
                    self.assertTrue(mutate(path))

                    self.assertEqual(
                        (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
                        (500 - elapsed, elapsed),
                    )
                    _assert_board_action(self, metro, rider)

    def test_exact_500_executes_before_later_attach_or_detach(self) -> None:
        for mutation_name in ("attach_carriage", "detach_carriage"):
            with self.subTest(mutation=mutation_name):
                mediator, start, end, path, metro = make_two_station_game(seed=6321)
                attach = require_attribute(self, mediator, "attach_carriage")
                if mutation_name == "detach_carriage":
                    self.assertTrue(attach(path))
                rider = boardable_passenger(
                    mediator,
                    start,
                    end,
                    path,
                    name=f"mature-{mutation_name}",
                )

                mediator.move_passengers(500)
                self.assertEqual(metro.passengers, [rider])
                mutate = require_attribute(self, mediator, mutation_name)
                self.assertTrue(mutate(path))

                self.assertEqual(
                    (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
                    (0, 0),
                )
                self.assertIsNone(_cached_action(self, metro))

    def test_attach_enables_fresh_boarding_interval_at_real_station(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6322)
        for index in range(6):
            onboard_passenger(
                mediator,
                metro,
                end,
                name=f"full-base-{index}",
            )
        rider = boardable_passenger(
            mediator,
            start,
            end,
            path,
            name="newly-enabled",
        )
        mediator.move_passengers(0)
        self.assertIsNone(_cached_action(self, metro))

        attach = require_attribute(self, mediator, "attach_carriage")
        self.assertTrue(attach(path))

        self.assertEqual(metro.capacity, 12)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (500, 0),
        )
        _assert_board_action(self, metro, rider)

    def test_detach_invalidates_boarding_action_at_exact_safe_occupancy(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6323)
        attach = require_attribute(self, mediator, "attach_carriage")
        detach = require_attribute(self, mediator, "detach_carriage")
        self.assertTrue(attach(path))
        for index in range(6):
            onboard_passenger(
                mediator,
                metro,
                end,
                name=f"safe-boundary-{index}",
            )
        rider = boardable_passenger(
            mediator,
            start,
            end,
            path,
            name="invalidated-boarder",
        )
        mediator.move_passengers(249)
        _assert_board_action(self, metro, rider)

        self.assertTrue(detach(path))

        self.assertEqual((len(metro.passengers), metro.capacity), (6, 6))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (0, 0),
        )
        self.assertIsNone(_cached_action(self, metro))


if __name__ == "__main__":
    unittest.main()

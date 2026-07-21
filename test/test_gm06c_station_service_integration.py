from __future__ import annotations

import copy
import os
import random
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.triangle import Triangle
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from test.gm06c_simulation_ui_support import (
    boardable_passenger,
    make_two_station_game,
    onboard_passenger,
    require_attribute,
)
from travel_plan import TravelPlan


def _quiet(mediator) -> None:
    future = 10**9
    mediator.passenger_spawning_step = future
    mediator.passenger_spawning_interval_step = future
    mediator.overdue_passenger_threshold = future
    for station in mediator.stations:
        mediator.station_steps_since_last_spawn[station] = 0
        mediator.station_spawn_interval_steps[station] = future


def _action(testcase: unittest.TestCase, metro):
    value = require_attribute(testcase, metro, "_station_service_action")
    testcase.assertIsNotNone(value)
    testcase.assertIsInstance(value, tuple)
    testcase.assertEqual(len(value), 2)
    return value


def _assert_action(testcase, metro, kind: str, passenger) -> None:
    actual_kind, actual_passenger = _action(testcase, metro)
    label = str(getattr(actual_kind, "value", actual_kind)).lower()
    testcase.assertIn(kind, label)
    testcase.assertIs(actual_passenger, passenger)


def _rng_state(mediator):
    return (
        mediator.context.python_random.getstate(),
        copy.deepcopy(mediator.context.numpy_random.bit_generator.state),
    )


class TestGM06cIncrementTimeServiceSeams(unittest.TestCase):
    def test_existing_station_stop_starts_before_movement_and_consumes_exact_dt(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6370)
        _quiet(mediator)
        rider = boardable_passenger(
            mediator,
            start,
            end,
            path,
            name="pre-move-seam",
        )
        original = mediator.start_station_stop_if_needed
        calls = []

        def recording(candidate, station, node_map):
            calls.append((candidate, station))
            return original(candidate, station, node_map)

        mediator.start_station_stop_if_needed = recording

        mediator.increment_time(249)

        self.assertEqual(calls, [(metro, start)])
        self.assertIs(metro.current_station, start)
        self.assertNotIn(rider, metro.passengers)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (251, 249),
        )
        _assert_action(self, metro, "board", rider)

    def test_arrival_stop_starts_at_post_move_seam_and_services_same_tick(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6371)
        _quiet(mediator)
        rider = boardable_passenger(
            mediator,
            end,
            start,
            path,
            name="arrival-seam",
        )
        metro.current_station = None
        metro.position = metro.current_segment.segment_end
        original = mediator.start_station_stop_if_needed
        calls = []

        def recording(candidate, station, node_map):
            calls.append((candidate, station))
            return original(candidate, station, node_map)

        mediator.start_station_stop_if_needed = recording

        mediator.increment_time(1)

        self.assertEqual(calls, [(metro, end)])
        self.assertIs(metro.current_station, end)
        self.assertTrue(metro.just_arrived_and_stopped)
        self.assertNotIn(rider, metro.passengers)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (499, 1),
        )
        _assert_action(self, metro, "board", rider)


class TestGM06cExecutedServiceInterleaving(unittest.TestCase):
    def test_destination_then_board_then_unblocked_transfer_replans_each_identity(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6372)
        start.capacity = 1
        destination = onboard_passenger(
            mediator,
            metro,
            start,
            name="destination-first",
        )
        transfer_shape = Triangle(config.station_color, config.station_size)
        transfer = Passenger(transfer_shape)
        transfer.id = "transfer-after-room"
        metro.add_passenger(transfer)
        mediator.passengers.append(transfer)
        mediator.travel_plans[transfer] = TravelPlan([Node(start)])
        boarder = boardable_passenger(
            mediator,
            start,
            end,
            path,
            name="board-to-free-room",
        )

        mediator.move_passengers(500)

        self.assertTrue(destination.is_at_destination)
        self.assertNotIn(destination, mediator.passengers)
        self.assertEqual(start.passengers, [boarder])
        _assert_action(self, metro, "board", boarder)

        mediator.move_passengers(500)

        self.assertEqual(start.passengers, [])
        self.assertIn(boarder, metro.passengers)
        _assert_action(self, metro, "transfer", transfer)

        mediator.move_passengers(500)

        self.assertEqual(start.passengers, [transfer])
        self.assertEqual(metro.passengers, [boarder])
        self.assertIsNone(require_attribute(self, metro, "_station_service_action"))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (0, 0),
        )

    def test_route_search_execution_commits_rng_and_plan_effects_exactly_once(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6373)
        alternate = Station(
            Circle(config.station_color, config.station_size),
            Point(900, 700),
        )
        mediator.stations.append(alternate)
        mediator.all_stations.append(alternate)
        rider = Passenger(end.shape)
        rider.id = "route-search-boarder"
        start.add_passenger(rider)
        mediator.passengers.append(rider)
        plans_object = mediator.travel_plans
        python_before = mediator.context.python_random.getstate()
        numpy_before = copy.deepcopy(mediator.context.numpy_random.bit_generator.state)
        expected_random = random.Random()
        expected_random.setstate(python_before)
        destinations = [end, alternate]
        expected_random.shuffle(destinations)
        python_after_one_search = expected_random.getstate()
        node_map = build_station_nodes_dict(mediator.stations, mediator.paths)

        mediator.start_station_stop_if_needed(metro, start, node_map)

        self.assertIs(mediator.travel_plans, plans_object)
        self.assertNotIn(rider, mediator.travel_plans)
        self.assertEqual(mediator.context.python_random.getstate(), python_before)
        self.assertEqual(
            mediator.context.numpy_random.bit_generator.state,
            numpy_before,
        )
        _assert_action(self, metro, "board", rider)

        mediator.move_passengers(499)
        self.assertNotIn(rider, mediator.travel_plans)
        self.assertEqual(mediator.context.python_random.getstate(), python_before)
        _assert_action(self, metro, "board", rider)

        mediator.move_passengers(1)

        self.assertIs(mediator.travel_plans, plans_object)
        self.assertIn(rider, metro.passengers)
        plan = mediator.travel_plans[rider]
        self.assertIs(plan.next_path, path)
        self.assertIs(plan.get_next_station(), end)
        self.assertEqual(
            mediator.context.python_random.getstate(),
            python_after_one_search,
        )
        self.assertEqual(
            mediator.context.numpy_random.bit_generator.state,
            numpy_before,
        )


class TestGM06cCompositionReconciliationContext(unittest.TestCase):
    def test_paused_real_station_mutations_preserve_active_identity_and_fraction(
        self,
    ) -> None:
        for mutation_name in ("attach_carriage", "detach_carriage"):
            with self.subTest(mutation=mutation_name):
                mediator, start, end, path, metro = make_two_station_game(seed=6374)
                attach = require_attribute(self, mediator, "attach_carriage")
                if mutation_name == "detach_carriage":
                    self.assertTrue(attach(path))
                rider = boardable_passenger(
                    mediator,
                    start,
                    end,
                    path,
                    name=f"paused-{mutation_name}",
                )
                mediator.move_passengers(249)
                before_action = _action(self, metro)
                before_clock = (mediator.time_ms, mediator.steps)
                self.assertIs(metro.current_station, start)
                self.assertIn(start, path.stations)

                mediator.is_paused = True
                mutate = require_attribute(self, mediator, mutation_name)
                self.assertTrue(mutate(path))

                self.assertEqual((mediator.time_ms, mediator.steps), before_clock)
                self.assertEqual(
                    (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
                    (251, 249),
                )
                after_action = _action(self, metro)
                self.assertEqual(after_action[0], before_action[0])
                self.assertIs(after_action[1], rider)

    def test_moving_mutations_leave_canonical_service_timing_untouched(self) -> None:
        for mutation_name in ("attach_carriage", "detach_carriage"):
            with self.subTest(mutation=mutation_name):
                mediator, _start, _end, path, metro = make_two_station_game(seed=6375)
                attach = require_attribute(self, mediator, "attach_carriage")
                if mutation_name == "detach_carriage":
                    self.assertTrue(attach(path))
                segment = metro.current_segment
                metro.current_station = None
                metro.position = Point(
                    (segment.segment_start.left + segment.segment_end.left) / 2,
                    (segment.segment_start.top + segment.segment_end.top) / 2,
                )
                before = (
                    metro.stop_time_remaining_ms,
                    metro.boarding_progress_ms,
                    require_attribute(self, metro, "_station_service_action"),
                    metro.speed,
                    mediator.time_ms,
                    mediator.steps,
                )
                self.assertIsNone(metro.current_station)
                self.assertEqual(before[:3], (0, 0, None))

                mutate = require_attribute(self, mediator, mutation_name)
                self.assertTrue(mutate(path))

                self.assertEqual(
                    (
                        metro.stop_time_remaining_ms,
                        metro.boarding_progress_ms,
                        require_attribute(self, metro, "_station_service_action"),
                        metro.speed,
                        mediator.time_ms,
                        mediator.steps,
                    ),
                    before,
                )

    def test_unplanned_route_search_is_pure_during_attach_until_execution(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6376)
        alternate = Station(
            Circle(config.station_color, config.station_size),
            Point(900, 700),
        )
        mediator.stations.append(alternate)
        mediator.all_stations.append(alternate)
        for index in range(metro.capacity):
            onboard_passenger(
                mediator,
                metro,
                end,
                name=f"composition-full-{index}",
            )
        rider = Passenger(end.shape)
        rider.id = "composition-route-search"
        start.add_passenger(rider)
        mediator.passengers.append(rider)
        plans_object = mediator.travel_plans
        plan_items = tuple(plans_object.items())
        before_rng = _rng_state(mediator)
        expected_random = random.Random()
        expected_random.setstate(before_rng[0])
        destinations = [end, alternate]
        expected_random.shuffle(destinations)
        after_one_search = expected_random.getstate()

        attach = require_attribute(self, mediator, "attach_carriage")
        self.assertTrue(attach(path))

        self.assertIs(mediator.travel_plans, plans_object)
        self.assertEqual(tuple(mediator.travel_plans.items()), plan_items)
        self.assertNotIn(rider, mediator.travel_plans)
        self.assertEqual(_rng_state(mediator), before_rng)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (500, 0),
        )
        _assert_action(self, metro, "board", rider)

        mediator.move_passengers(499)
        self.assertNotIn(rider, mediator.travel_plans)
        self.assertEqual(_rng_state(mediator), before_rng)
        _assert_action(self, metro, "board", rider)

        mediator.move_passengers(1)
        self.assertIn(rider, metro.passengers)
        self.assertIs(mediator.travel_plans, plans_object)
        self.assertIs(mediator.travel_plans[rider].next_path, path)
        self.assertEqual(
            mediator.context.python_random.getstate(),
            after_one_search,
        )
        self.assertEqual(
            mediator.context.numpy_random.bit_generator.state,
            before_rng[1],
        )


if __name__ == "__main__":
    unittest.main()

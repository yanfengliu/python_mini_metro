from __future__ import annotations

import os
import random
import sys
import unittest
from copy import deepcopy
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import station_color, station_size
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.pentagon import Pentagon
from geometry.point import Point
from geometry.rect import Rect
from geometry.triangle import Triangle
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from mediator import Mediator
from travel_plan import TravelPlan


def _station(shape, x: int) -> Station:
    return Station(shape, Point(x, 0))


def build_mediator(seed: int = 4105) -> tuple[Mediator, list[Station]]:
    mediator = Mediator(seed=seed)
    stations = [
        _station(Rect(station_color, 2 * station_size, 2 * station_size), 0),
        _station(Circle(station_color, station_size), 100),
        _station(Triangle(station_color, station_size), 200),
        _station(Pentagon(station_color, station_size), 300),
        _station(Rect(station_color, 2 * station_size, 2 * station_size), 400),
        _station(Circle(station_color, station_size), 500),
        _station(Triangle(station_color, station_size), 600),
        _station(Pentagon(station_color, station_size), 700),
    ]
    mediator.all_stations = stations
    mediator.stations = stations
    mediator.paths = []
    mediator.metros = []
    mediator.passengers = []
    mediator.travel_plans = {}
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.station_spawn_interval_steps = {station: 100 for station in stations}
    mediator.station_steps_since_last_spawn = {station: 0 for station in stations}
    return mediator, stations


def create_path(mediator: Mediator, indices: list[int], *, add_metro: bool):
    mediator.num_metros = len(mediator.metros) + int(add_metro)
    path = mediator.create_path_from_station_indices(indices, False)
    if path is None:
        raise AssertionError(f"failed to create path through {indices}")
    return path


def arrive_at_end(path):
    metro = path.metros[0]
    path.move_metro(metro, 1_000_000, should_stop_at_next_station=True)
    if metro.current_station is not path.stations[-1]:
        raise AssertionError("fixture metro did not arrive at the path endpoint")
    return metro


def add_passenger(mediator: Mediator, holder, destination: Station) -> Passenger:
    passenger = Passenger(destination.shape)
    holder.add_passenger(passenger)
    mediator.passengers.append(passenger)
    return passenger


def install_plan(
    mediator: Mediator, passenger: Passenger, path, *targets: Station
) -> TravelPlan:
    graph = build_station_nodes_dict(mediator.stations, mediator.paths)
    plan = TravelPlan([graph[target] for target in targets])
    plan.get_next_station()
    plan.next_path = path
    mediator.travel_plans[passenger] = plan
    return plan


def build_onboard_network(
    *, seed: int = 4105, target_riders: int = 0, other_riders: int = 1
):
    mediator, stations = build_mediator(seed)
    target = create_path(mediator, [0, 1], add_metro=target_riders > 0)
    other = create_path(mediator, [2, 3], add_metro=other_riders > 0)
    target_metro = arrive_at_end(target) if target_riders else None
    other_metro = arrive_at_end(other) if other_riders else None
    target_passengers = []
    other_passengers = []
    for _ in range(target_riders):
        passenger = add_passenger(mediator, target_metro, stations[3])
        install_plan(mediator, passenger, target, stations[1])
        target_passengers.append(passenger)
    for _ in range(other_riders):
        passenger = add_passenger(mediator, other_metro, stations[1])
        install_plan(mediator, passenger, other, stations[3])
        other_passengers.append(passenger)
    return (
        mediator,
        stations,
        target,
        other,
        target_metro,
        other_metro,
        target_passengers,
        other_passengers,
    )


def expected_shuffle_state(mediator: Mediator, shape_types) -> object:
    clone = random.Random()
    clone.setstate(mediator.context.python_random.getstate())
    for shape_type in shape_types:
        values = [
            station for station in mediator.stations if station.shape.type == shape_type
        ]
        clone.shuffle(values)
    return clone.getstate()


class TestGM05aPassengerTransitions(unittest.TestCase):
    def test_stable_waiting_refresh_handles_arrival_route_fallback_and_rng_order(self):
        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        arrival = add_passenger(mediator, stations[0], stations[4])
        routed = add_passenger(mediator, stations[0], stations[1])
        fallback = add_passenger(mediator, stations[0], stations[2])
        for passenger in (arrival, routed, fallback):
            mediator.travel_plans[passenger] = TravelPlan([])
        shape_order = [
            arrival.destination_shape.type,
            routed.destination_shape.type,
            fallback.destination_shape.type,
        ]
        expected_python = expected_shuffle_state(mediator, shape_order)
        numpy_before = deepcopy(mediator.context.numpy_random.bit_generator.state)
        original = mediator._replan_passenger_at_station
        calls = []

        def scoped(passenger, station, graph):
            emptied = mediator.travel_plans[passenger]
            self.assertIsNone(emptied.next_path)
            self.assertIsNone(emptied.next_station)
            self.assertEqual(emptied.node_path, [])
            self.assertEqual(emptied.next_station_idx, 0)
            calls.append((passenger, station, graph))
            return original(passenger, station, graph)

        mediator._replan_passenger_at_station = scoped

        self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))

        self.assertEqual([call[0] for call in calls], [arrival, routed, fallback])
        self.assertNotIn(arrival, stations[0].passengers)
        self.assertNotIn(arrival, mediator.passengers)
        self.assertTrue(arrival.is_at_destination)
        self.assertNotIn(arrival, mediator.travel_plans)
        self.assertIs(mediator.travel_plans[routed].next_path, target)
        self.assertIs(mediator.travel_plans[routed].next_station, stations[1])
        self.assertEqual(mediator.travel_plans[fallback].node_path, [])
        self.assertIsNone(mediator.travel_plans[fallback].next_path)
        self.assertEqual(mediator.context.python_random.getstate(), expected_python)
        self.assertEqual(
            mediator.context.numpy_random.bit_generator.state, numpy_before
        )

    def test_all_onboard_plans_become_fresh_one_alight_markers(self):
        (
            mediator,
            stations,
            target,
            other,
            _,
            _,
            target_riders,
            other_riders,
        ) = build_onboard_network(target_riders=1, other_riders=1)
        riders = [*target_riders, *other_riders]
        old_nodes = [mediator.travel_plans[rider].node_path[0] for rider in riders]
        old_plans = [mediator.travel_plans[rider] for rider in riders]

        self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))

        for rider, plan, old_node, line, station in zip(
            riders,
            old_plans,
            old_nodes,
            (target, other),
            (stations[1], stations[3]),
        ):
            self.assertIs(mediator.travel_plans[rider], plan)
            self.assertEqual(plan.next_station_idx, 0)
            self.assertIs(plan.next_station, station)
            self.assertIs(plan.next_path, line)
            self.assertEqual(len(plan.node_path), 1)
            self.assertIsNot(plan.node_path[0], old_node)
            self.assertIs(plan.node_path[0].station, station)
        self.assertEqual(old_plans[1].node_path[0].paths, {target, other})

    def test_raw_onboard_plan_invariants_reject_without_getter_mutation(self):
        cases = ("bool-cursor", "past-cursor", "stale-cache", "wrong-path", "equal-id")
        for case in cases:
            with self.subTest(case=case):
                (
                    mediator,
                    stations,
                    target,
                    other,
                    _,
                    _,
                    _,
                    riders,
                ) = build_onboard_network(other_riders=1)
                rider = riders[0]
                plan = mediator.travel_plans[rider]
                if case == "bool-cursor":
                    plan.next_station_idx = True
                elif case == "past-cursor":
                    plan.next_station_idx = 1
                elif case == "stale-cache":
                    plan.next_station = stations[2]
                elif case == "wrong-path":
                    plan.next_path = target
                else:
                    foreign = _station(Pentagon(station_color, station_size), 900)
                    foreign.id = stations[3].id
                    plan.node_path[0] = Node(foreign)
                    plan.next_station = foreign
                before = (
                    list(target.stations),
                    plan.next_path,
                    plan.next_station,
                    plan.next_station_idx,
                    list(plan.node_path),
                    mediator.context.python_random.getstate(),
                    deepcopy(mediator.context.numpy_random.bit_generator.state),
                )

                self.assertFalse(mediator.replace_path(target, [3, 0, 1], False))
                self.assertEqual(list(target.stations), before[0])
                self.assertIs(plan.next_path, before[1])
                self.assertIs(plan.next_station, before[2])
                self.assertEqual(plan.next_station_idx, before[3])
                self.assertEqual(plan.node_path, before[4])
                self.assertEqual(mediator.context.python_random.getstate(), before[5])
                self.assertEqual(
                    mediator.context.numpy_random.bit_generator.state, before[6]
                )

    def test_network_holder_and_plan_aliases_reject_atomically(self):
        for case in (
            "path-only-metro",
            "duplicate-holder",
            "duplicate-global",
            "plan-alias",
            "node-list-alias",
            "holder-list-alias",
        ):
            with self.subTest(case=case):
                (
                    mediator,
                    stations,
                    target,
                    _,
                    _,
                    other_metro,
                    _,
                    riders,
                ) = build_onboard_network(
                    other_riders=2 if case in ("plan-alias", "node-list-alias") else 1
                )
                if case == "path-only-metro":
                    mediator.metros.remove(other_metro)
                elif case == "duplicate-holder":
                    stations[2].passengers.append(riders[0])
                elif case == "duplicate-global":
                    mediator.passengers.append(riders[0])
                elif case == "plan-alias":
                    mediator.travel_plans[riders[1]] = mediator.travel_plans[riders[0]]
                elif case == "node-list-alias":
                    mediator.travel_plans[riders[1]].node_path = mediator.travel_plans[
                        riders[0]
                    ].node_path
                else:
                    stations[5].passengers = stations[4].passengers
                state = mediator.context.python_random.getstate()
                topology = list(target.stations)

                self.assertFalse(mediator.replace_path(target, [3, 0, 1], False))
                self.assertEqual(target.stations, topology)
                self.assertEqual(mediator.context.python_random.getstate(), state)

    def test_marker_alight_dispatches_one_scoped_fresh_route(self):
        mediator, stations, target, _, _, metro, _, riders = build_onboard_network()
        rider = riders[0]
        marker = mediator.travel_plans[rider]
        self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))
        original = mediator._replan_passenger_at_station
        calls = []

        def scoped(passenger, station, graph):
            emptied = mediator.travel_plans[passenger]
            self.assertIsNone(emptied.next_path)
            self.assertIsNone(emptied.next_station)
            self.assertEqual(emptied.node_path, [])
            self.assertEqual(emptied.next_station_idx, 0)
            calls.append((passenger, station, graph))
            return original(passenger, station, graph)

        mediator._replan_passenger_at_station = scoped
        expected_python = expected_shuffle_state(
            mediator, [rider.destination_shape.type]
        )
        metro.stop_time_remaining_ms = 500
        metro.boarding_progress_ms = 0

        mediator.move_passengers(500)

        self.assertEqual([(item[0], item[1]) for item in calls], [(rider, stations[3])])
        self.assertIn(rider, stations[3].passengers)
        self.assertNotIn(rider, metro.passengers)
        self.assertIsNot(mediator.travel_plans[rider], marker)
        self.assertIs(mediator.travel_plans[rider].next_path, target)
        self.assertIs(mediator.travel_plans[rider].next_station, stations[1])
        self.assertEqual(mediator.context.python_random.getstate(), expected_python)

    def test_direct_scoped_replanner_resolves_collaborators_at_effect_points(self):
        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        passenger = add_passenger(mediator, stations[0], stations[1])
        old_plan = TravelPlan([])
        mediator.travel_plans[passenger] = old_plan
        graph = build_station_nodes_dict(mediator.stations, mediator.paths)
        route = [graph[stations[0]], graph[stations[1]]]
        search = MagicMock(return_value=route)
        reducer = MagicMock(side_effect=lambda value: value)
        created_plan = TravelPlan(route[1:])
        factory = MagicMock(return_value=created_plan)
        search_slot = [MagicMock(side_effect=AssertionError("stale search"))]
        factory_slot = [MagicMock(side_effect=AssertionError("stale factory"))]

        def best_path_finder(_station, _destinations, _graph, **callbacks):
            self.assertIs(mediator.travel_plans[passenger], old_plan)
            self.assertIsNone(old_plan.next_path)
            self.assertIsNone(old_plan.next_station)
            self.assertEqual(old_plan.node_path, [])
            search_slot[0] = search
            factory_slot[0] = factory
            mediator.skip_stations_on_same_path = reducer
            self.assertEqual(callbacks["find_node_path"](route[0], route[1]), route)
            self.assertIs(callbacks["get_reduce_node_path"](), reducer)
            return route

        mediator._passenger_flow.replan_passenger_at_station(
            mediator,
            passenger,
            stations[0],
            graph,
            get_best_path_finder=lambda: best_path_finder,
            get_search=lambda: search_slot[0],
            get_plan_factory=lambda: factory_slot[0],
        )
        search.assert_called_once_with(route[0], route[1])
        factory.assert_called_once_with(route[1:])
        self.assertIs(mediator.travel_plans[passenger], created_plan)
        self.assertIs(created_plan.next_path, target)

    def test_two_marker_alights_are_scoped_and_leave_unrelated_fallback_untouched(self):
        mediator, stations, target, _, _, metro, _, riders = build_onboard_network(
            other_riders=2
        )
        fallback = add_passenger(mediator, stations[4], stations[7])
        mediator.travel_plans[fallback] = TravelPlan([])
        self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))
        fallback_plan = mediator.travel_plans[fallback]
        original = mediator._replan_passenger_at_station
        calls = []

        def scoped(passenger, station, graph):
            calls.append(passenger)
            return original(passenger, station, graph)

        mediator._replan_passenger_at_station = scoped
        expected_python = expected_shuffle_state(
            mediator, [rider.destination_shape.type for rider in riders]
        )
        metro.stop_time_remaining_ms = 1000
        metro.boarding_progress_ms = 0

        mediator.move_passengers(1000)

        self.assertEqual(calls, riders)
        self.assertTrue(all(rider in stations[3].passengers for rider in riders))
        self.assertIs(mediator.travel_plans[fallback], fallback_plan)
        self.assertEqual(fallback_plan.node_path, [])
        self.assertEqual(mediator.context.python_random.getstate(), expected_python)

    def test_destination_precedes_marker_replanning(self):
        mediator, stations, target, other, _, metro, _, riders = build_onboard_network()
        rider = riders[0]
        rider.destination_shape = stations[3].shape
        install_plan(mediator, rider, other, stations[3])
        self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))
        mediator._replan_passenger_at_station = MagicMock()
        deliveries = mediator.deliveries
        metro.stop_time_remaining_ms = 500
        metro.boarding_progress_ms = 0

        mediator.move_passengers(500)

        self.assertTrue(rider.is_at_destination)
        self.assertNotIn(rider, mediator.passengers)
        self.assertNotIn(rider, mediator.travel_plans)
        self.assertEqual(mediator.deliveries, deliveries + 1)
        mediator._replan_passenger_at_station.assert_not_called()

    def test_full_station_preserves_marker_and_matches_legacy_rng_control(self):
        subject = build_onboard_network(seed=991, other_riders=1)
        control = build_onboard_network(seed=991, other_riders=1)
        for bundle in (subject, control):
            mediator, stations, target, _, _, metro, _, _ = bundle
            self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))
            for _ in range(stations[3].capacity):
                waiting = add_passenger(mediator, stations[3], stations[7])
                plan = TravelPlan([Node(stations[1])])
                plan.get_next_station()
                plan.next_path = target
                mediator.travel_plans[waiting] = plan
            metro.stop_time_remaining_ms = 500
            metro.boarding_progress_ms = 0
        subject_mediator, stations, _, _, _, subject_metro, _, riders = subject
        (
            control_mediator,
            control_stations,
            _,
            control_line,
            _,
            control_metro,
            _,
            control_riders,
        ) = control
        rider = riders[0]
        marker = subject_mediator.travel_plans[rider]
        marker_state = (
            marker.next_path,
            marker.next_station,
            marker.next_station_idx,
            marker.node_path,
            list(marker.node_path),
        )
        graph = build_station_nodes_dict(
            control_mediator.stations, control_mediator.paths
        )
        ordinary = TravelPlan([graph[control_stations[3]], graph[control_stations[1]]])
        ordinary.get_next_station()
        ordinary.next_path = control_line
        control_mediator.travel_plans[control_riders[0]] = ordinary
        control_mediator.context.python_random.setstate(
            subject_mediator.context.python_random.getstate()
        )
        control_mediator.context.numpy_random.bit_generator.state = deepcopy(
            subject_mediator.context.numpy_random.bit_generator.state
        )
        python_before = subject_mediator.context.python_random.getstate()
        subject_mediator._replan_passenger_at_station = MagicMock()

        subject_mediator.move_passengers(500)
        control_mediator.move_passengers(500)

        self.assertIn(rider, subject_metro.passengers)
        self.assertIs(marker.next_path, marker_state[0])
        self.assertIs(marker.next_station, marker_state[1])
        self.assertEqual(marker.next_station_idx, marker_state[2])
        self.assertIs(marker.node_path, marker_state[3])
        self.assertEqual(marker.node_path, marker_state[4])
        subject_mediator._replan_passenger_at_station.assert_not_called()
        self.assertNotEqual(
            subject_mediator.context.python_random.getstate(), python_before
        )
        self.assertEqual(
            subject_mediator.context.python_random.getstate(),
            control_mediator.context.python_random.getstate(),
        )
        self.assertEqual(
            subject_mediator.context.numpy_random.bit_generator.state,
            control_mediator.context.numpy_random.bit_generator.state,
        )


if __name__ == "__main__":
    unittest.main()

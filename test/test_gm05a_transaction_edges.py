from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import mediator as mediator_module
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from geometry.point import Point
from recursive_checkpoint import canonical_checkpoint
from test.test_gm05a_metro_continuity import (
    _build_network,
    _point,
    _pose,
)
from test.test_gm05a_passenger_transitions import build_mediator, create_path
from travel_plan import TravelPlan


class _FailingTopologyList(list):
    def __init__(self, values):
        super().__init__(values)
        self.armed = True

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.armed and isinstance(key, slice):
            self.armed = False
            raise RuntimeError("topology write fault")


class _FailingMetro(Metro):
    def __init__(self):
        self.fail_binding = False
        super().__init__()

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name == "current_segment" and getattr(self, "fail_binding", False):
            self.fail_binding = False
            raise RuntimeError("metro binding fault")


class TestGM05aTransactionEdges(unittest.TestCase):
    def test_valid_noop_preflights_but_resolves_no_effect_collaborators(self):
        mediator, _, path, metros = _build_network()
        metro = metros[0]
        before = canonical_checkpoint(_as_env(mediator))
        path_factory = MagicMock(side_effect=AssertionError("factory resolved"))
        graph_builder = MagicMock(side_effect=AssertionError("graph resolved"))
        replanner = MagicMock(side_effect=AssertionError("replanner resolved"))

        with (
            patch.object(mediator_module, "Path", path_factory),
            patch.object(mediator_module, "build_station_nodes_dict", graph_builder),
        ):
            mediator._replan_passenger_at_station = replanner
            self.assertTrue(mediator.replace_path(path, [0, 1, 2], False))

        path_factory.assert_not_called()
        graph_builder.assert_not_called()
        replanner.assert_not_called()
        self.assertEqual(canonical_checkpoint(_as_env(mediator)), before)

        metro.current_segment_idx = 1
        invalid_before = canonical_checkpoint(_as_env(mediator))
        self.assertFalse(mediator.replace_path(path, [0, 1, 2], False))
        self.assertEqual(canonical_checkpoint(_as_env(mediator)), invalid_before)

        zero_mediator, zero_stations, zero_path, _ = _build_network(
            route=(0, 1), path_order=1
        )
        zero_stations[1].position = Point(
            zero_stations[0].position.left, zero_stations[0].position.top
        )
        zero_stations[1].shape.position = zero_stations[1].position
        zero_path.rebuild_geometry()
        zero_before = canonical_checkpoint(_as_env(zero_mediator))
        self.assertTrue(zero_mediator.replace_path(zero_path, [0, 1], False))
        self.assertEqual(canonical_checkpoint(_as_env(zero_mediator)), zero_before)

        angled, angled_stations, angled_path, _ = _build_network(
            route=(0, 1, 2), path_order=1, metro_count=0
        )
        for station, (left, top) in zip(
            angled_stations,
            ((0, 0), (27, -41), (123, 43), (180, 70)),
        ):
            station.position = Point(left, top)
            station.shape.position = station.position
        angled_path.rebuild_geometry()
        self.assertTrue(angled.replace_path(angled_path, [0, 1, 2, 3], False))

    def test_distinct_indices_aliasing_one_station_reject_without_effects(self):
        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        mediator.stations[3] = mediator.stations[2]
        topology = list(target.stations)
        python_rng = mediator.context.python_random.getstate()
        numpy_rng = deepcopy(mediator.context.numpy_random.bit_generator.state)

        self.assertFalse(mediator.replace_path(target, [0, 1, 2, 3], False))

        self.assertEqual(target.stations, topology)
        self.assertEqual(mediator.context.python_random.getstate(), python_rng)
        self.assertEqual(mediator.context.numpy_random.bit_generator.state, numpy_rng)

        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        other = create_path(mediator, [0, 1], add_metro=False)
        other.stations = target.stations
        topology = list(target.stations)
        self.assertFalse(mediator.replace_path(target, [3, 0, 1], False))
        self.assertEqual(target.stations, topology)
        self.assertEqual(other.stations, topology)

        mediator, _ = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        target.padding_segments = mediator.passengers
        self.assertFalse(mediator.replace_path(target, [3, 0, 1], False))
        self.assertEqual(mediator.passengers, [])

        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        passenger = Passenger(stations[3].shape)
        stations[4].add_passenger(passenger)
        mediator.passengers.append(passenger)
        plan = TravelPlan([])
        mediator.travel_plans[passenger] = plan
        target.padding_segments = plan.node_path
        self.assertFalse(mediator.replace_path(target, [3, 0, 1], False))
        self.assertEqual(plan.node_path, [])

    def test_factory_cannot_return_or_alias_a_live_path(self):
        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        other = create_path(mediator, [2, 3], add_metro=False)
        target_before = list(target.stations)
        other_before = list(other.stations)
        rng_before = mediator.context.python_random.getstate()

        with patch.object(mediator_module, "Path", return_value=other):
            with self.assertRaisesRegex(ValueError, "live path"):
                mediator.replace_path(target, [3, 0, 1], False)

        self.assertEqual(target.stations, target_before)
        self.assertEqual(other.stations, other_before)
        self.assertEqual(mediator.context.python_random.getstate(), rng_before)

        candidate = Path(target.color)
        candidate.stations = target.stations
        with patch.object(mediator_module, "Path", return_value=candidate):
            with self.assertRaisesRegex(ValueError, "aliased.*storage"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        candidate = Path(target.color)
        candidate.rebuild_geometry = MagicMock(
            side_effect=lambda: candidate.stations.pop()
        )
        with patch.object(mediator_module, "Path", return_value=candidate):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        class MissingGeometryPath(Path):
            def rebuild_geometry(self):
                pass

        with patch.object(mediator_module, "Path", MissingGeometryPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        class WrongLoopPath(Path):
            def rebuild_geometry(self):
                self.is_looped = not self.is_looped
                super().rebuild_geometry()

        with patch.object(mediator_module, "Path", WrongLoopPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], True)
        self.assertEqual(target.stations, target_before)

        class AliasedGeometryPath(Path):
            def rebuild_geometry(self):
                super().rebuild_geometry()
                self.segments = target.segments
                self.path_segments = target.path_segments
                self.padding_segments = target.padding_segments

        with patch.object(mediator_module, "Path", AliasedGeometryPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        class WrongWidthPath(Path):
            def rebuild_geometry(self):
                super().rebuild_geometry()
                for segment in self.segments:
                    segment.line.width = float(segment.line.width)

        with patch.object(mediator_module, "Path", WrongWidthPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        class NoncanonicalGeometryPath(Path):
            def rebuild_geometry(self):
                super().rebuild_geometry()
                self.path_segments[0].path_order = float(self.path_order)
                self.path_segments[0].segment_start.left = str(
                    self.path_segments[0].segment_start.left
                )

        with patch.object(mediator_module, "Path", NoncanonicalGeometryPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        class InternallyAliasedGeometryPath(Path):
            def rebuild_geometry(self):
                super().rebuild_geometry()
                shared = self.path_segments[0].segment_end
                self.path_segments[1].segment_start = shared
                self.path_segments[1].line.start = shared
                self.padding_segments[0].segment_end = shared
                self.padding_segments[0].line.end = shared

        with patch.object(mediator_module, "Path", InternallyAliasedGeometryPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        class StationAliasedGeometryPath(Path):
            def rebuild_geometry(self):
                super().rebuild_geometry()
                shared = self.path_segments[0].start_station.position
                self.path_segments[0].segment_start = shared
                self.path_segments[0].line.start = shared

        with patch.object(mediator_module, "Path", StationAliasedGeometryPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        other.color = target.color
        other.path_order = target.path_order
        other.stations[:] = [stations[index] for index in (3, 0, 1)]
        other.rebuild_geometry()

        class SharedGeometryPath(Path):
            def rebuild_geometry(self):
                super().rebuild_geometry()
                self.segments[:] = other.segments
                self.path_segments[:] = other.path_segments
                self.padding_segments[:] = other.padding_segments

        with patch.object(mediator_module, "Path", SharedGeometryPath):
            with self.assertRaisesRegex(ValueError, "invalid candidate"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        candidate = Path(target.color)
        candidate.metros = target.metros
        with patch.object(mediator_module, "Path", return_value=candidate):
            with self.assertRaisesRegex(ValueError, "aliased.*storage"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(target.stations, target_before)

        candidate = Path(target.color)
        candidate.stations = mediator.passengers
        with patch.object(mediator_module, "Path", return_value=candidate):
            with self.assertRaisesRegex(ValueError, "aliased.*storage"):
                mediator.replace_path(target, [3, 0, 1], False)
        self.assertEqual(mediator.passengers, [])

    def test_scoped_route_re_resolves_plan_factory_and_reducer(self):
        mediator, stations = build_mediator()
        target = create_path(mediator, [0, 1], add_metro=False)
        passenger = Passenger(stations[1].shape)
        stations[0].add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.travel_plans[passenger] = TravelPlan([])
        original_reducer = mediator.skip_stations_on_same_path
        mediator.skip_stations_on_same_path = MagicMock(wraps=original_reducer)

        class ReboundPlan(TravelPlan):
            pass

        with patch.object(mediator_module, "TravelPlan", ReboundPlan):
            self.assertTrue(mediator.replace_path(target, [3, 0, 1], False))

        self.assertIsInstance(mediator.travel_plans[passenger], ReboundPlan)
        mediator.skip_stations_on_same_path.assert_called()

    def test_two_station_loop_maps_every_segment_and_direction(self):
        expected_indices = {0: 2, 1: 3, 2: 0, 3: 1}
        for old_index in range(4):
            for direction in (False, True):
                with self.subTest(index=old_index, direction=direction):
                    mediator, _, path, metros = _build_network(route=(0, 1), loop=True)
                    metro = metros[0]
                    segment = path.segments[old_index]
                    metro.current_segment = segment
                    metro.current_segment_idx = old_index
                    metro.is_forward = direction
                    metro.current_station = None
                    metro.position = Point(
                        (segment.segment_start.left + segment.segment_end.left) / 2,
                        (segment.segment_start.top + segment.segment_end.top) / 2,
                    )
                    pose = _pose(metro)

                    self.assertTrue(mediator.replace_path(path, [1, 0], True))

                    self.assertEqual(_point(metro.position), pose["coordinates"])
                    self.assertEqual(
                        metro.current_segment_idx, expected_indices[old_index]
                    )
                    self.assertEqual(metro.is_forward, direction)
                    self.assertIs(
                        metro.current_segment,
                        path.segments[expected_indices[old_index]],
                    )

    def test_backward_motion_and_both_linear_arrival_edges_remain_continuous(self):
        mediator, _, path, metros = _build_network()
        metro = metros[0]
        path.move_metro(metro, 2_000)
        path.move_metro(metro, 2_000)
        path.move_metro(metro, 2_000)
        self.assertFalse(metro.is_forward)
        path.move_metro(metro, 100)
        self.assertIsNone(metro.current_station)
        pose = _pose(metro)

        self.assertTrue(mediator.replace_path(path, [3, 0, 1, 2], False))
        self.assertEqual(_point(metro.position), pose["coordinates"])
        self.assertFalse(metro.is_forward)

        for prepend in (False, True):
            with self.subTest(prepend=prepend):
                subject, _, line, trains = _build_network(route=(0, 1))
                train = trains[0]
                line.move_metro(train, 2_000, should_stop_at_next_station=True)
                if prepend:
                    line.move_metro(train, 2_000)
                    line.move_metro(train, 2_000)
                    self.assertIs(train.current_station, line.stations[0])
                    replacement = [2, 0, 1]
                else:
                    self.assertIs(train.current_station, line.stations[1])
                    replacement = [0, 1, 2]
                stopped_pose = _pose(train)

                self.assertTrue(subject.replace_path(line, replacement, False))
                self.assertEqual(_point(train.position), stopped_pose["coordinates"])
                self.assertIs(train.current_station, stopped_pose["current_station"])

    def test_partial_topology_and_first_metro_binding_failures_roll_back(self):
        for fault in ("topology", "metro"):
            with self.subTest(fault=fault):
                mediator, _, path, metros = _build_network()
                env = _as_env(mediator)
                if fault == "topology":
                    failing = _FailingTopologyList(path.stations)
                    path.stations = failing
                else:
                    original = metros[0]
                    failing_metro = _FailingMetro()
                    failing_metro.__dict__.update(original.__dict__)
                    path.metros[:] = [failing_metro]
                    mediator.metros[:] = [failing_metro]
                    metros[:] = [failing_metro]
                    failing_metro.fail_binding = True
                before = canonical_checkpoint(env)

                with self.assertRaisesRegex(RuntimeError, f"{fault} .* fault"):
                    mediator.replace_path(path, [0, 1, 3, 2], False)

                self.assertEqual(canonical_checkpoint(env), before)
                if fault == "topology":
                    self.assertIs(path.stations, failing)
                else:
                    self.assertIs(path.metros[0], failing_metro)


def _as_env(mediator):
    from env import MiniMetroEnv

    env = MiniMetroEnv()
    env.mediator = mediator
    env.last_deliveries = mediator.deliveries
    env.last_line_credits = mediator.line_credits
    return env


if __name__ == "__main__":
    unittest.main()

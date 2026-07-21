from __future__ import annotations

import math
import os
import sys
import unittest
from dataclasses import replace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.metro import Metro
from entity.path import Path
from geometry.point import Point
from mediator import Mediator
from rendering.interpolation import MetroInterpolator, interpolate_heading
from rendering.layout import build_visual_path, project_metro_pose
from test.gm06c_consist_test_support import (
    assert_position,
    layout,
    place_on_segment,
    sample_carriages,
    spacing,
)
from test.gm06c_simulation_ui_support import (
    make_two_station_game,
    require_attribute,
)


def _attached_game(testcase: unittest.TestCase, seed: int):
    mediator, start, end, path, metro = make_two_station_game(seed=seed)
    attach = require_attribute(testcase, mediator, "attach_carriage")
    testcase.assertTrue(attach(path))
    testcase.assertTrue(attach(path))
    testcase.assertEqual(len(metro.carriages), 2)
    return mediator, start, end, path, metro


def _normalize_heading(value: float) -> float:
    result = (value + 180.0) % 360.0 - 180.0
    return 180.0 if math.isclose(result, -180.0) else result


_REPLACEMENT_POSITIONS = (
    (100, 100),
    (300, 100),
    (300, 300),
    (20, 220),
    (500, 200),
)


def _replacement_game(testcase: unittest.TestCase, seed: int):
    mediator = Mediator(seed=seed)
    stations = list(mediator.all_stations[: len(_REPLACEMENT_POSITIONS)])
    for station, (left, top) in zip(stations, _REPLACEMENT_POSITIONS):
        station.position = Point(left, top)
        station.shape.position = station.position
    mediator.stations = stations
    mediator.unlocked_num_stations = len(stations)

    color = next(iter(mediator.path_colors))
    path = Path(color)
    path.path_order = 1
    for station in stations[:3]:
        path.add_station(station)
    metro = Metro()
    path.add_metro(metro)
    mediator.paths = [path]
    mediator.metros = [metro]
    mediator.path_colors[color] = True
    mediator.path_to_color[path] = color
    button = mediator.path_buttons[0]
    button.assign_path(path)
    mediator.path_to_button[path] = button

    attach = require_attribute(testcase, mediator, "attach_carriage")
    testcase.assertTrue(attach(path))
    testcase.assertTrue(attach(path))
    testcase.assertEqual(len(metro.carriages), 2)
    return mediator, path, metro


class TestGM06cNoncollapsingTurnaround(unittest.TestCase):
    def test_live_terminal_arrival_uses_turnaround_instead_of_linear_collapse(
        self,
    ) -> None:
        mediator, start, end, path, metro = _attached_game(self, 6378)
        start.position = Point(100, 100)
        start.shape.position = start.position
        end.position = Point(300, 100)
        end.shape.position = end.position
        path.rebuild_geometry()
        metro.current_segment_idx = 0
        metro.current_segment = path.segments[0]
        metro.current_station = None
        metro.position = Point(299, 100)
        metro.is_forward = True
        metro.speed = metro.max_speed
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        gap = spacing(self)
        previous_head = project_metro_pose(path, metro, visual)
        previous = layout(self, visual, previous_head, 2, gap)
        interpolator = MetroInterpolator()
        interpolator.before_step(mediator)

        path.move_metro(metro, 16, should_stop_at_next_station=False)
        self.assertIs(metro.current_station, end)
        self.assertFalse(metro.is_forward)
        current_head = project_metro_pose(path, metro, visual)
        current = layout(self, visual, current_head, 2, gap)
        interpolator.after_step(mediator)

        self.assertEqual(
            sample_carriages(self, interpolator, path, metro, visual, 0.0),
            previous,
        )
        self.assertEqual(
            sample_carriages(self, interpolator, path, metro, visual, 1.0),
            current,
        )
        for alpha in (0.25, 0.5, 0.75):
            with self.subTest(alpha=alpha):
                head = interpolator.pose_for(path, metro, visual, alpha)
                actual = sample_carriages(
                    self,
                    interpolator,
                    path,
                    metro,
                    visual,
                    alpha,
                )
                self.assertEqual(
                    sample_carriages(
                        self,
                        interpolator,
                        path,
                        metro,
                        visual,
                        alpha,
                    ),
                    actual,
                )
                for ordinal, carriage_pose in enumerate(actual, start=1):
                    self.assertAlmostEqual(
                        math.dist(head.position, carriage_pose.position),
                        gap * ordinal,
                        places=5,
                    )
                self.assertAlmostEqual(
                    math.dist(actual[0].position, actual[1].position),
                    gap,
                    places=5,
                )

    def test_bent_short_terminal_turnaround_is_continuous_at_both_endpoints(
        self,
    ) -> None:
        mediator, path, metro = _replacement_game(self, 6379)
        path.path_order = 0
        terminal = path.stations[2]
        terminal.position = Point(300, 120)
        terminal.shape.position = terminal.position
        path.rebuild_geometry()
        metro.current_segment_idx = len(path.segments) - 1
        metro.current_segment = path.segments[metro.current_segment_idx]
        metro.current_station = None
        metro.position = Point(300, 119)
        metro.is_forward = True
        metro.speed = metro.max_speed
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        gap = spacing(self)
        previous_head = project_metro_pose(path, metro, visual)
        previous = layout(self, visual, previous_head, 2, gap)
        interpolator = MetroInterpolator()
        interpolator.before_step(mediator)

        path.move_metro(metro, 16, should_stop_at_next_station=False)
        self.assertIs(metro.current_station, terminal)
        self.assertFalse(metro.is_forward)
        current_head = project_metro_pose(path, metro, visual)
        current = layout(self, visual, current_head, 2, gap)
        interpolator.after_step(mediator)

        epsilon = 1e-6
        at_start = sample_carriages(
            self,
            interpolator,
            path,
            metro,
            visual,
            0.0,
        )
        near_start = sample_carriages(
            self,
            interpolator,
            path,
            metro,
            visual,
            epsilon,
        )
        near_end = sample_carriages(
            self,
            interpolator,
            path,
            metro,
            visual,
            1.0 - epsilon,
        )
        at_end = sample_carriages(
            self,
            interpolator,
            path,
            metro,
            visual,
            1.0,
        )
        self.assertEqual(at_start, previous)
        self.assertEqual(at_end, current)
        for ordinal in range(2):
            self.assertLess(
                math.dist(near_start[ordinal].position, at_start[ordinal].position),
                0.01,
            )
            self.assertLess(
                math.dist(near_end[ordinal].position, at_end[ordinal].position),
                0.01,
            )

        for alpha in (0.25, 0.5, 0.75):
            with self.subTest(alpha=alpha):
                head = interpolator.pose_for(path, metro, visual, alpha)
                actual = sample_carriages(
                    self,
                    interpolator,
                    path,
                    metro,
                    visual,
                    alpha,
                )
                radii = tuple(
                    math.dist(head.position, carriage_pose.position)
                    for carriage_pose in actual
                )
                self.assertGreater(radii[0], gap * 0.8)
                self.assertGreater(radii[1], radii[0])
                self.assertGreater(
                    math.dist(actual[0].position, actual[1].position),
                    gap * 0.8,
                )

    def test_both_terminals_follow_one_common_signed_half_circle(self) -> None:
        for terminal_name in ("start", "end"):
            with self.subTest(terminal=terminal_name):
                mediator, start, end, path, metro = _attached_game(
                    self,
                    6380 if terminal_name == "start" else 6381,
                )
                terminal = start if terminal_name == "start" else end
                before_forward = terminal_name == "end"
                after_forward = not before_forward
                metro.current_segment_idx = 0
                metro.current_segment = path.segments[0]
                metro.current_station = terminal
                metro.position = terminal.position
                metro.is_forward = before_forward
                visual = build_visual_path(path, 0.0, config.path_order_shift)
                gap = spacing(self)
                previous_head = project_metro_pose(path, metro, visual)
                previous = layout(self, visual, previous_head, 2, gap)
                interpolator = MetroInterpolator()
                interpolator.before_step(mediator)

                metro.is_forward = after_forward
                current_head = project_metro_pose(path, metro, visual)
                current = layout(self, visual, current_head, 2, gap)
                interpolator.after_step(mediator)

                self.assertEqual(
                    sample_carriages(self, interpolator, path, metro, visual, 0.0),
                    previous,
                )
                self.assertEqual(
                    sample_carriages(self, interpolator, path, metro, visual, 1.0),
                    current,
                )

                first_start = (
                    previous[0].position[0] - previous_head.position[0],
                    previous[0].position[1] - previous_head.position[1],
                )
                heading_delta = (
                    current_head.heading_degrees - previous_head.heading_degrees + 180.0
                ) % 360.0 - 180.0
                self.assertAlmostEqual(heading_delta, -180.0, places=6)
                signed_direction = -1.0 if heading_delta < 0.0 else 1.0
                start_angle = math.atan2(first_start[1], first_start[0])

                for alpha in (0.25, 0.5, 0.75):
                    with self.subTest(terminal=terminal_name, alpha=alpha):
                        head = interpolator.pose_for(path, metro, visual, alpha)
                        actual = sample_carriages(
                            self,
                            interpolator,
                            path,
                            metro,
                            visual,
                            alpha,
                        )
                        repeated = sample_carriages(
                            self,
                            interpolator,
                            path,
                            metro,
                            visual,
                            alpha,
                        )
                        self.assertEqual(repeated, actual)
                        assert_position(self, head.position, previous_head.position)
                        angle = start_angle + signed_direction * math.pi * alpha
                        for ordinal, carriage_pose in enumerate(actual, start=1):
                            radius = gap * ordinal
                            expected_position = (
                                head.position[0] + radius * math.cos(angle),
                                head.position[1] + radius * math.sin(angle),
                            )
                            assert_position(
                                self,
                                carriage_pose.position,
                                expected_position,
                            )
                            expected_heading = interpolate_heading(
                                previous_head.heading_degrees,
                                current_head.heading_degrees,
                                alpha,
                            )
                            self.assertAlmostEqual(
                                _normalize_heading(carriage_pose.heading_degrees),
                                expected_heading,
                                places=6,
                            )
                        self.assertAlmostEqual(
                            math.dist(actual[0].position, actual[1].position),
                            gap,
                            places=5,
                        )


class TestGM06cRetainedGeometryRebase(unittest.TestCase):
    def test_retained_path_edge_and_padding_replacements_rebase_both_endpoints(
        self,
    ) -> None:
        cases = (
            ("path edge", "path", 0, 0.5, 0.8, [3, 0, 1, 2]),
            ("padding", "padding", 1, 0.25, 0.75, [3, 0, 1, 2, 4]),
        )
        for label, kind, segment_index, before, after, replacement in cases:
            with self.subTest(case=label):
                mediator, path, metro = _replacement_game(
                    self,
                    6382 + segment_index,
                )
                interpolator = MetroInterpolator()
                old_visual = build_visual_path(
                    path,
                    float(path.path_order),
                    config.path_order_shift,
                )
                self.assertEqual(old_visual.segments[segment_index].kind, kind)
                self.assertGreater(
                    math.dist(
                        old_visual.segments[segment_index].start,
                        old_visual.segments[segment_index].end,
                    ),
                    0.0,
                )
                place_on_segment(metro, path, segment_index, before)
                previous_head = project_metro_pose(path, metro, old_visual)
                interpolator.before_step(mediator)
                place_on_segment(metro, path, segment_index, after)
                current_head = project_metro_pose(path, metro, old_visual)
                interpolator.after_step(mediator)
                self.assertNotEqual(
                    previous_head.position,
                    current_head.position,
                )

                self.assertTrue(mediator.replace_path(path, replacement))
                new_index = metro.current_segment_idx
                visual = build_visual_path(
                    path,
                    float(path.path_order),
                    config.path_order_shift,
                )
                gap = spacing(self)
                previous = layout(
                    self,
                    visual,
                    replace(previous_head, logical_segment_index=new_index),
                    2,
                    gap,
                )
                current = layout(
                    self,
                    visual,
                    replace(current_head, logical_segment_index=new_index),
                    2,
                    gap,
                )
                self.assertNotEqual(previous, current)

                for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
                    with self.subTest(case=label, alpha=alpha):
                        actual = sample_carriages(
                            self,
                            interpolator,
                            path,
                            metro,
                            visual,
                            alpha,
                        )
                        for ordinal, carriage_pose in enumerate(actual):
                            expected = tuple(
                                previous[ordinal].position[axis]
                                + (
                                    current[ordinal].position[axis]
                                    - previous[ordinal].position[axis]
                                )
                                * alpha
                                for axis in (0, 1)
                            )
                            assert_position(self, carriage_pose.position, expected)
                            self.assertAlmostEqual(
                                carriage_pose.heading_degrees,
                                interpolate_heading(
                                    previous[ordinal].heading_degrees,
                                    current[ordinal].heading_degrees,
                                    alpha,
                                ),
                                places=6,
                            )
                        if 0.0 < alpha < 1.0:
                            self.assertNotEqual(actual, current)


if __name__ == "__main__":
    unittest.main()

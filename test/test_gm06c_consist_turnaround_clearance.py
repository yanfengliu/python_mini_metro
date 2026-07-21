from __future__ import annotations

import itertools
import math
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.metro import Metro
from entity.path import Path
from geometry.point import Point
from mediator import Mediator
from rendering.interpolation import MetroInterpolator
from rendering.layout import build_visual_path, project_metro_pose
from test.gm06c_consist_test_support import layout, sample_carriages, spacing
from test.gm06c_simulation_ui_support import require_attribute

_STATIONS = (
    (0.0, 0.0),
    (31.0325060113, -53.0194772380),
    (127.5691364783, -192.8278895760),
    (109.2281526816, -362.5157476343),
    (3.7199998572, -428.7770015613),
    (11.4794746725, -288.3534965594),
)

_NONADJACENT_STATIONS = (
    (500.0, 500.0),
    (406.5738095533, 691.3476971976),
    (285.2290314729, 516.5135643267),
    (224.4896881055, 655.6163766671),
    (414.7156770420, 648.7805345774),
)

_CAP_EXHAUSTION_STATIONS = (
    (500.0, 500.0),
    (466.4667517962, 569.0754106502),
    (582.0574061593, 412.1308489666),
    (476.3120739002, 348.3815853450),
    (306.0572696537, 349.3657210539),
    (434.7111812345, 364.7646398545),
    (326.0569113331, 354.6189381007),
    (229.2836488460, 250.1143250500),
)


def _clearances(previous, current):
    pairs = tuple(itertools.combinations(range(len(previous)), 2))
    return pairs, {
        pair: min(
            float(config.carriage_body_length),
            math.dist(previous[pair[0]], previous[pair[1]]),
            math.dist(current[pair[0]], current[pair[1]]),
        )
        for pair in pairs
    }


def _consist_game(
    testcase: unittest.TestCase,
    positions: tuple[tuple[float, float], ...],
    seed: int,
    carriage_count: int,
):
    mediator = Mediator(seed=seed)
    stations = list(mediator.all_stations[: len(positions)])
    testcase.assertEqual(len(stations), len(positions))
    for station, position in zip(stations, positions):
        station.position = Point(*position)
        station.shape.position = station.position
    mediator.stations = stations
    mediator.unlocked_num_stations = len(stations)

    color = next(iter(mediator.path_colors))
    path = Path(color)
    for station in stations:
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
    mediator.num_carriages = carriage_count
    attach = require_attribute(testcase, mediator, "attach_carriage")
    for _ in range(carriage_count):
        testcase.assertTrue(attach(path))
    testcase.assertEqual(len(metro.carriages), carriage_count)
    return mediator, stations, path, metro


def _place_before_terminal(path, metro, *, at_start: bool) -> None:
    index = 0 if at_start else len(path.segments) - 1
    segment = path.segments[index]
    dx = segment.segment_end.left - segment.segment_start.left
    dy = segment.segment_end.top - segment.segment_start.top
    length = math.hypot(dx, dy)
    unit = (dx / length, dy / length)
    target = segment.segment_start if at_start else segment.segment_end
    direction = 1.0 if at_start else -1.0
    metro.current_segment_idx = index
    metro.current_segment = segment
    metro.current_station = None
    metro.position = Point(
        target.left + direction * unit[0] * 0.1,
        target.top + direction * unit[1] * 0.1,
    )
    metro.is_forward = not at_start
    metro.speed = metro.max_speed


class TestGM06cTurnaroundBodyClearance(unittest.TestCase):
    def test_seven_body_arrival_converges_at_projection_boundary(self) -> None:
        mediator, stations, path, metro = _consist_game(
            self,
            _CAP_EXHAUSTION_STATIONS,
            6395,
            7,
        )
        _place_before_terminal(path, metro, at_start=False)
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        gap = spacing(self)
        previous_head = project_metro_pose(path, metro, visual)
        previous = layout(self, visual, previous_head, 7, gap)
        interpolator = MetroInterpolator()
        interpolator.before_step(mediator)

        path.move_metro(metro, 16, should_stop_at_next_station=False)
        self.assertIs(metro.current_station, stations[-1])
        self.assertFalse(metro.is_forward)
        current_head = project_metro_pose(path, metro, visual)
        current = layout(self, visual, current_head, 7, gap)
        interpolator.after_step(mediator)
        pairs, clearances = _clearances(
            tuple(body.position for body in previous),
            tuple(body.position for body in current),
        )

        samples = tuple(
            sample_carriages(
                self,
                interpolator,
                path,
                metro,
                visual,
                0.109 + step * 0.0001,
            )
            for step in range(21)
        )
        for bodies in samples:
            self.assertTrue(
                all(math.isfinite(value) for body in bodies for value in body.position)
            )
            for pair in pairs:
                self.assertGreaterEqual(
                    math.dist(
                        bodies[pair[0]].position,
                        bodies[pair[1]].position,
                    ),
                    clearances[pair] - 1e-6,
                )
        for before, after in zip(samples, samples[1:]):
            for prior_body, body in zip(before, after):
                self.assertLess(
                    math.dist(prior_body.position, body.position),
                    0.1,
                )

    def test_four_body_bent_arrival_preserves_all_pair_clearances(self) -> None:
        for label, positions, at_start in (
            ("end", _STATIONS, False),
            ("start", tuple(reversed(_STATIONS)), True),
        ):
            with self.subTest(terminal=label):
                mediator, stations, path, metro = _consist_game(
                    self,
                    positions,
                    6391 if at_start else 6392,
                    4,
                )
                _place_before_terminal(path, metro, at_start=at_start)
                visual = build_visual_path(path, 0.0, config.path_order_shift)
                gap = spacing(self)
                previous_head = project_metro_pose(path, metro, visual)
                previous = layout(self, visual, previous_head, 4, gap)
                interpolator = MetroInterpolator()
                interpolator.before_step(mediator)

                path.move_metro(metro, 16, should_stop_at_next_station=False)
                terminal = stations[0] if at_start else stations[-1]
                self.assertIs(metro.current_station, terminal)
                self.assertEqual(metro.is_forward, at_start)
                current_head = project_metro_pose(path, metro, visual)
                current = layout(self, visual, current_head, 4, gap)
                interpolator.after_step(mediator)

                self.assertEqual(
                    sample_carriages(self, interpolator, path, metro, visual, 0.0),
                    previous,
                )
                self.assertEqual(
                    sample_carriages(self, interpolator, path, metro, visual, 1.0),
                    current,
                )
                pairs, clearances = _clearances(
                    tuple(body.position for body in previous),
                    tuple(body.position for body in current),
                )
                for index in range(3):
                    self.assertAlmostEqual(
                        clearances[(index, index + 1)],
                        float(config.carriage_body_length),
                        places=6,
                    )

                for alpha, endpoint in ((1e-6, previous), (1.0 - 1e-6, current)):
                    actual = sample_carriages(
                        self,
                        interpolator,
                        path,
                        metro,
                        visual,
                        alpha,
                    )
                    for body, expected in zip(actual, endpoint):
                        self.assertLess(
                            math.dist(body.position, expected.position),
                            0.01,
                        )

                cached_previous = dict(interpolator._previous)
                cached_current = dict(interpolator._current)
                prior_positions = tuple(body.position for body in previous)
                for step in range(1, 2000):
                    alpha = step / 2000.0
                    bodies = sample_carriages(
                        self,
                        interpolator,
                        path,
                        metro,
                        visual,
                        alpha,
                    )
                    self.assertTrue(
                        all(
                            math.isfinite(value)
                            for body in bodies
                            for value in body.position
                        )
                    )
                    for body, prior_position in zip(bodies, prior_positions):
                        self.assertLess(
                            math.dist(body.position, prior_position),
                            2.0,
                        )
                    for pair in pairs:
                        self.assertGreaterEqual(
                            math.dist(
                                bodies[pair[0]].position,
                                bodies[pair[1]].position,
                            ),
                            clearances[pair] - 1e-6,
                        )
                    prior_positions = tuple(body.position for body in bodies)
                for prior_position, body in zip(prior_positions, current):
                    self.assertLess(math.dist(prior_position, body.position), 2.0)
                self.assertEqual(interpolator._previous, cached_previous)
                self.assertEqual(interpolator._current, cached_current)

    def test_six_body_turnaround_preserves_nonadjacent_clearance(self) -> None:
        for label, positions, at_start in (
            ("end", _NONADJACENT_STATIONS, False),
            ("start", tuple(reversed(_NONADJACENT_STATIONS)), True),
        ):
            with self.subTest(terminal=label):
                mediator, stations, path, metro = _consist_game(
                    self,
                    positions,
                    6393 if at_start else 6394,
                    6,
                )
                _place_before_terminal(path, metro, at_start=at_start)
                visual = build_visual_path(path, 0.0, config.path_order_shift)
                gap = spacing(self)
                previous_head = project_metro_pose(path, metro, visual)
                previous = layout(self, visual, previous_head, 6, gap)
                interpolator = MetroInterpolator()
                interpolator.before_step(mediator)

                path.move_metro(metro, 16, should_stop_at_next_station=False)
                terminal = stations[0] if at_start else stations[-1]
                self.assertIs(metro.current_station, terminal)
                self.assertEqual(metro.is_forward, at_start)
                current_head = project_metro_pose(path, metro, visual)
                current = layout(self, visual, current_head, 6, gap)
                interpolator.after_step(mediator)

                self.assertEqual(
                    sample_carriages(self, interpolator, path, metro, visual, 0.0),
                    previous,
                )
                self.assertEqual(
                    sample_carriages(self, interpolator, path, metro, visual, 1.0),
                    current,
                )
                pairs, clearances = _clearances(
                    tuple(body.position for body in previous),
                    tuple(body.position for body in current),
                )
                reported_pair = (3, 5)
                self.assertEqual(clearances[reported_pair], 60.0)
                self.assertAlmostEqual(
                    math.dist(
                        previous[reported_pair[0]].position,
                        previous[reported_pair[1]].position,
                    ),
                    69.6516,
                    places=3,
                )
                self.assertAlmostEqual(
                    math.dist(
                        current[reported_pair[0]].position,
                        current[reported_pair[1]].position,
                    ),
                    140.0,
                    places=3,
                )
                reported_sample = sample_carriages(
                    self,
                    interpolator,
                    path,
                    metro,
                    visual,
                    0.31,
                )
                self.assertGreaterEqual(
                    math.dist(
                        reported_sample[reported_pair[0]].position,
                        reported_sample[reported_pair[1]].position,
                    ),
                    clearances[reported_pair] - 1e-6,
                )
                cached_previous = dict(interpolator._previous)
                cached_current = dict(interpolator._current)
                prior_positions = tuple(body.position for body in previous)

                for step in range(1, 2000):
                    alpha = step / 2000.0
                    bodies = sample_carriages(
                        self,
                        interpolator,
                        path,
                        metro,
                        visual,
                        alpha,
                    )
                    self.assertTrue(
                        all(
                            math.isfinite(value)
                            for body in bodies
                            for value in body.position
                        )
                    )
                    for body, prior_position in zip(bodies, prior_positions):
                        self.assertLess(math.dist(body.position, prior_position), 3.0)
                    for pair in pairs:
                        self.assertGreaterEqual(
                            math.dist(
                                bodies[pair[0]].position,
                                bodies[pair[1]].position,
                            ),
                            clearances[pair] - 1e-6,
                        )
                    prior_positions = tuple(body.position for body in bodies)

                for alpha, endpoint in ((1e-6, previous), (1.0 - 1e-6, current)):
                    bodies = sample_carriages(
                        self,
                        interpolator,
                        path,
                        metro,
                        visual,
                        alpha,
                    )
                    for body, expected in zip(bodies, endpoint):
                        self.assertLess(
                            math.dist(body.position, expected.position),
                            0.01,
                        )
                for prior_position, body in zip(prior_positions, current):
                    self.assertLess(math.dist(prior_position, body.position), 3.0)
                self.assertEqual(interpolator._previous, cached_previous)
                self.assertEqual(interpolator._current, cached_current)


if __name__ == "__main__":
    unittest.main()

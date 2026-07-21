from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from geometry.point import Point
from rendering.interpolation import MetroInterpolator
from rendering.layout import build_visual_path, project_metro_pose
from test.gm06c_consist_test_support import layout, sample_carriages, spacing
from test.test_gm06c_consist_turnaround_rebase import _replacement_game


class TestGM06cHairpinTurnaround(unittest.TestCase):
    def test_reversed_endpoint_radii_exchange_without_body_collapse(self) -> None:
        mediator, path, metro = _replacement_game(self, 6390)
        path.path_order = 0
        for station, position in zip(
            path.stations,
            ((400, 310), (200, 300), (300, 300)),
        ):
            station.position = Point(*position)
            station.shape.position = station.position
        path.rebuild_geometry()
        terminal = path.stations[-1]
        metro.current_segment_idx = len(path.segments) - 1
        metro.current_segment = path.segments[-1]
        metro.current_station = None
        metro.position = Point(299.9, 300)
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

        self.assertEqual(
            sample_carriages(self, interpolator, path, metro, visual, 0.0),
            previous,
        )
        self.assertEqual(
            sample_carriages(self, interpolator, path, metro, visual, 1.0),
            current,
        )
        for alpha, endpoint in ((1e-6, previous), (1.0 - 1e-6, current)):
            near_endpoint = sample_carriages(
                self,
                interpolator,
                path,
                metro,
                visual,
                alpha,
            )
            for actual, expected in zip(near_endpoint, endpoint):
                self.assertLess(
                    math.dist(actual.position, expected.position),
                    0.01,
                )
        start_radii = tuple(
            math.dist(previous_head.position, pose.position) for pose in previous
        )
        end_radii = tuple(
            math.dist(current_head.position, pose.position) for pose in current
        )
        self.assertLess(start_radii[1], start_radii[0])
        self.assertGreater(end_radii[1], end_radii[0])
        endpoint_clearance = min(
            math.dist(previous[0].position, previous[1].position),
            math.dist(current[0].position, current[1].position),
        )
        self.assertGreater(endpoint_clearance, 0.0)

        cached_previous = dict(interpolator._previous)
        cached_current = dict(interpolator._current)
        samples = []
        for step in range(1, 2000):
            alpha = step / 2000.0
            head = interpolator.pose_for(path, metro, visual, alpha)
            bodies = sample_carriages(
                self,
                interpolator,
                path,
                metro,
                visual,
                alpha,
            )
            values = (
                *head.position,
                *(value for pose in bodies for value in pose.position),
            )
            self.assertTrue(all(math.isfinite(value) for value in values))
            body_distance = math.dist(bodies[0].position, bodies[1].position)
            self.assertGreaterEqual(body_distance, endpoint_clearance - 1e-6)
            radius_delta = math.dist(
                head.position,
                bodies[1].position,
            ) - math.dist(head.position, bodies[0].position)
            samples.append((abs(radius_delta), body_distance))

        crossover_delta, crossover_distance = min(samples)
        self.assertLess(crossover_delta, 0.1)
        self.assertGreaterEqual(crossover_distance, endpoint_clearance - 1e-6)
        self.assertEqual(interpolator._previous, cached_previous)
        self.assertEqual(interpolator._current, cached_current)


if __name__ == "__main__":
    unittest.main()

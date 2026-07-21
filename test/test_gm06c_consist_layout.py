from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from rendering.interpolation import MetroInterpolator, interpolate_heading
from rendering.layout import build_visual_path, project_metro_pose
from test.gm06c_consist_test_support import (
    assert_position as _assert_position,
)
from test.gm06c_consist_test_support import (
    layout as _layout,
)
from test.gm06c_consist_test_support import (
    place_on_segment as _place_on_segment,
)
from test.gm06c_consist_test_support import (
    pose as _pose,
)
from test.gm06c_consist_test_support import (
    sample_carriages as _sample_carriages,
)
from test.gm06c_consist_test_support import (
    segment as _segment,
)
from test.gm06c_consist_test_support import (
    spacing as _spacing,
)
from test.gm06c_consist_test_support import (
    visual_path as _path,
)
from test.gm06c_simulation_ui_support import (
    make_two_station_game,
    require_attribute,
)


class TestGM06cPureConsistLayout(unittest.TestCase):
    def test_straight_forward_and_reverse_order(self) -> None:
        visual = _path(_segment(0, (0.0, 0.0), (200.0, 0.0)))

        forward = _layout(
            self,
            visual,
            _pose((150.0, 0.0), 0.0, 0, 0.75),
            2,
            60.0,
        )
        reverse = _layout(
            self,
            visual,
            _pose((50.0, 0.0), 180.0, 0, 0.25, forward=False),
            2,
            60.0,
        )

        self.assertEqual(
            tuple(pose.position for pose in forward),
            ((90.0, 0.0), (30.0, 0.0)),
        )
        self.assertEqual(
            tuple(pose.position for pose in reverse),
            ((110.0, 0.0), (170.0, 0.0)),
        )
        self.assertEqual(
            tuple(pose.heading_degrees for pose in reverse),
            (180.0, 180.0),
        )

    def test_forward_and_reverse_walk_across_path_padding_bends(self) -> None:
        visual = _path(
            _segment(0, (0.0, 0.0), (100.0, 0.0)),
            _segment(1, (100.0, 0.0), (100.0, 20.0), kind="padding"),
            _segment(2, (100.0, 20.0), (100.0, 120.0)),
        )

        forward = _layout(
            self,
            visual,
            _pose((100.0, 80.0), 90.0, 2, 0.6),
            2,
            60.0,
        )
        reverse = _layout(
            self,
            visual,
            _pose((40.0, 0.0), 180.0, 0, 0.4, forward=False),
            2,
            60.0,
        )

        self.assertEqual(
            tuple(pose.position for pose in forward),
            ((100.0, 20.0), (60.0, 0.0)),
        )
        self.assertEqual(
            tuple(pose.position for pose in reverse),
            ((100.0, 0.0), (100.0, 60.0)),
        )
        self.assertEqual(forward[0].logical_segment_index, 1)
        self.assertEqual(forward[1].logical_segment_index, 0)
        self.assertEqual(reverse[1].logical_segment_index, 2)

    def test_short_loop_wraps_repeatedly_for_each_ordinal_spacing(self) -> None:
        visual = _path(
            _segment(0, (0.0, 0.0), (100.0, 0.0)),
            _segment(1, (100.0, 0.0), (100.0, 100.0)),
            _segment(2, (100.0, 100.0), (0.0, 100.0)),
            _segment(3, (0.0, 100.0), (0.0, 0.0)),
            looped=True,
        )

        carriages = _layout(
            self,
            visual,
            _pose((10.0, 0.0), 0.0, 0, 0.1),
            2,
            450.0,
        )

        _assert_position(self, carriages[0].position, (0.0, 40.0))
        _assert_position(self, carriages[1].position, (0.0, 90.0))
        self.assertEqual(
            tuple(pose.logical_segment_index for pose in carriages),
            (3, 3),
        )
        self.assertEqual(
            tuple(pose.heading_degrees for pose in carriages),
            (-90.0, -90.0),
        )

    def test_nonloop_extrapolates_from_both_reached_terminal_tangents(self) -> None:
        visual = _path(_segment(0, (0.0, 0.0), (1000.0, 0.0)))

        near_start = _layout(
            self,
            visual,
            _pose((10.0, 0.0), 0.0, 0, 0.01),
            2,
            60.0,
        )
        near_end_reverse = _layout(
            self,
            visual,
            _pose((990.0, 0.0), 180.0, 0, 0.99, forward=False),
            2,
            60.0,
        )

        self.assertEqual(
            tuple(pose.position for pose in near_start),
            ((-50.0, 0.0), (-110.0, 0.0)),
        )
        self.assertEqual(
            tuple(pose.position for pose in near_end_reverse),
            ((1050.0, 0.0), (1110.0, 0.0)),
        )
        self.assertTrue(
            all(math.isfinite(value) for pose in near_start for value in pose.position)
        )

    def test_degenerate_geometry_uses_finite_heading_fallback(self) -> None:
        visual = _path(
            _segment(0, (5.0, 5.0), (5.0, 5.0)),
            _segment(1, (5.0, 5.0), (5.0, 5.0), kind="padding"),
        )

        first = _layout(
            self,
            visual,
            _pose((10.0, 20.0), 90.0, 0, 0.0),
            2,
            60.0,
        )
        second = _layout(
            self,
            visual,
            _pose((10.0, 20.0), 90.0, 0, 0.0),
            2,
            60.0,
        )

        _assert_position(self, first[0].position, (10.0, -40.0))
        _assert_position(self, first[1].position, (10.0, -100.0))
        self.assertEqual(first, second)
        self.assertTrue(
            all(math.isfinite(value) for pose in first for value in pose.position)
        )

    def test_zero_count_is_empty_and_inputs_remain_unchanged(self) -> None:
        visual = _path(_segment(0, (0.0, 0.0), (100.0, 0.0)))
        head = _pose((50.0, 0.0), 0.0, 0, 0.5)

        self.assertEqual(_layout(self, visual, head, 0, 60.0), ())
        self.assertEqual(visual.segments[0].start, (0.0, 0.0))
        self.assertEqual(head.position, (50.0, 0.0))


class TestGM06cConsistInterpolation(unittest.TestCase):
    def _attached_game(self, seed: int):
        mediator, start, end, path, metro = make_two_station_game(seed=seed)
        attach = require_attribute(self, mediator, "attach_carriage")
        self.assertTrue(attach(path))
        self.assertTrue(attach(path))
        self.assertEqual(len(require_attribute(self, metro, "carriages")), 2)
        return mediator, start, end, path, metro

    def _three_station_game(self, seed: int):
        mediator, start, middle, path, metro = self._attached_game(seed)
        middle.position = Point(500, 200)
        middle.shape.position = middle.position
        third = Station(
            Circle(config.station_color, config.station_size),
            Point(500, 600),
        )
        mediator.stations.append(third)
        mediator.all_stations.append(third)
        path.add_station(third)
        metro.current_segment_idx = 0
        metro.current_segment = path.segments[0]
        return mediator, start, middle, third, path, metro

    def test_endpoint_samples_equal_coherent_layouts_not_interpolated_logical_fields(
        self,
    ) -> None:
        mediator, _start, _end, path, metro = self._attached_game(6330)
        interpolator = MetroInterpolator()
        segment = path.segments[0]
        metro.current_station = None
        metro.position = Point(
            segment.segment_start.left
            + 0.35 * (segment.segment_end.left - segment.segment_start.left),
            segment.segment_start.top
            + 0.35 * (segment.segment_end.top - segment.segment_start.top),
        )
        interpolator.before_step(mediator)
        metro.position = Point(
            segment.segment_start.left
            + 0.70 * (segment.segment_end.left - segment.segment_start.left),
            segment.segment_start.top
            + 0.70 * (segment.segment_end.top - segment.segment_start.top),
        )
        interpolator.after_step(mediator)
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        spacing = _spacing(self)

        for alpha in (0.0, 1.0):
            with self.subTest(alpha=alpha):
                head = interpolator.pose_for(path, metro, visual, alpha)
                expected = _layout(self, visual, head, 2, spacing)
                actual = _sample_carriages(
                    self,
                    interpolator,
                    path,
                    metro,
                    visual,
                    alpha,
                )
                self.assertEqual(actual, expected)

    def test_same_terminal_direction_flip_uses_noncollapsing_common_pivot(self) -> None:
        mediator, start, _end, path, metro = self._attached_game(6331)
        interpolator = MetroInterpolator()
        metro.current_station = start
        metro.position = start.position
        metro.is_forward = False
        interpolator.before_step(mediator)
        metro.is_forward = True
        interpolator.after_step(mediator)
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        spacing = _spacing(self)

        head = interpolator.pose_for(path, metro, visual, 0.5)
        carriages = _sample_carriages(
            self,
            interpolator,
            path,
            metro,
            visual,
            0.5,
        )

        radii = [
            math.hypot(
                pose.position[0] - head.position[0],
                pose.position[1] - head.position[1],
            )
            for pose in carriages
        ]
        self.assertAlmostEqual(radii[0], spacing, places=5)
        self.assertAlmostEqual(radii[1], 2 * spacing, places=5)
        self.assertAlmostEqual(
            math.dist(carriages[0].position, carriages[1].position),
            spacing,
            places=5,
        )
        self.assertNotEqual(carriages[0].position, head.position)
        self.assertNotEqual(carriages[1].position, head.position)

    def test_path_padding_transitions_interpolate_coherent_endpoint_consists(
        self,
    ) -> None:
        mediator, _start, _middle, _third, path, metro = self._three_station_game(6332)
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        spacing = _spacing(self)

        for before_index, before_progress, after_index, after_progress in (
            (0, 0.9, 1, 0.4),
            (1, 0.6, 2, 0.1),
        ):
            with self.subTest(
                before=before_index,
                after=after_index,
            ):
                interpolator = MetroInterpolator()
                _place_on_segment(metro, path, before_index, before_progress)
                previous_head = project_metro_pose(path, metro, visual)
                previous = _layout(self, visual, previous_head, 2, spacing)
                interpolator.before_step(mediator)
                _place_on_segment(metro, path, after_index, after_progress)
                current_head = project_metro_pose(path, metro, visual)
                current = _layout(self, visual, current_head, 2, spacing)
                interpolator.after_step(mediator)

                for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
                    with self.subTest(alpha=alpha):
                        actual = _sample_carriages(
                            self,
                            interpolator,
                            path,
                            metro,
                            visual,
                            alpha,
                        )
                        for ordinal, pose in enumerate(actual):
                            expected_position = tuple(
                                previous[ordinal].position[axis]
                                + (
                                    current[ordinal].position[axis]
                                    - previous[ordinal].position[axis]
                                )
                                * alpha
                                for axis in (0, 1)
                            )
                            _assert_position(self, pose.position, expected_position)
                            self.assertAlmostEqual(
                                pose.heading_degrees,
                                interpolate_heading(
                                    previous[ordinal].heading_degrees,
                                    current[ordinal].heading_degrees,
                                    alpha,
                                ),
                                places=6,
                            )

    def test_retained_edge_replacement_rebases_and_sampling_is_pure(
        self,
    ) -> None:
        mediator, _start, _end, path, metro = self._attached_game(6333)
        interpolator = MetroInterpolator()
        metro.current_station = None
        segment = path.segments[0]
        metro.position = Point(
            (segment.segment_start.left + segment.segment_end.left) / 2,
            (segment.segment_start.top + segment.segment_end.top) / 2,
        )
        interpolator.before_step(mediator)
        interpolator.after_step(mediator)
        previous_object = interpolator._previous
        current_object = interpolator._current
        previous_items = tuple(interpolator._previous.items())
        current_items = tuple(interpolator._current.items())

        path.rebuild_geometry()
        metro.current_segment = path.segments[metro.current_segment_idx]
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        live_head = project_metro_pose(path, metro, visual)
        expected = _layout(self, visual, live_head, 2, _spacing(self))

        first = _sample_carriages(self, interpolator, path, metro, visual, 0.4)
        second = _sample_carriages(self, interpolator, path, metro, visual, 0.4)

        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        self.assertIs(interpolator._previous, previous_object)
        self.assertIs(interpolator._current, current_object)
        self.assertEqual(tuple(interpolator._previous.items()), previous_items)
        self.assertEqual(tuple(interpolator._current.items()), current_items)

    def test_stale_topology_falls_back_to_one_live_coherent_consist(self) -> None:
        mediator, _start, end, path, metro = self._attached_game(6334)
        interpolator = MetroInterpolator()
        _place_on_segment(metro, path, 0, 0.4)
        interpolator.before_step(mediator)
        _place_on_segment(metro, path, 0, 0.6)
        interpolator.after_step(mediator)

        end.position = Point(end.position.left + 140, end.position.top + 80)
        end.shape.position = end.position
        path.rebuild_geometry()
        metro.current_segment = path.segments[metro.current_segment_idx]
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        live_head = project_metro_pose(path, metro, visual)
        expected = _layout(self, visual, live_head, 2, _spacing(self))

        for alpha in (0.0, 0.3, 0.7, 1.0):
            with self.subTest(alpha=alpha):
                self.assertEqual(
                    _sample_carriages(
                        self,
                        interpolator,
                        path,
                        metro,
                        visual,
                        alpha,
                    ),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()

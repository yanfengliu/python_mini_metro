from __future__ import annotations

import gc
import os
import sys
import unittest
import weakref
from dataclasses import replace
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import path_order_shift
from entity.metro import Metro
from entity.path import Path
from geometry.point import Point
from mediator import Mediator
from rendering.interpolation import MetroInterpolator
from rendering.layout import MetroPose, build_visual_path, project_metro_pose

_POSITIONS = (
    (100, 100),
    (300, 100),
    (300, 300),
    (20, 220),
    (500, 200),
)


def _build_network(route=(0, 1, 2), *, loop=False, path_order=0):
    mediator = Mediator(seed=505)
    stations = list(mediator.all_stations[: len(_POSITIONS)])
    for station, (left, top) in zip(stations, _POSITIONS):
        station.position = Point(left, top)
        station.shape.position = station.position
    mediator.stations = stations
    mediator.unlocked_num_stations = len(stations)

    color = next(iter(mediator.path_colors))
    path = Path(color)
    path.path_order = path_order
    for index in route:
        path.add_station(stations[index])
    if loop:
        path.set_loop()
    metro = Metro()
    path.add_metro(metro)

    mediator.paths = [path]
    mediator.metros = [metro]
    mediator.path_colors[color] = True
    mediator.path_to_color[path] = color
    button = mediator.path_buttons[0]
    button.assign_path(path)
    mediator.path_to_button[path] = button
    return mediator, stations, path, metro


def _layout(path):
    return build_visual_path(path, float(path.path_order), path_order_shift)


def _place(
    metro,
    path,
    segment_index: int,
    progress: float,
    *,
    is_forward: bool = True,
    current_station=None,
):
    segment = path.segments[segment_index]
    start = segment.segment_start
    end = segment.segment_end
    metro.current_segment_idx = segment_index
    metro.current_segment = segment
    metro.position = Point(
        start.left + (end.left - start.left) * progress,
        start.top + (end.top - start.top) * progress,
    )
    metro.is_forward = is_forward
    metro.current_station = current_station


def _live_pose(path, metro):
    return project_metro_pose(path, metro, _layout(path))


class TestGM05bRenderContinuity(unittest.TestCase):
    def test_reindexed_retained_edge_preserves_subtick_pose_at_every_alpha(self):
        mediator, _, path, metro = _build_network()
        interpolator = MetroInterpolator()
        _place(metro, path, 0, 0.2)
        interpolator.before_step(mediator)
        _place(metro, path, 0, 0.4)
        interpolator.after_step(mediator)
        alphas = (0.0, 0.5, 1.0)
        expected = {
            alpha: interpolator.pose_for(path, metro, _layout(path), alpha)
            for alpha in alphas
        }

        self.assertTrue(mediator.replace_path(path, [3, 0, 1, 2]))
        new_index = metro.current_segment_idx
        layout = _layout(path)

        for alpha in alphas:
            with self.subTest(alpha=alpha):
                self.assertEqual(
                    interpolator.pose_for(path, metro, layout, alpha),
                    replace(expected[alpha], logical_segment_index=new_index),
                )

    def test_interpolation_resumes_after_next_observed_step(self):
        mediator, _, path, metro = _build_network()
        interpolator = MetroInterpolator()
        _place(metro, path, 0, 0.2)
        interpolator.before_step(mediator)
        _place(metro, path, 0, 0.4)
        interpolator.after_step(mediator)
        self.assertTrue(mediator.replace_path(path, [3, 0, 1, 2]))
        interpolator.pose_for(path, metro, _layout(path), 0.5)

        _place(metro, path, metro.current_segment_idx, 0.4)
        interpolator.before_step(mediator)
        _place(metro, path, metro.current_segment_idx, 0.6)
        interpolator.after_step(mediator)

        self.assertEqual(
            interpolator.pose_for(path, metro, _layout(path), 0.5),
            MetroPose(
                position=(200.0, 100.0),
                heading_degrees=0.0,
                logical_segment_index=metro.current_segment_idx,
                progress=0.5,
                is_forward=True,
                is_stopped=False,
            ),
        )

    def test_reindexed_retained_padding_preserves_subtick_pose(self):
        mediator, _, path, metro = _build_network(path_order=1)
        interpolator = MetroInterpolator()
        _place(metro, path, 1, 0.25)
        interpolator.before_step(mediator)
        _place(metro, path, 1, 0.75)
        interpolator.after_step(mediator)
        alphas = (0.0, 0.5, 1.0)
        expected = {
            alpha: interpolator.pose_for(path, metro, _layout(path), alpha)
            for alpha in alphas
        }

        self.assertTrue(mediator.replace_path(path, [3, 0, 1, 2, 4]))
        new_index = metro.current_segment_idx

        for alpha in alphas:
            with self.subTest(alpha=alpha):
                self.assertEqual(
                    interpolator.pose_for(path, metro, _layout(path), alpha),
                    replace(expected[alpha], logical_segment_index=new_index),
                )

    def test_loop_closing_padding_key_survives_cycle_rotation(self):
        mediator, _, path, metro = _build_network(loop=True, path_order=1)
        closing_index = len(path.segments) - 1
        interpolator = MetroInterpolator()
        _place(metro, path, closing_index, 0.25)
        interpolator.before_step(mediator)
        _place(metro, path, closing_index, 0.75)
        interpolator.after_step(mediator)
        alphas = (0.0, 0.5, 1.0)
        expected = {
            alpha: interpolator.pose_for(path, metro, _layout(path), alpha)
            for alpha in alphas
        }

        self.assertTrue(mediator.replace_path(path, [1, 2, 0], loop=True))
        new_index = metro.current_segment_idx

        for alpha in alphas:
            with self.subTest(alpha=alpha):
                self.assertEqual(
                    interpolator.pose_for(path, metro, _layout(path), alpha),
                    replace(expected[alpha], logical_segment_index=new_index),
                )

    def test_normal_within_step_segment_transition_still_interpolates(self):
        mediator, stations, path, metro = _build_network()
        interpolator = MetroInterpolator()
        _place(metro, path, 0, 0.9)
        interpolator.before_step(mediator)
        _place(metro, path, 1, 0.0, current_station=stations[1])
        interpolator.after_step(mediator)

        self.assertEqual(
            interpolator.pose_for(path, metro, _layout(path), 0.5),
            MetroPose(
                position=(290.0, 100.0),
                heading_degrees=45.0,
                logical_segment_index=1,
                progress=0.45,
                is_forward=True,
                is_stopped=True,
            ),
        )

    def test_replacement_during_segment_transition_falls_back_to_live_pose(self):
        mediator, _, path, metro = _build_network(path_order=1)
        interpolator = MetroInterpolator()
        _place(metro, path, 0, 0.9)
        interpolator.before_step(mediator)
        _place(metro, path, 1, 0.5)
        interpolator.after_step(mediator)
        self.assertTrue(mediator.replace_path(path, [0, 1, 2, 4]))
        expected = _live_pose(path, metro)

        for alpha in (0.0, 0.5, 1.0):
            with self.subTest(alpha=alpha):
                self.assertEqual(
                    interpolator.pose_for(path, metro, _layout(path), alpha),
                    expected,
                )

    def test_missing_transition_context_falls_back_instead_of_rebasing(self):
        mediator, _, path, metro = _build_network()
        source_without_paths = SimpleNamespace(metros=mediator.metros)
        interpolator = MetroInterpolator()
        _place(metro, path, 0, 0.2)
        interpolator.before_step(source_without_paths)
        _place(metro, path, 0, 0.4)
        interpolator.after_step(source_without_paths)
        self.assertTrue(mediator.replace_path(path, [2, 1, 0]))
        expected = _live_pose(path, metro)

        for alpha in (0.0, 0.5, 1.0):
            with self.subTest(alpha=alpha):
                self.assertEqual(
                    interpolator.pose_for(path, metro, _layout(path), alpha),
                    expected,
                )

    def test_stopped_outgoing_padding_changes_fall_back_to_full_live_pose(self):
        cases = (
            ([3, 0, 1, 4], "rerouted padding"),
            ([3, 0, 1], "new terminus"),
        )
        for replacement, label in cases:
            with self.subTest(case=label):
                mediator, stations, path, metro = _build_network()
                _place(
                    metro,
                    path,
                    1,
                    0.0,
                    current_station=stations[1],
                )
                interpolator = MetroInterpolator()
                interpolator.before_step(mediator)
                interpolator.after_step(mediator)

                self.assertTrue(mediator.replace_path(path, replacement))
                expected = _live_pose(path, metro)
                for alpha in (0.0, 0.5, 1.0):
                    self.assertEqual(
                        interpolator.pose_for(path, metro, _layout(path), alpha),
                        expected,
                    )

    def test_two_station_turnaround_rebases_each_snapshot_direction(self):
        mediator, stations, path, metro = _build_network(route=(0, 1))
        interpolator = MetroInterpolator()
        _place(metro, path, 0, 0.9)
        interpolator.before_step(mediator)
        _place(
            metro,
            path,
            0,
            1.0,
            is_forward=False,
            current_station=stations[1],
        )
        interpolator.after_step(mediator)

        self.assertTrue(mediator.replace_path(path, [1, 0]))

        self.assertEqual(
            interpolator.pose_for(path, metro, _layout(path), 0.5),
            MetroPose(
                position=(290.0, 100.0),
                heading_degrees=-90.0,
                logical_segment_index=0,
                progress=0.05,
                is_forward=True,
                is_stopped=True,
            ),
        )

    def test_old_segment_references_release_after_clear_and_rotation(self):
        def retained_reference(release: str):
            mediator, _, path, metro = _build_network()
            interpolator = MetroInterpolator()
            interpolator.before_step(mediator)
            interpolator.after_step(mediator)
            old_reference = weakref.ref(path.segments[0])
            self.assertTrue(mediator.replace_path(path, [3, 0, 1, 2]))
            self.assertIsNotNone(old_reference())
            if release == "clear":
                interpolator.clear()
            else:
                interpolator.before_step(mediator)
                interpolator.after_step(mediator)
            return old_reference

        for release in ("clear", "rotation"):
            with self.subTest(release=release):
                old_reference = retained_reference(release)
                gc.collect()
                self.assertIsNone(old_reference())


if __name__ == "__main__":
    unittest.main()

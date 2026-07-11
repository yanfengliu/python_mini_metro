from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from rendering.layout import (
    build_visual_path,
    centered_path_orders,
    project_metro_pose,
)
from rendering.network_renderer import NetworkRenderer, NetworkStyle


@dataclass
class FakePoint:
    left: float
    top: float


@dataclass
class FakeStation:
    id: str
    position: FakePoint


@dataclass
class FakeSegment:
    segment_start: FakePoint
    segment_end: FakePoint
    start_station: FakeStation | None = None
    end_station: FakeStation | None = None


class FakePath:
    def __init__(
        self,
        path_id: str,
        color: tuple[int, int, int],
        stations: list[FakeStation],
        *,
        looped: bool = False,
    ) -> None:
        self.id = path_id
        self.color = color
        self.stations = stations
        self.is_looped = looped
        self.temp_point: FakePoint | None = None
        self.path_order = 77
        self.segments = self._segments()

    def _segments(self) -> list[FakeSegment]:
        path_segments = [
            FakeSegment(a.position, b.position, a, b)
            for a, b in zip(self.stations, self.stations[1:])
        ]
        if self.is_looped and len(self.stations) > 1:
            path_segments.append(
                FakeSegment(
                    self.stations[-1].position,
                    self.stations[0].position,
                    self.stations[-1],
                    self.stations[0],
                )
            )

        segments: list[FakeSegment] = []
        for index, segment in enumerate(path_segments):
            segments.append(segment)
            has_next = index < len(path_segments) - 1
            if has_next or self.is_looped:
                next_segment = path_segments[(index + 1) % len(path_segments)]
                segments.append(
                    FakeSegment(segment.segment_end, next_segment.segment_start)
                )
        return segments


def make_path(
    path_id: str = "red",
    color: tuple[int, int, int] = (220, 40, 40),
    points: tuple[tuple[float, float], ...] = ((10, 30), (110, 30)),
    *,
    looped: bool = False,
) -> FakePath:
    stations = [
        FakeStation(f"station-{index}", FakePoint(*point))
        for index, point in enumerate(points)
    ]
    return FakePath(path_id, color, stations, looped=looped)


def make_metro(
    segment_index: int,
    position: tuple[float, float],
    *,
    forward: bool = True,
    stopped: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        current_segment_idx=segment_index,
        position=FakePoint(*position),
        is_forward=forward,
        current_station=object() if stopped else None,
        speed=0.0 if stopped else 0.15,
    )


class TestRenderLayout(unittest.TestCase):
    def test_centered_orders_are_symmetric_for_even_and_odd_counts(self) -> None:
        self.assertEqual(centered_path_orders(0), ())
        self.assertEqual(centered_path_orders(1), (0.0,))
        self.assertEqual(centered_path_orders(2), (-0.5, 0.5))
        self.assertEqual(centered_path_orders(4), (-1.5, -0.5, 0.5, 1.5))

    def test_reversed_station_pair_uses_the_same_canonical_side(self) -> None:
        forward = make_path(points=((10, 20), (110, 60)))
        reverse = make_path(points=((110, 60), (10, 20)))

        forward_layout = build_visual_path(forward, order=1.0, lane_spacing=10)
        reverse_layout = build_visual_path(reverse, order=1.0, lane_spacing=10)

        forward_offset = (
            forward_layout.segments[0].start[0] - 10,
            forward_layout.segments[0].start[1] - 20,
        )
        reverse_offset = (
            reverse_layout.segments[0].start[0] - 110,
            reverse_layout.segments[0].start[1] - 60,
        )
        self.assertAlmostEqual(forward_offset[0], reverse_offset[0])
        self.assertAlmostEqual(forward_offset[1], reverse_offset[1])

    def test_visual_segments_preserve_logical_count_and_corner_padding(self) -> None:
        path = make_path(points=((10, 10), (110, 10), (110, 110)))

        layout = build_visual_path(path, order=1.0, lane_spacing=10)

        self.assertEqual(len(layout.segments), len(path.segments))
        self.assertEqual(
            [segment.kind for segment in layout.segments],
            ["path", "padding", "path"],
        )
        self.assertEqual(layout.segments[1].start, layout.segments[0].end)
        self.assertEqual(layout.segments[1].end, layout.segments[2].start)

    def test_metro_pose_projects_progress_and_reverse_heading(self) -> None:
        path = make_path()
        layout = build_visual_path(path, order=0.5, lane_spacing=10)

        forward = project_metro_pose(path, make_metro(0, (35, 30)), layout)
        reverse = project_metro_pose(
            path, make_metro(0, (85, 30), forward=False), layout
        )

        self.assertAlmostEqual(forward.progress, 0.25)
        self.assertAlmostEqual(forward.position[0], 35)
        self.assertAlmostEqual(forward.position[1], 35)
        self.assertAlmostEqual(forward.heading_degrees, 0)
        self.assertAlmostEqual(reverse.progress, 0.75)
        self.assertAlmostEqual(reverse.heading_degrees, 180)

    def test_stopped_metro_uses_traversal_side_of_corner_padding(self) -> None:
        path = make_path(points=((10, 10), (110, 10), (110, 110)))
        layout = build_visual_path(path, order=1.0, lane_spacing=10)

        forward = project_metro_pose(
            path, make_metro(1, (110, 10), stopped=True), layout
        )
        reverse = project_metro_pose(
            path,
            make_metro(1, (110, 10), forward=False, stopped=True),
            layout,
        )

        self.assertEqual(forward.position, layout.segments[1].start)
        self.assertEqual(forward.progress, 0.0)
        self.assertEqual(reverse.position, layout.segments[1].end)
        self.assertEqual(reverse.progress, 1.0)
        self.assertAlmostEqual(forward.heading_degrees, -135)
        self.assertAlmostEqual(reverse.heading_degrees, 45)

    def test_loop_padding_projects_at_both_traversal_ends(self) -> None:
        path = make_path(points=((20, 20), (100, 20), (100, 100)), looped=True)
        layout = build_visual_path(path, order=1.0, lane_spacing=8)
        last_index = len(path.segments) - 1

        forward = project_metro_pose(
            path, make_metro(last_index, (20, 20), stopped=True), layout
        )
        reverse = project_metro_pose(
            path,
            make_metro(last_index, (20, 20), forward=False, stopped=True),
            layout,
        )

        self.assertEqual(forward.position, layout.segments[-1].start)
        self.assertEqual(reverse.position, layout.segments[-1].end)
        self.assertEqual(layout.segments[-1].end, layout.segments[0].start)


class TestNetworkRenderer(unittest.TestCase):
    def setUp(self) -> None:
        self.style = NetworkStyle(
            lane_spacing=10,
            stroke_width=6,
            halo_width=10,
            supersample=3,
        )
        self.renderer = NetworkRenderer(self.style)
        self.surface = pygame.Surface((160, 120), pygame.SRCALPHA, 32)
        self.path = make_path()

    def test_cache_hits_invalidation_and_one_entry_bound(self) -> None:
        original_segments = tuple(self.path.segments)
        original_order = self.path.path_order

        self.renderer.draw(self.surface, [self.path])
        self.renderer.draw(self.surface, [self.path])
        self.assertEqual(self.renderer.cache_rebuild_count, 1)
        self.assertEqual(self.renderer.cache_entry_count, 1)

        self.path.temp_point = FakePoint(145, 90)
        self.renderer.draw(self.surface, [self.path])
        self.assertEqual(self.renderer.cache_rebuild_count, 1)

        self.path.color = (20, 80, 220)
        self.renderer.draw(self.surface, [self.path])
        self.assertEqual(self.renderer.cache_rebuild_count, 2)

        self.path.stations[1].position.left = 120
        self.renderer.draw(self.surface, [self.path])
        self.assertEqual(self.renderer.cache_rebuild_count, 3)

        larger = pygame.Surface((180, 120), pygame.SRCALPHA, 32)
        self.renderer.draw(larger, [self.path], orders=(1.0,))
        self.assertEqual(self.renderer.cache_rebuild_count, 4)
        self.assertEqual(self.renderer.cache_entry_count, 1)
        self.assertEqual(tuple(self.path.segments), original_segments)
        self.assertEqual(self.path.path_order, original_order)

    def test_empty_network_caches_layout_without_allocating_full_surface(self) -> None:
        layouts = self.renderer.draw(self.surface, [])
        self.renderer.draw(self.surface, [])

        self.assertEqual(layouts, ())
        self.assertEqual(self.renderer.cache_rebuild_count, 1)
        self.assertEqual(self.renderer.cache_entry_count, 0)

    def test_dynamic_temporary_line_is_not_baked_into_cache(self) -> None:
        self.renderer.draw(self.surface, [self.path])
        before = self.surface.copy()
        self.surface.fill((0, 0, 0, 0))
        self.path.temp_point = FakePoint(145, 90)

        self.renderer.draw(self.surface, [self.path])

        self.assertEqual(self.renderer.cache_rebuild_count, 1)
        self.assertNotEqual(before.get_at((135, 75)), self.surface.get_at((135, 75)))

    def test_cached_diagonal_stroke_has_antialiased_edge_pixels(self) -> None:
        diagonal = make_path(points=((20, 20), (130, 95)))

        self.renderer.draw(self.surface, [diagonal])

        alphas = {
            self.surface.get_at((x, y)).a
            for x in range(self.surface.get_width())
            for y in range(self.surface.get_height())
        }
        self.assertTrue(any(0 < alpha < 255 for alpha in alphas))


if __name__ == "__main__":
    unittest.main()

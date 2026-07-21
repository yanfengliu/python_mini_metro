from __future__ import annotations

import math
import os
import sys
import unittest
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import config
from entity.passenger import Passenger
from geometry.point import Point
from graph.node import Node
from rendering.game_renderer import GameRenderer
from rendering.layout import build_visual_path, project_metro_pose
from test.gm06c_render_state_support import render_state_signature
from test.gm06c_simulation_ui_support import (
    carriage_spacing,
    make_two_station_game,
    product_symbol,
    require_attribute,
    surface_bytes,
)
from travel_plan import TravelPlan


class _RecordingPassenger:
    def __init__(self, name: str) -> None:
        self.id = name
        self.draw_calls: list[dict[str, Any]] = []

    def draw(self, _surface, **kwargs) -> None:
        self.draw_calls.append(dict(kwargs))


def _surface() -> pygame.Surface:
    result = pygame.Surface(
        (config.screen_width, config.screen_height),
        pygame.SRCALPHA,
        32,
    )
    result.fill((*config.screen_color, 255))
    return result


def _exclusive_color_count(
    surface: pygame.Surface,
    center,
    all_centers,
    color,
) -> int:
    other_centers = tuple(candidate for candidate in all_centers if candidate != center)
    nearest = min(
        (math.dist(center, candidate) for candidate in other_centers),
        default=90.0,
    )
    half_extent = max(3, int(nearest / 2) - 1)
    rect = pygame.Rect(
        round(center[0]) - half_extent,
        round(center[1]) - half_extent,
        2 * half_extent + 1,
        2 * half_extent + 1,
    ).clip(surface.get_rect())
    expected = tuple(color)
    return sum(
        tuple(surface.get_at((x, y))[:3]) == expected
        and all(
            (x - center[0]) ** 2 + (y - center[1]) ** 2
            < (x - other[0]) ** 2 + (y - other[1]) ** 2
            for other in other_centers
        )
        for x in range(rect.left, rect.right)
        for y in range(rect.top, rect.bottom)
    )


def _mean_draw_position(passengers) -> tuple[float, float]:
    positions = [
        passenger.draw_calls[-1]["display_position"] for passenger in passengers
    ]
    return (
        sum(position[0] for position in positions) / len(positions),
        sum(position[1] for position in positions) / len(positions),
    )


class TestGM06cRealCarriageDrawing(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_real_carriage_draws_only_supplied_slice_without_owning_it(self) -> None:
        carriage_type = product_symbol(self, "entity.carriage", "Carriage")
        carriage = carriage_type()
        passengers = [_RecordingPassenger(f"slice-{index}") for index in range(3)]
        surface = pygame.Surface((240, 160), pygame.SRCALPHA, 32)

        carriage.draw(
            surface,
            passengers=passengers,
            display_position=(120.0, 80.0),
            rotation_degrees=30.0,
            current_time_ms=100,
            passenger_max_wait_time_ms=40_000,
        )

        self.assertFalse(hasattr(carriage, "passengers"))
        self.assertEqual([len(item.draw_calls) for item in passengers], [1, 1, 1])
        positions = tuple(item.draw_calls[0]["display_position"] for item in passengers)
        self.assertEqual(len(set(positions)), len(passengers))
        self.assertTrue(
            all(
                math.isfinite(coordinate)
                for position in positions
                for coordinate in position
            )
        )
        self.assertTrue(
            all(item.draw_calls[0]["rotation_degrees"] == 30.0 for item in passengers)
        )

    def test_two_occupied_carriages_render_slices_and_queue_outline_every_body(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6400)
        start.position = Point(260, 600)
        start.shape.position = start.position
        end.position = Point(900, 600)
        end.shape.position = end.position
        path.rebuild_geometry()
        metro.current_segment_idx = 0
        metro.current_segment = path.segments[0]
        metro.current_station = start
        metro.position = start.position
        attach = require_attribute(self, mediator, "attach_carriage")
        self.assertTrue(attach(path))
        self.assertTrue(attach(path))
        passengers = [_RecordingPassenger(f"rider-{index}") for index in range(18)]
        metro.passengers.extend(passengers)
        renderer = GameRenderer()
        ordinary = _surface()

        renderer.draw(ordinary, mediator)

        visual = build_visual_path(path, 0.0, config.path_order_shift)
        head = project_metro_pose(path, metro, visual)
        function = product_symbol(
            self,
            "rendering.consist_layout",
            "consist_layout",
        )
        tails = function(visual, head, 2, carriage_spacing(self))
        centers = (head.position, *(pose.position for pose in tails))
        for ordinal, center in enumerate(centers):
            passenger_slice = passengers[ordinal * 6 : (ordinal + 1) * 6]
            observed = _mean_draw_position(passenger_slice)
            self.assertAlmostEqual(observed[0], center[0], places=1)
            self.assertAlmostEqual(observed[1], center[1], places=1)
            self.assertEqual(
                _exclusive_color_count(
                    ordinary,
                    center,
                    centers,
                    config.metro_queue_outline_color,
                ),
                0,
            )

        metro.is_unassignment_queued = True
        queued = _surface()
        renderer.draw(queued, mediator)

        self.assertEqual([len(item.draw_calls) for item in passengers], [2] * 18)
        for center in centers:
            self.assertGreater(
                _exclusive_color_count(
                    queued,
                    center,
                    centers,
                    config.metro_queue_outline_color,
                ),
                0,
            )

    def test_first_and_repeated_draws_preserve_full_entity_shape_and_ui_state(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6401)
        start.position = Point(220, 560)
        start.shape.position = start.position
        end.position = Point(860, 560)
        end.shape.position = end.position
        path.rebuild_geometry()
        metro.current_segment_idx = 0
        metro.current_segment = path.segments[0]
        metro.current_station = start
        metro.position = start.position
        attach = require_attribute(self, mediator, "attach_carriage")
        self.assertTrue(attach(path))
        carriage = metro.carriages[0]
        waiting = Passenger(end.shape)
        waiting.id = "render-state-waiting"
        start.add_passenger(waiting)
        onboard = Passenger(start.shape)
        onboard.id = "render-state-onboard"
        metro.add_passenger(onboard)
        mediator.passengers.extend((waiting, onboard))
        plan = TravelPlan([Node(end)])
        plan.next_path = path
        mediator.travel_plans[waiting] = plan
        path_button = mediator.path_buttons[0]
        path_button.assign_path(path)
        path_button.show_cross = True
        mediator.path_to_button[path] = path_button
        mediator.deliveries = 3
        mediator.line_credits = 4
        start.start_snap_blip(mediator.time_ms, path.color)
        renderer = GameRenderer()
        renderer.before_step(mediator)
        renderer.after_step(mediator)
        before = render_state_signature(mediator)
        previous_cache = renderer.interpolator._previous
        current_cache = renderer.interpolator._current
        previous_items = tuple(previous_cache.items())
        current_items = tuple(current_cache.items())
        first = _surface()
        second = _surface()

        renderer.draw(first, mediator, alpha=0.5)
        self.assertEqual(render_state_signature(mediator), before)
        renderer.draw(second, mediator, alpha=0.5)

        self.assertEqual(surface_bytes(first), surface_bytes(second))
        self.assertEqual(render_state_signature(mediator), before)
        self.assertIn(carriage, metro.carriages)
        self.assertIs(renderer.interpolator._previous, previous_cache)
        self.assertIs(renderer.interpolator._current, current_cache)
        self.assertEqual(tuple(previous_cache.items()), previous_items)
        self.assertEqual(tuple(current_cache.items()), current_items)
        self.assertEqual(renderer.network_renderer.cache_entry_count, 1)
        self.assertEqual(renderer.network_renderer.cache_rebuild_count, 1)
        self.assertEqual(renderer.resources.font_count, 1)


if __name__ == "__main__":
    unittest.main()

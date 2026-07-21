from __future__ import annotations

import os
import sys
import unittest
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_color, screen_height, screen_width
from entity.passenger import Passenger
from env import MiniMetroEnv
from geometry.diamond import Diamond
from geometry.point import Point
from geometry.triangle import Triangle
from recursive_checkpoint import canonical_checkpoint
from rendering.game_renderer import GameRenderer


def _point_state(owner: Any, attribute: str) -> tuple[Any, ...]:
    if not hasattr(owner, attribute):
        return ("absent",)
    value = getattr(owner, attribute)
    if value is None:
        return ("present", None)
    return (
        "present",
        id(value),
        float(value.left),
        float(value.top),
    )


def _degrees_state(shape: Any) -> tuple[Any, ...]:
    if not hasattr(shape, "degrees"):
        return ("absent",)
    return ("present", float(shape.degrees))


def _shape_state(shape: Any) -> tuple[Any, ...]:
    return (
        id(shape),
        _point_state(shape, "position"),
        _degrees_state(shape),
    )


def _rect_state(rect: pygame.Rect | None) -> tuple[Any, ...] | None:
    if rect is None:
        return None
    return (id(rect), rect.x, rect.y, rect.width, rect.height)


def _render_state(mediator: Any) -> dict[str, Any]:
    """Capture mutable render-facing state omitted from canonical checkpoints."""

    return {
        "stations": tuple(
            (
                id(station),
                _point_state(station, "position"),
                _shape_state(station.shape),
                tuple(station.snap_blips),
            )
            for station in mediator.stations
        ),
        "passengers": tuple(
            (
                id(passenger),
                _point_state(passenger, "position"),
                _shape_state(passenger.destination_shape),
            )
            for passenger in mediator.passengers
        ),
        "paths": tuple(
            (
                id(path),
                path.path_order,
                tuple(
                    (
                        id(segment),
                        _point_state(segment, "segment_start"),
                        _point_state(segment, "segment_end"),
                        id(segment.line),
                    )
                    for segment in path.segments
                ),
                tuple(
                    (
                        id(metro),
                        id(metro.current_segment),
                        metro.current_segment_idx,
                    )
                    for metro in path.metros
                ),
            )
            for path in mediator.paths
        ),
        "metros": tuple(
            (
                id(metro),
                _point_state(metro, "position"),
                _shape_state(metro.shape),
                id(metro.current_segment),
                metro.current_segment_idx,
            )
            for metro in mediator.metros
        ),
        "buttons": tuple(
            (
                id(button),
                _point_state(button, "position"),
                _shape_state(button.shape),
                (
                    None
                    if getattr(button, "cross", None) is None
                    else _shape_state(button.cross)
                ),
            )
            for button in mediator.buttons
        ),
        "game_over_rects": (
            _rect_state(mediator.game_over_restart_rect),
            _rect_state(mediator.game_over_exit_rect),
        ),
    }


def _build_renderable_env(seed: int = 41) -> MiniMetroEnv:
    env = MiniMetroEnv(dt_ms=17)
    env.reset(seed=seed)
    mediator = env.mediator
    created = mediator.create_path_from_station_indices([0, 1, 2], loop=False)
    if created is None:
        raise AssertionError("deterministic render fixture could not create a path")
    if not mediator.assign_locomotive(created):
        raise AssertionError("deterministic render fixture could not assign a Metro")

    station_passenger = Passenger(Triangle((20, 20, 20), 5))
    station_passenger.position = Point(7, 11)
    mediator.stations[0].add_passenger(station_passenger)

    metro_passenger = Passenger(Diamond((30, 30, 30), 5))
    metro_passenger.position = Point(13, 17)
    mediator.metros[0].add_passenger(metro_passenger)
    mediator.passengers.extend((station_passenger, metro_passenger))

    mediator.stations[1].start_snap_blip(mediator.time_ms, created.color)
    mediator.path_buttons[0].on_hover()
    mediator.prepare_layout(screen_width, screen_height)
    return env


def _new_surface() -> pygame.Surface:
    surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA, 32)
    surface.fill(screen_color)
    return surface


class TestRenderPurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_repeated_render_is_pixel_deterministic_and_state_observational(self):
        env = _build_renderable_env()
        mediator = env.mediator
        renderer = GameRenderer()
        before_render_state = _render_state(mediator)
        before_checkpoint = canonical_checkpoint(env)

        first_surface = _new_surface()
        renderer.draw(first_surface, mediator, alpha=1.0)
        after_first_render_state = _render_state(mediator)
        after_first_checkpoint = canonical_checkpoint(env)

        second_surface = _new_surface()
        renderer.draw(second_surface, mediator, alpha=1.0)
        after_second_render_state = _render_state(mediator)
        after_second_checkpoint = canonical_checkpoint(env)

        self.assertEqual(
            pygame.image.tobytes(first_surface, "RGBA"),
            pygame.image.tobytes(second_surface, "RGBA"),
        )
        self.assertEqual(after_first_render_state, before_render_state)
        self.assertEqual(after_second_render_state, before_render_state)
        self.assertEqual(after_first_checkpoint, before_checkpoint)
        self.assertEqual(after_second_checkpoint, before_checkpoint)

    def test_repeated_render_reuses_one_bounded_network_cache_entry(self):
        env = _build_renderable_env()
        renderer = GameRenderer()
        surface = _new_surface()

        renderer.draw(surface, env.mediator, alpha=1.0)
        cached_surface = renderer.network_renderer._cache_surface
        cached_layouts = renderer.network_renderer._cache_layouts

        for _ in range(4):
            surface.fill(screen_color)
            renderer.draw(surface, env.mediator, alpha=1.0)

        self.assertEqual(renderer.network_renderer.cache_entry_count, 1)
        self.assertEqual(renderer.network_renderer.cache_rebuild_count, 1)
        self.assertIs(renderer.network_renderer._cache_surface, cached_surface)
        self.assertIs(renderer.network_renderer._cache_layouts, cached_layouts)

    def test_rendering_every_update_cannot_change_scripted_trajectory(self):
        def run_script(*, render_every_update: bool) -> dict[str, Any]:
            env = MiniMetroEnv(dt_ms=17)
            env.reset(seed=73)
            renderer = GameRenderer()
            surface = _new_surface()
            actions = [
                {"type": "create_path", "stations": [0, 1, 2], "loop": False},
                {"type": "assign_locomotive", "path_index": 0},
                *({"type": "noop"} for _ in range(89)),
            ]

            for action in actions:
                _, _, done, info = env.step(action, dt_ms=17)
                self.assertTrue(info["action_ok"])
                if render_every_update:
                    surface.fill(screen_color)
                    renderer.draw(surface, env.mediator, alpha=1.0)
                if done:
                    break

            return canonical_checkpoint(env)

        never_rendered = run_script(render_every_update=False)
        rendered_every_update = run_script(render_every_update=True)

        self.assertEqual(rendered_every_update, never_rendered)


if __name__ == "__main__":
    unittest.main()

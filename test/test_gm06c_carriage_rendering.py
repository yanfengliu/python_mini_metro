from __future__ import annotations

import hashlib
import os
import sys
import unittest
from types import SimpleNamespace
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import config
from entity.metro import Metro
from geometry.point import Point
from rendering.game_renderer import GameRenderer
from rendering.layout import (
    MetroPose,
    VisualPath,
    VisualSegment,
    build_visual_path,
    project_metro_pose,
)
from test.gm06c_simulation_ui_support import (
    carriage_spacing,
    make_two_station_game,
    product_symbol,
    require_attribute,
    surface_bytes,
)

ZERO_CARRIAGE_SHA256 = (
    "52731b8f9d0b4d98804f26a5c9666d9fdc85fcc0221a9eb6dfaee418a02952d2"
)
INTEGRATED_ZERO_CARRIAGE_CROP_SHA256 = (
    "6ab1ec747888507a135e162c947206b4cf5183347687198550cc1faab2efaad2"
)
_PASSENGER_KEYS = (
    "passengers",
    "passenger_slice",
    "display_passengers",
    "passengers_override",
)


class _RecordingBody:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.draw_calls: list[dict[str, Any]] = []

    def draw(self, _surface, **kwargs) -> None:
        self.draw_calls.append(dict(kwargs))


class _RecordingMetro(_RecordingBody):
    def __init__(self, passengers: list[Any], carriages: list[_RecordingBody]) -> None:
        super().__init__(6)
        self.id = "metro-recording"
        self.path_id = "recording-path"
        self.passengers = passengers
        self.carriages = carriages
        self._base_capacity = 6
        self.is_unassignment_queued = True


class _RecordingNetwork:
    def __init__(self, layout: VisualPath) -> None:
        self.layout = layout

    def draw(self, _surface, _paths):
        return (self.layout,)

    def clear_preview_cache(self) -> None:
        return


class _RecordingInterpolator:
    def __init__(self, head: MetroPose, carriages: tuple[MetroPose, ...]) -> None:
        self.head = head
        self.carriages = carriages

    def pose_for(self, *_args, **_kwargs) -> MetroPose:
        return self.head

    def poses_for_consist(self, *_args, **_kwargs) -> tuple[MetroPose, ...]:
        return self.carriages

    def consist_poses_for(self, *_args, **_kwargs) -> tuple[MetroPose, ...]:
        return self.carriages

    def sample_consist(self, *_args, **_kwargs) -> tuple[MetroPose, ...]:
        return self.carriages


class _Label:
    def __init__(self, text: str) -> None:
        self.text = text


class _RecordingFont:
    def __init__(self, owner) -> None:
        self.owner = owner

    def render(self, text, _antialias, _color):
        self.owner.rendered_text.append(text)
        return _Label(text)


class _RecordingResources:
    def __init__(self) -> None:
        self.rendered_text: list[str] = []

    def font(self, _name, _size):
        return _RecordingFont(self)


class _RecordingSurface:
    def __init__(self) -> None:
        self.blits: list[tuple[Any, Any]] = []

    def blit(self, source, destination) -> None:
        self.blits.append((source, destination))


def _passenger_argument(testcase: unittest.TestCase, call: dict[str, Any]):
    matches = [(name, call[name]) for name in _PASSENGER_KEYS if name in call]
    testcase.assertEqual(
        len(matches),
        1,
        f"body draw must receive one explicit canonical passenger slice: {call!r}",
    )
    return tuple(matches[0][1])


def _surface() -> pygame.Surface:
    surface = pygame.Surface(
        (config.screen_width, config.screen_height),
        pygame.SRCALPHA,
        32,
    )
    surface.fill((*config.screen_color, 255))
    return surface


def _crop(surface: pygame.Surface, center, half_width=42, half_height=32) -> bytes:
    left, top = center
    rect = pygame.Rect(
        round(left) - half_width,
        round(top) - half_height,
        2 * half_width + 1,
        2 * half_height + 1,
    ).clip(surface.get_rect())
    return pygame.image.tobytes(surface.subsurface(rect), "RGBA")


def _has_color(surface: pygame.Surface, center, color) -> bool:
    left, top = center
    rect = pygame.Rect(round(left) - 45, round(top) - 35, 91, 71).clip(
        surface.get_rect()
    )
    expected = tuple(color)
    return any(
        tuple(surface.get_at((x, y))[:3]) == expected
        for x in range(rect.left, rect.right)
        for y in range(rect.top, rect.bottom)
    )


class TestGM06cCarriageRenderingContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_renderer_slices_canonical_passenger_order_across_each_body(self) -> None:
        passengers = [object() for _ in range(11)]
        carriages = [_RecordingBody(2), _RecordingBody(3)]
        metro = _RecordingMetro(passengers, carriages)
        visual = VisualPath(
            path_id=metro.path_id,
            color=(10, 20, 30),
            order=0.0,
            is_looped=False,
            segments=(VisualSegment(0, "path", (0.0, 0.0), (400.0, 0.0), "a", "b"),),
        )
        head = MetroPose((250.0, 300.0), 0.0, 0, 0.5, True, False)
        carriage_poses = (
            MetroPose((180.0, 300.0), 0.0, 0, 0.3, True, False),
            MetroPose((110.0, 300.0), 0.0, 0, 0.1, True, False),
        )
        renderer = GameRenderer(
            network_renderer=_RecordingNetwork(visual),
            interpolator=_RecordingInterpolator(head, carriage_poses),
        )
        renderer._draw_hud = lambda *_args: None
        state = SimpleNamespace(
            paths=[SimpleNamespace(id=metro.path_id)],
            metros=[metro],
            stations=[],
            buttons=[],
            path_buttons=[],
            speed_buttons=[],
            path_redraw=None,
            path_edit_selection=None,
            time_ms=0,
            passenger_max_wait_time_ms=40_000,
            is_game_over=False,
        )

        renderer.draw(pygame.Surface((500, 500), pygame.SRCALPHA, 32), state)

        self.assertEqual(len(metro.draw_calls), 1)
        self.assertEqual([len(item.draw_calls) for item in carriages], [1, 1])
        self.assertEqual(
            _passenger_argument(self, metro.draw_calls[0]),
            tuple(passengers[:6]),
        )
        self.assertEqual(
            _passenger_argument(self, carriages[0].draw_calls[0]),
            tuple(passengers[6:8]),
        )
        self.assertEqual(
            _passenger_argument(self, carriages[1].draw_calls[0]),
            tuple(passengers[8:11]),
        )
        self.assertEqual(metro.draw_calls[0]["display_position"], head.position)
        self.assertEqual(
            tuple(call.draw_calls[0]["display_position"] for call in carriages),
            tuple(pose.position for pose in carriage_poses),
        )

    def test_hud_adds_fourth_available_carriage_line_at_next_row(self) -> None:
        resources = _RecordingResources()
        renderer = GameRenderer(resources=resources)
        surface = _RecordingSurface()
        state = SimpleNamespace(
            deliveries=23,
            line_credits=4,
            available_locomotives=1,
            available_carriages=2,
        )

        renderer._draw_hud(surface, state)

        self.assertEqual(
            resources.rendered_text,
            [
                "Passengers Delivered: 23",
                "Line Credits: 4",
                "Locomotives Available: 1",
                "Carriages Available: 2",
            ],
        )
        self.assertEqual(
            [destination for _source, destination in surface.blits],
            [
                config.hud_display_coords,
                (
                    config.hud_display_coords[0],
                    config.hud_display_coords[1] + config.hud_line_spacing,
                ),
                (
                    config.hud_display_coords[0],
                    config.hud_display_coords[1] + 2 * config.hud_line_spacing,
                ),
                (
                    config.hud_display_coords[0],
                    config.hud_display_coords[1] + 3 * config.hud_line_spacing,
                ),
            ],
        )

    def test_zero_carriage_direct_draw_retains_established_locomotive_bytes(
        self,
    ) -> None:
        metro = Metro()
        metro.position = Point(80, 50)
        require_attribute(self, metro, "carriages")
        self.assertEqual(metro.carriages, [])
        surface = pygame.Surface((160, 100), pygame.SRCALPHA, 32)
        surface.fill((*config.screen_color, 255))

        metro.draw(surface)

        digest = hashlib.sha256(surface_bytes(surface)).hexdigest()
        self.assertEqual(digest, ZERO_CARRIAGE_SHA256)

    def test_live_attach_detach_pixels_and_queue_outline_cover_carriage_body(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6350)
        start.position = Point(100, 500)
        start.shape.position = start.position
        end.position = Point(500, 500)
        end.shape.position = end.position
        path.rebuild_geometry()
        metro.current_segment = path.segments[0]
        metro.current_segment_idx = 0
        metro.current_station = start
        metro.position = start.position
        renderer = GameRenderer()
        baseline_surface = _surface()
        renderer.draw(baseline_surface, mediator)
        baseline = _crop(baseline_surface, (80, 500), 80, 55)
        self.assertEqual(
            hashlib.sha256(baseline).hexdigest(),
            INTEGRATED_ZERO_CARRIAGE_CROP_SHA256,
        )

        attach = require_attribute(self, mediator, "attach_carriage")
        detach = require_attribute(self, mediator, "detach_carriage")
        self.assertTrue(attach(path))
        attached_surface = _surface()
        renderer.draw(attached_surface, mediator)
        attached = _crop(attached_surface, (80, 500), 80, 55)
        self.assertNotEqual(attached, baseline)

        function = product_symbol(
            self,
            "rendering.consist_layout",
            "consist_layout",
        )
        visual = build_visual_path(path, 0.0, config.path_order_shift)
        head = project_metro_pose(path, metro, visual)
        spacing = carriage_spacing(self)
        carriage_pose = function(visual, head, 1, spacing)[0]
        ordinary_crop = _crop(attached_surface, carriage_pose.position)
        self.assertFalse(
            _has_color(
                attached_surface,
                carriage_pose.position,
                config.metro_queue_outline_color,
            )
        )

        metro.is_unassignment_queued = True
        queued_surface = _surface()
        renderer.draw(queued_surface, mediator)
        queued_crop = _crop(queued_surface, carriage_pose.position)
        self.assertNotEqual(queued_crop, ordinary_crop)
        self.assertTrue(
            _has_color(
                queued_surface,
                carriage_pose.position,
                config.metro_queue_outline_color,
            )
        )

        metro.is_unassignment_queued = False
        self.assertTrue(detach(path))
        detached_surface = _surface()
        renderer.draw(detached_surface, mediator)
        self.assertEqual(_crop(detached_surface, (80, 500), 80, 55), baseline)

    def test_repeated_draw_is_byte_identical_state_pure_and_cache_bounded(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6351)
        start.position = Point(160, 500)
        start.shape.position = start.position
        end.position = Point(700, 500)
        end.shape.position = end.position
        path.rebuild_geometry()
        metro.current_segment = path.segments[0]
        metro.current_station = start
        metro.position = start.position
        attach = require_attribute(self, mediator, "attach_carriage")
        self.assertTrue(attach(path))
        renderer = GameRenderer()
        renderer.before_step(mediator)
        renderer.after_step(mediator)
        warm = _surface()
        renderer.draw(warm, mediator, alpha=0.5)
        passenger_list = metro.passengers
        passenger_items = tuple(metro.passengers)
        carriage_list = metro.carriages
        carriage_items = tuple(metro.carriages)
        entity_ids = (
            (id(metro), metro.id),
            *((id(item), item.id) for item in metro.carriages),
        )
        previous_cache = renderer.interpolator._previous
        current_cache = renderer.interpolator._current
        previous_items = tuple(previous_cache.items())
        current_items = tuple(current_cache.items())
        network_rebuilds = renderer.network_renderer.cache_rebuild_count
        font_count = renderer.resources.font_count

        first = _surface()
        second = _surface()
        renderer.draw(first, mediator, alpha=0.5)
        renderer.draw(second, mediator, alpha=0.5)

        self.assertEqual(surface_bytes(first), surface_bytes(second))
        self.assertIs(metro.passengers, passenger_list)
        self.assertEqual(tuple(metro.passengers), passenger_items)
        self.assertIs(metro.carriages, carriage_list)
        self.assertEqual(tuple(metro.carriages), carriage_items)
        self.assertEqual(
            (
                (id(metro), metro.id),
                *((id(item), item.id) for item in metro.carriages),
            ),
            entity_ids,
        )
        self.assertIs(renderer.interpolator._previous, previous_cache)
        self.assertIs(renderer.interpolator._current, current_cache)
        self.assertEqual(tuple(previous_cache.items()), previous_items)
        self.assertEqual(tuple(current_cache.items()), current_items)
        self.assertEqual(
            renderer.network_renderer.cache_rebuild_count, network_rebuilds
        )
        self.assertEqual(renderer.network_renderer.cache_entry_count, 1)
        self.assertEqual(renderer.resources.font_count, font_count)


if __name__ == "__main__":
    unittest.main()

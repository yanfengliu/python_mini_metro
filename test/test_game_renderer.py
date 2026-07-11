from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from rendering.game_renderer import GameRenderer, LazyRenderResources
from rendering.interpolation import MetroInterpolator, interpolate_heading
from rendering.layout import build_visual_path


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
    def __init__(self) -> None:
        station_a = FakeStation("a", FakePoint(10, 30))
        station_b = FakeStation("b", FakePoint(110, 30))
        self.id = "path-1"
        self.color = (210, 40, 40)
        self.stations = [station_a, station_b]
        self.segments = [
            FakeSegment(
                station_a.position,
                station_b.position,
                station_a,
                station_b,
            )
        ]
        self.is_looped = False
        self.temp_point = None
        self.metros: list[FakeMetro] = []


class FakeMetro:
    def __init__(self, event_log: list[str] | None = None) -> None:
        self.id = "metro-1"
        self.path_id = "path-1"
        self.current_segment_idx = 0
        self.position = FakePoint(10, 30)
        self.is_forward = True
        self.current_station = None
        self.speed = 1.0
        self.event_log = event_log
        self.observed_display_position = None
        self.observed_rotation = None

    def draw(
        self,
        surface,
        display_position=None,
        rotation_degrees=None,
        **kwargs,
    ) -> None:
        del surface, kwargs
        if self.event_log is not None:
            self.event_log.append("metro-passengers")
        self.observed_display_position = display_position
        self.observed_rotation = rotation_degrees


class FakeNetworkRenderer:
    def __init__(self, event_log: list[str], layout) -> None:
        self.event_log = event_log
        self.layout = layout

    def draw(self, surface, paths):
        del surface, paths
        self.event_log.append("network")
        return (self.layout,)


class FakeDrawable:
    def __init__(self, label: str, event_log: list[str]) -> None:
        self.label = label
        self.event_log = event_log
        self.observed_kwargs = None

    def draw(self, surface, **kwargs) -> None:
        del surface
        self.observed_kwargs = kwargs
        self.event_log.append(self.label)


class TestMetroInterpolator(unittest.TestCase):
    def setUp(self) -> None:
        self.path = FakePath()
        self.metro = FakeMetro()
        self.path.metros.append(self.metro)
        self.state = SimpleNamespace(metros=[self.metro])
        self.layout = build_visual_path(self.path, order=0.5, lane_spacing=10)

    def test_before_and_after_step_interpolate_without_mutating_metro(self) -> None:
        interpolator = MetroInterpolator()
        interpolator.before_step(self.state)
        self.metro.position.left = 50
        interpolator.after_step(self.state)
        gameplay_position = (self.metro.position.left, self.metro.position.top)

        pose = interpolator.pose_for(self.path, self.metro, self.layout, alpha=0.5)

        self.assertEqual(pose.position, (30.0, 35.0))
        self.assertEqual(
            (self.metro.position.left, self.metro.position.top), gameplay_position
        )

    def test_missing_history_and_new_metro_fall_back_to_current_pose(self) -> None:
        interpolator = MetroInterpolator()
        self.metro.position.left = 80

        pose = interpolator.pose_for(self.path, self.metro, self.layout, alpha=0.0)

        self.assertEqual(pose.position, (80.0, 35.0))

    def test_heading_interpolation_takes_shortest_arc(self) -> None:
        self.assertAlmostEqual(interpolate_heading(170, -170, 0.5), 180)
        self.assertAlmostEqual(interpolate_heading(-170, 170, 0.5), -180)


class TestLazyRenderResources(unittest.TestCase):
    def test_constructor_is_lazy_and_fonts_are_cached(self) -> None:
        fake_font = object()
        with (
            patch("pygame.font.get_init", return_value=False),
            patch("pygame.font.init") as init,
            patch("pygame.font.Font", return_value=fake_font) as bundled_font,
            patch("pygame.font.SysFont") as sys_font,
        ):
            resources = LazyRenderResources()
            init.assert_not_called()
            sys_font.assert_not_called()

            first = resources.font("courier", 24)
            second = resources.font("courier", 24)

        self.assertIs(first, fake_font)
        self.assertIs(second, fake_font)
        init.assert_called_once_with()
        bundled_font.assert_called_once_with(None, 24)
        sys_font.assert_not_called()
        self.assertEqual(resources.font_count, 1)


class TestGameRenderer(unittest.TestCase):
    def setUp(self) -> None:
        self.surface = pygame.Surface((320, 240), pygame.SRCALPHA, 32)
        self.event_log: list[str] = []
        self.path = FakePath()
        self.metro = FakeMetro(self.event_log)
        self.path.metros.append(self.metro)
        self.station = FakeDrawable("station-passengers", self.event_log)
        self.path_button = FakeDrawable("path-button", self.event_log)
        self.path_button.is_locked = False
        self.path_button.path = self.path
        self.speed_button = FakeDrawable("speed-button", self.event_log)
        self.speed_button.action = "speed_1"
        self.layout = build_visual_path(self.path, order=0.0, lane_spacing=10)
        self.network = FakeNetworkRenderer(self.event_log, self.layout)
        self.renderer = GameRenderer(network_renderer=self.network)
        self.state = SimpleNamespace(
            paths=[self.path],
            stations=[self.station],
            metros=[self.metro],
            path_buttons=[self.path_button],
            speed_buttons=[self.speed_button],
            buttons=[self.path_button, self.speed_button],
            time_ms=100,
            passenger_max_wait_time_ms=40_000,
            score=7,
            is_game_over=True,
            game_over_restart_rect=pygame.Rect(10, 120, 300, 64),
            game_over_exit_rect=pygame.Rect(10, 202, 300, 64),
            get_purchase_price_for_path_button_idx=lambda index: 90,
            can_purchase_path_button_idx=lambda index: False,
            is_speed_button_active=lambda action: True,
        )

    def test_draw_uses_stable_layer_order(self) -> None:
        with (
            patch.object(
                self.renderer,
                "_draw_score",
                side_effect=lambda *args: self.event_log.append("score"),
            ),
            patch.object(
                self.renderer,
                "_draw_game_over",
                side_effect=lambda *args: self.event_log.append("game-over"),
            ),
        ):
            self.renderer.draw(self.surface, self.state, alpha=1.0)

        self.assertEqual(
            self.event_log,
            [
                "network",
                "station-passengers",
                "metro-passengers",
                "path-button",
                "speed-button",
                "score",
                "game-over",
            ],
        )

    def test_draw_passes_interpolated_pose_without_changing_gameplay_state(
        self,
    ) -> None:
        self.renderer.before_step(self.state)
        self.metro.position.left = 50
        self.renderer.after_step(self.state)
        original_position = (self.metro.position.left, self.metro.position.top)

        with (
            patch.object(self.renderer, "_draw_score"),
            patch.object(self.renderer, "_draw_game_over"),
        ):
            self.renderer.draw(self.surface, self.state, alpha=0.5)

        self.assertEqual(
            self.metro.observed_display_position,
            (30.0, 30.0),
        )
        self.assertAlmostEqual(self.metro.observed_rotation, 0)
        self.assertEqual(
            (self.metro.position.left, self.metro.position.top), original_position
        )

    def test_locked_path_button_receives_renderer_cached_font(self) -> None:
        self.state.is_game_over = False
        self.path_button.is_locked = True
        self.path_button.show_cross = True

        with patch.object(self.renderer, "_draw_score"):
            self.renderer.draw(self.surface, self.state)
            assert self.path_button.observed_kwargs is not None
            first_font = self.path_button.observed_kwargs["buy_text_font"]
            self.renderer.draw(self.surface, self.state)

        assert self.path_button.observed_kwargs is not None
        self.assertIs(self.path_button.observed_kwargs["buy_text_font"], first_font)
        self.assertEqual(self.renderer.resources.font_count, 1)

    def test_game_over_uses_prepared_hit_rects_without_mutating_them(self) -> None:
        self.state.is_game_over = True
        restart_before = self.state.game_over_restart_rect.copy()
        exit_before = self.state.game_over_exit_rect.copy()

        self.renderer.draw(self.surface, self.state)

        self.assertEqual(self.state.game_over_restart_rect, restart_before)
        self.assertEqual(self.state.game_over_exit_rect, exit_before)
        self.assertGreaterEqual(self.renderer.resources.font_count, 3)


if __name__ == "__main__":
    unittest.main()

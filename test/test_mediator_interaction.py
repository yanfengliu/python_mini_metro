from unittest.mock import MagicMock, patch

from test import mediator_test_support as support

# isort: split

import pygame

from config import screen_height, screen_width, station_color, station_size
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.circle import Circle
from geometry.point import Point
from mediator import Mediator
from ui.button import Button


class TestMediatorInteraction(support.MediatorTestCase):
    def test_react_mouse_down(self):
        for station in self.mediator.stations:
            station.draw(self.screen)
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_DOWN, Point(-1, -1)))

        self.assertTrue(self.mediator.is_mouse_down)

    def test_generate_distinct_path_colors_handles_non_positive_count(self):
        self.assertEqual(self.mediator.generate_distinct_path_colors(0), {})

    def test_constructor_does_not_initialize_render_resources(self):
        with patch("pygame.font.init") as font_init, patch("pygame.font.Font") as font:
            Mediator()

        font_init.assert_not_called()
        font.assert_not_called()

    def test_generate_distinct_path_colors_backfills_color_collisions(self):
        calls = {"count": 0}

        def fake_hue_to_rgb(_hue, saturation=1.0, value=1.0):
            calls["count"] += 1
            if calls["count"] <= self.mediator.num_paths:
                return (0, 0, 0)
            idx = calls["count"]
            return (idx, idx, idx)

        with patch("mediator.hue_to_rgb", side_effect=fake_hue_to_rgb):
            colors = self.mediator.generate_distinct_path_colors(
                self.mediator.num_paths
            )

        self.assertEqual(len(colors), self.mediator.num_paths)

    def test_get_containing_entity(self):
        self.assertTrue(
            self.mediator.get_containing_entity(
                self.mediator.stations[2].position + Point(1, 1)
            )
        )

    def test_react_mouse_up(self):
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_UP, Point(-1, -1)))

        self.assertFalse(self.mediator.is_mouse_down)

    def test_handle_game_over_click(self):
        mediator = Mediator()
        mediator.is_game_over = True
        mediator.game_over_restart_rect = pygame.Rect(0, 0, 10, 10)
        mediator.game_over_exit_rect = pygame.Rect(20, 0, 10, 10)

        self.assertEqual(mediator.handle_game_over_click(Point(5, 5)), "restart")
        self.assertEqual(mediator.handle_game_over_click(Point(25, 5)), "exit")
        self.assertIsNone(mediator.handle_game_over_click(Point(50, 50)))

    def test_prepare_layout_makes_first_frame_controls_clickable(self):
        mediator = Mediator()
        mediator.prepare_layout(screen_width, screen_height)

        self.assertIs(
            mediator.get_containing_entity(mediator.path_buttons[0].position),
            mediator.path_buttons[0],
        )
        self.assertIs(
            mediator.get_containing_entity(mediator.speed_buttons[0].position),
            mediator.speed_buttons[0],
        )
        mediator.is_game_over = True
        assert mediator.game_over_restart_rect is not None
        self.assertEqual(
            mediator.handle_game_over_click(
                Point(*mediator.game_over_restart_rect.center)
            ),
            "restart",
        )

    def test_compatibility_render_reuses_renderer_and_adapts_layout(self):
        surface = pygame.Surface((800, 600))

        self.mediator.render(surface)
        compatibility_renderer = self.mediator._compat_renderer
        self.mediator.render(surface)

        self.assertIs(self.mediator._compat_renderer, compatibility_renderer)
        self.assertLess(self.mediator.path_buttons[-1].position.left, 800)
        self.assertLess(self.mediator.path_buttons[-1].position.top, 600)
        assert self.mediator.game_over_restart_rect is not None
        self.assertEqual(self.mediator.game_over_restart_rect.centerx, 400)

    def test_mouse_motion_no_entity_triggers_exit(self):
        mediator = Mediator()
        mediator.stations = []
        button = MagicMock()
        button.contains = MagicMock(return_value=False)
        mediator.buttons = [button]
        mediator.react_mouse_event(
            MouseEvent(MouseEventType.MOUSE_MOTION, Point(-1000, -1000))
        )
        button.on_exit.assert_called_once()

    def test_mouse_motion_over_button_triggers_hover(self):
        mediator = Mediator()
        mediator.stations = []

        class HoverButton(Button):
            def __init__(self):
                super().__init__(Circle(station_color, station_size))
                self.position = Point(0, 0)
                self.hovered = False

            def contains(self, point: Point) -> bool:
                return True

            def on_hover(self):
                self.hovered = True

            def on_exit(self):
                pass

            def on_click(self):
                pass

        button = HoverButton()
        mediator.buttons = [button]
        mediator.react_mouse_event(MouseEvent(MouseEventType.MOUSE_MOTION, Point(0, 0)))
        self.assertTrue(button.hovered)

    def test_speed_buttons_pause_and_resume_with_multiplier(self):
        mediator = Mediator()
        mediator.prepare_layout(self.width, self.height)
        pause_button = mediator.speed_buttons[0]
        speed_4_button = mediator.speed_buttons[3]

        mediator.react_mouse_event(
            MouseEvent(MouseEventType.MOUSE_UP, pause_button.position)
        )
        self.assertTrue(mediator.is_paused)

        mediator.react_mouse_event(
            MouseEvent(MouseEventType.MOUSE_UP, speed_4_button.position)
        )
        self.assertFalse(mediator.is_paused)
        self.assertEqual(mediator.game_speed_multiplier, 4)

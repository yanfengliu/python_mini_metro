import os
import runpy
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main
from config import framerate, screen_height, screen_width
from game_session import GameSession
from mediator import Mediator
from path_redraw import PathRedrawGesture
from settings import DEFAULT_SETTINGS


class TestMain(unittest.TestCase):
    def test_letterbox_mouse_up_cancels_live_redraw_without_release_actions(self):
        mouse_up = main.pygame.MOUSEBUTTONUP
        mediator = Mediator(seed=5055)
        path = mediator.create_path_from_station_indices([0, 1, 2])
        self.assertIsNotNone(path)
        assert path is not None
        mediator.set_paused(True)
        mediator.path_redraw = PathRedrawGesture(path)
        mediator.path_to_button[path].show_cross = True
        mediator.is_mouse_down = True
        real_session = GameSession

        with (
            patch("main.pygame") as pygame_mock,
            patch("main.Mediator", return_value=mediator),
            patch(
                "main.GameSession",
                side_effect=lambda subject, **kwargs: real_session(subject, **kwargs),
            ),
            patch("main.GameRenderer") as renderer_mock,
            patch.object(
                mediator, "replace_path", wraps=mediator.replace_path
            ) as replace,
            patch.object(mediator, "remove_path", wraps=mediator.remove_path) as remove,
            patch.object(
                mediator,
                "try_purchase_path_button",
                wraps=mediator.try_purchase_path_button,
            ) as purchase,
            patch.object(
                mediator,
                "apply_speed_action",
                wraps=mediator.apply_speed_action,
            ) as speed,
        ):
            pygame_mock.QUIT = main.pygame.QUIT
            pygame_mock.MOUSEBUTTONDOWN = main.pygame.MOUSEBUTTONDOWN
            pygame_mock.MOUSEBUTTONUP = mouse_up
            pygame_mock.MOUSEMOTION = main.pygame.MOUSEMOTION
            window = MagicMock()
            window.get_size.return_value = (1000, 1000)
            pygame_mock.display.set_mode.return_value = window
            game_surface = MagicMock()
            game_surface.get_size.return_value = (screen_width, screen_height)
            pygame_mock.Surface.return_value = game_surface
            clock = MagicMock()
            clock.tick.return_value = 0
            pygame_mock.time.Clock.return_value = clock
            pygame_mock.event.get.return_value = [
                SimpleNamespace(type=mouse_up, pos=(10, 10), button=1)
            ]

            main.run_game(max_frames=1)

        self.assertFalse(mediator.is_mouse_down)
        self.assertIsNone(mediator.path_redraw)
        self.assertIsNone(mediator.path_edit_selection)
        self.assertIn(path, mediator.paths)
        self.assertFalse(mediator.path_to_button[path].show_cross)
        replace.assert_not_called()
        remove.assert_not_called()
        purchase.assert_not_called()
        speed.assert_not_called()
        renderer_mock.return_value.draw.assert_called_once()

    def test_letterbox_mouse_up_dispatches_one_outside_cancel(self):
        with (
            patch("main.pygame") as pygame_mock,
            patch("main.Mediator") as mediator_mock,
            patch("main.GameSession") as session_mock,
            patch("main.GameRenderer"),
            patch("main.convert_pygame_event") as convert_mock,
        ):
            pygame_mock.QUIT = 12
            pygame_mock.MOUSEBUTTONDOWN = 13
            pygame_mock.MOUSEBUTTONUP = 14
            pygame_mock.MOUSEMOTION = 15
            window = MagicMock()
            window.get_size.return_value = (1000, 1000)
            pygame_mock.display.set_mode.return_value = window
            game_surface = MagicMock()
            game_surface.get_size.return_value = (screen_width, screen_height)
            pygame_mock.Surface.return_value = game_surface
            clock = MagicMock()
            clock.tick.return_value = 17
            pygame_mock.time.Clock.return_value = clock
            outside_up = SimpleNamespace(type=pygame_mock.MOUSEBUTTONUP, pos=(10, 10))
            pygame_mock.event.get.return_value = [outside_up]
            mediator_mock.return_value.is_game_over = False
            session = session_mock.return_value
            session.advance.return_value = SimpleNamespace(alpha=0.0)
            converted = MagicMock()
            convert_mock.return_value = converted

            main.run_game(max_frames=1)

            convert_mock.assert_called_once_with(
                outside_up,
                mouse_position=(-1, -1),
            )
            session.dispatch.assert_called_once_with(converted)

    def test_run_game_dispatches_input_before_fixed_update_and_render(self):
        with (
            patch("main.pygame") as pygame_mock,
            patch("main.Mediator") as mediator_mock,
            patch("main.GameSession") as session_mock,
            patch("main.GameRenderer") as renderer_mock,
            patch("main.convert_pygame_event") as convert_mock,
            # Insulate the settings load so the set_mode-once assertion below is
            # independent of any developer machine's persisted fullscreen=True.
            patch("main.read_settings", return_value=DEFAULT_SETTINGS),
        ):
            pygame_mock.QUIT = 12
            window = MagicMock()
            window.get_size.return_value = (screen_width, screen_height)
            pygame_mock.display.set_mode.return_value = window
            game_surface = MagicMock()
            game_surface.get_size.return_value = (screen_width, screen_height)
            pygame_mock.Surface.return_value = game_surface
            clock = MagicMock()
            clock.tick.return_value = 17
            pygame_mock.time.Clock.return_value = clock
            pygame_event = MagicMock(type=0)
            pygame_mock.event.get.return_value = [pygame_event]
            converted = MagicMock()
            convert_mock.return_value = converted
            mediator = mediator_mock.return_value
            mediator.is_game_over = False
            session = session_mock.return_value
            session.advance.return_value = SimpleNamespace(alpha=0.25)

            main.run_game(max_frames=1)

            pygame_mock.display.set_mode.assert_called_once_with(
                (screen_width, screen_height), pygame_mock.RESIZABLE
            )
            clock.tick.assert_called_once_with(framerate)
            session.prepare_layout.assert_called_once_with(game_surface)
            session.dispatch.assert_called_once_with(converted)
            session.advance.assert_called_once_with(17)
            renderer_mock.return_value.draw.assert_called_once_with(
                game_surface, mediator, alpha=0.25, reduced_motion=False
            )
            pygame_mock.display.flip.assert_called_once()

    def test_run_game_quit_prevents_simulation_and_render(self):
        with (
            patch("main.pygame") as pygame_mock,
            patch("main.Mediator") as mediator_mock,
            patch("main.GameSession") as session_mock,
            patch("main.GameRenderer") as renderer_mock,
        ):
            pygame_mock.QUIT = 12
            window = MagicMock()
            window.get_size.return_value = (screen_width, screen_height)
            pygame_mock.display.set_mode.return_value = window
            game_surface = MagicMock()
            game_surface.get_size.return_value = (screen_width, screen_height)
            pygame_mock.Surface.return_value = game_surface
            clock = MagicMock()
            clock.tick.return_value = 17
            pygame_mock.time.Clock.return_value = clock
            pygame_mock.event.get.return_value = [MagicMock(type=pygame_mock.QUIT)]
            mediator_mock.return_value.is_game_over = False

            with self.assertRaises(SystemExit):
                main.run_game(max_frames=1)

            session_mock.return_value.advance.assert_not_called()
            renderer_mock.return_value.draw.assert_not_called()

    def test_main_module_runs_with_env_limit(self):
        with (
            patch.dict(os.environ, {"PYTHON_MINI_METRO_MAX_FRAMES": "1"}),
            patch("pygame.display.set_mode", return_value=MagicMock()) as set_mode,
            patch("pygame.Surface") as surface_mock,
            patch("pygame.time.Clock") as clock_mock,
            patch("pygame.event.get", return_value=[MagicMock(type=0)]),
            patch("pygame.display.flip"),
            patch("pygame.init"),
            patch("mediator.Mediator") as mediator_mock,
            patch("game_session.GameSession") as session_mock,
            patch("rendering.game_renderer.GameRenderer"),
            patch(
                "event.convert.convert_pygame_event", return_value=MagicMock()
            ) as convert_mock,
        ):
            set_mode.return_value.get_size.return_value = (
                screen_width,
                screen_height,
            )
            surface_mock.return_value.get_size.return_value = (
                screen_width,
                screen_height,
            )
            clock = MagicMock()
            clock.tick.return_value = 17
            clock_mock.return_value = clock
            mediator_mock.return_value.is_game_over = False
            session_mock.return_value.advance.return_value = SimpleNamespace(alpha=0.0)

            runpy.run_module("main", run_name="__main__")

            session_mock.return_value.advance.assert_called_once_with(17)
            convert_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

import os
import runpy
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main
from config import framerate, screen_height, screen_width


class TestMain(unittest.TestCase):
    def test_run_game_dispatches_input_before_fixed_update_and_render(self):
        with (
            patch("main.pygame") as pygame_mock,
            patch("main.Mediator") as mediator_mock,
            patch("main.GameSession") as session_mock,
            patch("main.GameRenderer") as renderer_mock,
            patch("main.convert_pygame_event") as convert_mock,
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
                game_surface, mediator, alpha=0.25
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

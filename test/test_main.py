import os
import runpy
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main


class TestMain(unittest.TestCase):
    def test_run_game_processes_events_and_exits_on_frame_limit(self):
        with patch("main.pygame") as pygame_mock, patch(
            "main.Mediator"
        ) as mediator_mock, patch("main.convert_pygame_event") as convert_mock:
            pygame_mock.SCALED = 1
            pygame_mock.QUIT = 12
            screen = MagicMock()
            pygame_mock.display.set_mode.return_value = screen
            clock = MagicMock()
            clock.tick.return_value = 16
            pygame_mock.time.Clock.return_value = clock
            pygame_mock.event.get.return_value = [MagicMock(type=0)]
            convert_mock.return_value = MagicMock()

            main.run_game(max_frames=1)

            mediator_instance = mediator_mock.return_value
            mediator_instance.increment_time.assert_called_once()
            mediator_instance.react.assert_called_once()
            pygame_mock.display.flip.assert_called_once()

    def test_run_game_raises_on_quit(self):
        with patch("main.pygame") as pygame_mock, patch(
            "main.Mediator"
        ) as mediator_mock, patch("main.convert_pygame_event"):
            pygame_mock.SCALED = 1
            pygame_mock.QUIT = 12
            pygame_mock.display.set_mode.return_value = MagicMock()
            clock = MagicMock()
            clock.tick.return_value = 16
            pygame_mock.time.Clock.return_value = clock
            pygame_mock.event.get.return_value = [MagicMock(type=pygame_mock.QUIT)]

            with self.assertRaises(SystemExit):
                main.run_game(max_frames=1)

            mediator_mock.return_value.increment_time.assert_called_once()

    def test_main_module_runs_with_env_limit(self):
        with patch.dict(os.environ, {"PYTHON_MINI_METRO_MAX_FRAMES": "1"}), patch(
            "pygame.display.set_mode", return_value=MagicMock()
        ), patch("pygame.time.Clock") as clock_mock, patch(
            "pygame.event.get", return_value=[MagicMock(type=0)]
        ), patch("pygame.display.flip"), patch("pygame.init"), patch(
            "mediator.Mediator"
        ) as mediator_mock, patch(
            "event.convert.convert_pygame_event", return_value=MagicMock()
        ) as convert_mock:
            clock = MagicMock()
            clock.tick.return_value = 16
            clock_mock.return_value = clock

            runpy.run_module("main", run_name="__main__")

            mediator_mock.return_value.increment_time.assert_called_once()
            convert_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

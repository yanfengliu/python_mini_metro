"""GM-08a red contract: main.run_game applies the fullscreen setting (D-029).

The startup ``set_mode`` stays windowed (RESIZABLE); a persisted ``fullscreen``
drives exactly one additional ``set_mode`` with the fullscreen flags, reassigning
the window surface, and it never re-applies while the setting is unchanged.
"""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main
from config import screen_height, screen_width
from settings import DEFAULT_SETTINGS, Settings


def _run(frames: int, settings):
    with (
        patch("main.pygame") as pygame_mock,
        patch("main.Mediator"),
        patch("main.GameSession") as session_mock,
        patch("main.GameRenderer"),
        patch("main.convert_pygame_event"),
        patch("main.read_settings", return_value=settings),
    ):
        pygame_mock.QUIT = 12
        pygame_mock.RESIZABLE = 1
        pygame_mock.FULLSCREEN = 2
        pygame_mock.SCALED = 4
        window = MagicMock()
        window.get_size.return_value = (screen_width, screen_height)
        pygame_mock.display.set_mode.return_value = window
        game_surface = MagicMock()
        game_surface.get_size.return_value = (screen_width, screen_height)
        pygame_mock.Surface.return_value = game_surface
        clock = MagicMock()
        clock.tick.return_value = 17
        pygame_mock.time.Clock.return_value = clock
        pygame_mock.event.get.return_value = []
        session = session_mock.return_value
        session.advance.return_value = SimpleNamespace(alpha=1.0)
        main.run_game(max_frames=frames)
        return pygame_mock.display.set_mode


class TestGM08aFullscreenConsumer(unittest.TestCase):
    def test_windowed_default_calls_set_mode_once(self):
        set_mode = _run(3, DEFAULT_SETTINGS)
        set_mode.assert_called_once_with(
            (screen_width, screen_height),
            1,  # RESIZABLE
        )

    def test_fullscreen_setting_applies_exactly_one_extra_set_mode(self):
        set_mode = _run(3, Settings(fullscreen=True))
        # Startup RESIZABLE, then a single fullscreen application that does not
        # repeat over the remaining frames.
        self.assertEqual(set_mode.call_count, 2, "one startup + one fullscreen apply")
        self.assertEqual(
            set_mode.call_args_list[0],
            call((screen_width, screen_height), 1),
            "startup stays windowed (RESIZABLE)",
        )
        self.assertEqual(
            set_mode.call_args_list[1],
            call((screen_width, screen_height), 2 | 4),
            "fullscreen uses FULLSCREEN | SCALED",
        )


if __name__ == "__main__":
    unittest.main()

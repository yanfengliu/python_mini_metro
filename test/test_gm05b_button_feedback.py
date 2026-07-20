from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from geometry.circle import Circle
from geometry.point import Point
from ui.path_button import (
    INVALID_OUTLINE_COLOR,
    SELECTED_OUTLINE_COLOR,
    PathButton,
)


class TestGM05bButtonFeedback(unittest.TestCase):
    def test_selected_feedback_remains_visible_during_blink_off_phase(self) -> None:
        button = PathButton(Circle((180, 180, 180), 30), Point(60, 60))
        button.assign_path(SimpleNamespace(color=(35, 120, 220)))
        button.start_unlock_blink(0)

        hidden = pygame.Surface((120, 120), pygame.SRCALPHA, 32)
        button.draw(hidden, current_time_ms=200)
        self.assertEqual(hidden.get_bounding_rect().width, 0)

        selected = pygame.Surface((120, 120), pygame.SRCALPHA, 32)
        button.draw(selected, current_time_ms=200, is_selected=True)
        self.assertEqual(selected.get_at((94, 60))[:3], SELECTED_OUTLINE_COLOR)

        invalid = pygame.Surface((120, 120), pygame.SRCALPHA, 32)
        button.draw(invalid, current_time_ms=200, is_selected=True, is_invalid=True)
        self.assertEqual(invalid.get_at((94, 60))[:3], INVALID_OUTLINE_COLOR)


if __name__ == "__main__":
    unittest.main()

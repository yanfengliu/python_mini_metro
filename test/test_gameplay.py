import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width
from entity.get_entity import get_random_airports
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from mediator import Mediator
from utils import get_random_color, get_random_position


class TestMediator(unittest.TestCase):
    def setUp(self):
        self.width, self.height = screen_width, screen_height
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()
        self.mediator = Mediator()
        pygame.draw = MagicMock()
        self.mediator.render(self.screen)

    def connect_airports(self, airport_idx):
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_DOWN,
                self.mediator.airports[airport_idx[0]].position,
            )
        )
        for idx in airport_idx[1:]:
            self.mediator.react(
                MouseEvent(
                    MouseEventType.MOUSE_MOTION, self.mediator.airports[idx].position
                )
            )
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_UP,
                self.mediator.airports[airport_idx[-1]].position,
            )
        )

    def test_react_mouse_down_start_path(self):
        self.mediator.start_path_on_airport = MagicMock()
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_DOWN,
                self.mediator.airports[3].position + Point(1, 1),
            )
        )

        self.mediator.start_path_on_airport.assert_called_once()

    def test_mouse_down_and_up_at_the_same_point_does_not_create_path(self):
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_DOWN, Point(-1, -1)))
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_UP, Point(-1, -1)))

        self.assertEqual(len(self.mediator.paths), 0)

    def test_mouse_dragged_between_airports_creates_path(self):
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_DOWN,
                self.mediator.airports[0].position + Point(1, 1),
            )
        )
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_MOTION, Point(2, 2)))
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_UP,
                self.mediator.airports[1].position + Point(1, 1),
            )
        )

        self.assertEqual(len(self.mediator.paths), 1)
        self.assertSequenceEqual(
            self.mediator.paths[0].airports,
            [self.mediator.airports[0], self.mediator.airports[1]],
        )

    def test_mouse_dragged_between_non_airport_points_does_not_create_path(self):
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_DOWN, Point(0, 0)))
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_MOTION, Point(2, 2)))
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_UP, Point(0, 1)))

        self.assertEqual(len(self.mediator.paths), 0)

    def test_mouse_dragged_between_airport_and_non_airport_points_does_not_create_path(
        self,
    ):
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_DOWN,
                self.mediator.airports[0].position + Point(1, 1),
            )
        )
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_MOTION, Point(2, 2)))
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_UP, Point(0, 1)))

        self.assertEqual(len(self.mediator.paths), 0)

    def test_mouse_dragged_between_3_airports_creates_looped_path(self):
        self.connect_airports([0, 1, 2, 0])

        self.assertEqual(len(self.mediator.paths), 1)
        self.assertTrue(self.mediator.paths[0].is_looped)

    def test_mouse_dragged_between_4_airports_creates_looped_path(self):
        self.connect_airports([0, 1, 2, 3, 0])
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertTrue(self.mediator.paths[0].is_looped)

    def test_path_between_2_airports_is_not_looped(self):
        self.connect_airports([0, 1])
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertFalse(self.mediator.paths[0].is_looped)

    def test_mouse_dragged_between_3_airports_without_coming_back_to_first_does_not_create_loop(
        self,
    ):
        self.connect_airports([0, 1, 2])
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertFalse(self.mediator.paths[0].is_looped)

    def test_space_key_pauses_and_unpauses_game(self):
        self.mediator.react(KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_SPACE))

        self.assertTrue(self.mediator.is_paused)

        self.mediator.react(KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_SPACE))

        self.assertFalse(self.mediator.is_paused)

    def test_path_button_removes_path_on_click(self):
        self.mediator.airports = get_random_airports(5)
        for airport in self.mediator.airports:
            airport.draw(self.screen)
        self.connect_airports([0, 1])
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 0)
        self.assertEqual(len(self.mediator.path_to_button.items()), 0)

    def test_path_buttons_get_assigned_upon_path_creation(self):
        self.mediator.airports = get_random_airports(5)
        for airport in self.mediator.airports:
            airport.draw(self.screen)
        self.connect_airports([0, 1])
        self.assertEqual(len(self.mediator.path_to_button.items()), 1)
        self.assertIn(self.mediator.paths[0], self.mediator.path_to_button)
        self.connect_airports([2, 3])
        self.assertEqual(len(self.mediator.path_to_button.items()), 2)
        self.assertIn(self.mediator.paths[0], self.mediator.path_to_button)
        self.assertIn(self.mediator.paths[1], self.mediator.path_to_button)
        self.connect_airports([1, 3])
        self.assertEqual(len(self.mediator.path_to_button.items()), 3)
        self.assertIn(self.mediator.paths[0], self.mediator.path_to_button)
        self.assertIn(self.mediator.paths[1], self.mediator.path_to_button)
        self.assertIn(self.mediator.paths[2], self.mediator.path_to_button)

    def test_more_paths_can_be_created_after_removing_paths(self):
        self.mediator.airports = get_random_airports(5)
        for airport in self.mediator.airports:
            airport.draw(self.screen)
        self.connect_airports([0, 1])
        self.connect_airports([2, 3])
        self.connect_airports([1, 4])
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 2)
        self.connect_airports([1, 3])
        self.assertEqual(len(self.mediator.paths), 3)

    def test_assigned_path_buttons_bubble_to_left(self):
        self.mediator.airports = get_random_airports(5)
        for airport in self.mediator.airports:
            airport.draw(self.screen)
        self.connect_airports([0, 1])
        self.connect_airports([2, 3])
        self.connect_airports([1, 4])
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 2)
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 1)
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 0)

    def test_unassigned_path_buttons_do_nothing_on_click(self):
        self.assertEqual(len(self.mediator.paths), 0)
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 0)
        self.mediator.react(
            MouseEvent(MouseEventType.MOUSE_UP, self.mediator.path_buttons[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 0)

import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from entity.path import Path
from event import EventType, MouseEvent
from geometry.point import Point
from mediator import Mediator
from utils import get_random_color, get_random_position


class TestMediator(unittest.TestCase):
    def setUp(self):
        self.width, self.height = 640, 480
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()
        self.mediator = Mediator()
        for station in self.mediator.stations:
            station.draw(self.screen)

    def test_singleton(self):
        other = Mediator()
        self.assertEqual(id(self.mediator), id(other))

    def test_react_mouse_down(self):
        for station in self.mediator.stations:
            station.draw(self.screen)
        self.mediator.react(MouseEvent(EventType.MOUSE_DOWN, Point(-1, -1)))
        self.assertTrue(self.mediator.is_mouse_down)

    def test_get_containing_entity(self):
        self.assertTrue(
            self.mediator.get_containing_entity(
                self.mediator.stations[2].position + Point(1, 1)
            )
        )

    def test_react_mouse_down_start_path(self):
        self.mediator.start_path_on_station = MagicMock()
        self.mediator.react(
            MouseEvent(
                EventType.MOUSE_DOWN, self.mediator.stations[3].position + Point(1, 1)
            )
        )
        self.mediator.start_path_on_station.assert_called_once()

    def test_react_mouse_up(self):
        self.mediator.react(MouseEvent(EventType.MOUSE_UP, Point(-1, -1)))
        self.assertFalse(self.mediator.is_mouse_down)

    def test_mouse_down_and_up_at_the_same_point_does_not_create_path(self):
        self.mediator.react(MouseEvent(EventType.MOUSE_DOWN, Point(-1, -1)))
        self.mediator.react(MouseEvent(EventType.MOUSE_UP, Point(-1, -1)))
        self.assertEqual(len(self.mediator.paths), 0)

    def test_mouse_dragged_between_stations_creates_path(self):
        self.mediator.react(
            MouseEvent(
                EventType.MOUSE_DOWN, self.mediator.stations[0].position + Point(1, 1)
            )
        )
        self.mediator.react(MouseEvent(EventType.MOUSE_MOTION, Point(2, 2)))
        self.mediator.react(
            MouseEvent(
                EventType.MOUSE_UP, self.mediator.stations[1].position + Point(1, 1)
            )
        )
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertSequenceEqual(
            self.mediator.paths[0].stations,
            [self.mediator.stations[0], self.mediator.stations[1]],
        )

    def test_mouse_dragged_between_non_station_points_does_not_create_path(self):
        self.mediator.react(MouseEvent(EventType.MOUSE_DOWN, Point(0, 0)))
        self.mediator.react(MouseEvent(EventType.MOUSE_MOTION, Point(2, 2)))
        self.mediator.react(MouseEvent(EventType.MOUSE_UP, Point(0, 1)))
        self.assertEqual(len(self.mediator.paths), 0)

    def test_mouse_dragged_between_station_and_non_station_points_does_not_create_path(
        self,
    ):
        self.mediator.react(
            MouseEvent(
                EventType.MOUSE_DOWN, self.mediator.stations[0].position + Point(1, 1)
            )
        )
        self.mediator.react(MouseEvent(EventType.MOUSE_MOTION, Point(2, 2)))
        self.mediator.react(MouseEvent(EventType.MOUSE_UP, Point(0, 1)))
        self.assertEqual(len(self.mediator.paths), 0)

    def test_mouse_dragged_between_3_stations_creates_looped_path(self):
        self.mediator.react(
            MouseEvent(EventType.MOUSE_DOWN, self.mediator.stations[0].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_MOTION, self.mediator.stations[1].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_MOTION, self.mediator.stations[2].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_UP, self.mediator.stations[0].position)
        )
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertTrue(self.mediator.paths[0].is_looped)

    def test_path_between_2_stations_is_not_looped(self):
        self.mediator.react(
            MouseEvent(EventType.MOUSE_DOWN, self.mediator.stations[0].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_MOTION, self.mediator.stations[1].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_UP, self.mediator.stations[1].position)
        )
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertFalse(self.mediator.paths[0].is_looped)

    def test_mouse_dragged_between_3_stations_without_coming_back_to_first_does_not_create_loop(
        self,
    ):
        self.mediator.react(
            MouseEvent(EventType.MOUSE_DOWN, self.mediator.stations[0].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_MOTION, self.mediator.stations[1].position)
        )
        self.mediator.react(
            MouseEvent(EventType.MOUSE_UP, self.mediator.stations[2].position)
        )
        self.assertEqual(len(self.mediator.paths), 1)
        self.assertFalse(self.mediator.paths[0].is_looped)


if __name__ == "__main__":
    unittest.main()

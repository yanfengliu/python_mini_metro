import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from entity.get_entity import get_random_station, get_random_stations
from entity.path import Path
from geometry.point import Point
from utils import get_random_color, get_random_position


class TestPath(unittest.TestCase):
    def setUp(self):
        self.width, self.height = 640, 480
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()

    def test_init(self):
        path = Path()
        station = get_random_station()
        path.add_station(station)
        self.assertIn(station, path.stations)

    def test_draw(self):
        path = Path()
        stations = get_random_stations(5)
        pygame.draw.line = MagicMock()
        for station in stations:
            path.add_station(station)
        path.draw(self.screen)
        self.assertEqual(pygame.draw.line.call_count, 4)

    def test_draw_temporary_point(self):
        path = Path()
        pygame.draw.line = MagicMock()
        path.add_station(get_random_station())
        path.set_temporary_point(Point(1, 1))
        path.draw(self.screen)
        self.assertEqual(pygame.draw.line.call_count, 1)


if __name__ == "__main__":
    unittest.main()

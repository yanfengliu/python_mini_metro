import os
import sys
import unittest
from math import ceil
from unittest.mock import MagicMock, create_autospec, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import framerate, metro_speed_per_ms
from entity.get_entity import get_random_station, get_random_stations
from entity.metro import Metro
from entity.path import Path
from entity.station import Station
from geometry.point import Point
from utils import get_random_color, get_random_position, get_random_station_shape


class TestPath(unittest.TestCase):
    def setUp(self):
        self.width, self.height = 640, 480
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()

    def test_init(self):
        path = Path(get_random_color())
        station = get_random_station()
        path.add_station(station)

        self.assertIn(station, path.stations)

    def test_draw(self):
        path = Path(get_random_color())
        stations = get_random_stations(5)
        pygame.draw.line = MagicMock()
        for station in stations:
            path.add_station(station)
        path.draw(self.screen, 0)

        self.assertEqual(pygame.draw.line.call_count, 4 + 3)

    def test_draw_temporary_point(self):
        path = Path(get_random_color())
        pygame.draw.line = MagicMock()
        path.add_station(get_random_station())
        path.set_temporary_point(Point(1, 1))
        path.draw(self.screen, 0)

        self.assertEqual(pygame.draw.line.call_count, 1)

    def test_metro_starts_at_beginning_of_first_line(self):
        path = Path(get_random_color())
        path.add_station(get_random_station())
        path.add_station(get_random_station())
        path.draw(self.screen, 0)
        metro = Metro()
        path.add_metro(metro)

        self.assertEqual(metro.current_segment, path.segments[0])
        self.assertEqual(metro.current_segment_idx, 0)
        self.assertTrue(metro.is_forward)

    def test_metro_moves_from_beginning_to_end(self):
        path = Path(get_random_color())
        path.add_station(Station(get_random_station_shape(), Point(0, 0)))
        dist_in_one_sec = 1000 * metro_speed_per_ms
        path.add_station(Station(get_random_station_shape(), Point(dist_in_one_sec, 0)))
        path.draw(self.screen, 0)
        for station in path.stations:
            station.draw(self.screen)
        metro = Metro()
        path.add_metro(metro)
        dt_ms = ceil(1000 / framerate)
        for _ in range(framerate):
            path.move_metro(metro, dt_ms)

        self.assertTrue(path.stations[1].contains(metro.position))

    def test_metro_turns_around_when_it_reaches_the_end(self):
        path = Path(get_random_color())
        path.add_station(Station(get_random_station_shape(), Point(0, 0)))
        dist_in_one_sec = 1000 * metro_speed_per_ms
        path.add_station(Station(get_random_station_shape(), Point(dist_in_one_sec, 0)))
        path.draw(self.screen, 0)
        for station in path.stations:
            station.draw(self.screen)
        metro = Metro()
        path.add_metro(metro)
        dt_ms = ceil(1000 / framerate)
        for _ in range(framerate + 1):
            path.move_metro(metro, dt_ms)

        self.assertFalse(metro.is_forward)

    def test_metro_loops_around_the_path(self):
        path = Path(get_random_color())
        path.add_station(Station(get_random_station_shape(), Point(0, 0)))
        dist_in_one_sec = 1000 * metro_speed_per_ms
        path.add_station(Station(get_random_station_shape(), Point(dist_in_one_sec, 0)))
        path.add_station(
            Station(get_random_station_shape(), Point(dist_in_one_sec, dist_in_one_sec))
        )
        path.add_station(Station(get_random_station_shape(), Point(0, dist_in_one_sec)))
        path.set_loop()
        path.draw(self.screen, 0)
        for station in path.stations:
            station.draw(self.screen)
        metro = Metro()
        path.add_metro(metro)
        dt_ms = ceil(1000 / framerate)
        for station_idx in [1, 2, 3, 0, 1]:
            for _ in range(framerate):
                path.move_metro(metro, dt_ms)

            self.assertTrue(path.stations[station_idx].contains(metro.position))


if __name__ == "__main__":
    unittest.main()

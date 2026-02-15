import os
import sys
import unittest
from math import ceil
from unittest.mock import MagicMock, create_autospec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame
from config import framerate, metro_speed_per_ms, station_color, station_size
from entity.get_entity import get_random_station, get_random_stations
from entity.metro import Metro
from entity.path import Path
from entity.path_segment import PathSegment
from entity.station import Station
from geometry.circle import Circle
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

    def _build_path_with_four_stations(self):
        path = Path((10, 10, 10))
        for idx in range(4):
            station = Station(Circle(station_color, station_size), Point(idx * 10, 0))
            path.add_station(station)
        metro = Metro()
        path.add_metro(metro)
        return path, metro

    def test_path_repr_and_remove_loop(self):
        path, _ = self._build_path_with_four_stations()
        path.set_loop()
        path.remove_loop()
        self.assertFalse(path.is_looped)
        self.assertIn("Path-", repr(path))

    def test_move_metro_last_segment_forward_turns_around(self):
        path, metro = self._build_path_with_four_stations()
        metro.current_segment_idx = len(path.segments) - 1
        metro.current_segment = path.segments[-1]
        metro.is_forward = True
        metro.position = metro.current_segment.segment_start
        path.move_metro(metro, 100000)
        self.assertFalse(metro.is_forward)

    def test_move_metro_last_segment_backward_decrements(self):
        path, metro = self._build_path_with_four_stations()
        metro.current_segment_idx = len(path.segments) - 1
        metro.current_segment = path.segments[-1]
        metro.is_forward = False
        metro.position = metro.current_segment.segment_end
        path.move_metro(metro, 100000)
        self.assertEqual(metro.current_segment_idx, len(path.segments) - 2)

    def test_move_metro_first_segment_backward_sets_forward(self):
        path, metro = self._build_path_with_four_stations()
        metro.current_segment_idx = 0
        metro.current_segment = path.segments[0]
        metro.is_forward = False
        metro.position = metro.current_segment.segment_end
        path.move_metro(metro, 100000)
        self.assertTrue(metro.is_forward)

    def test_move_metro_middle_segment_backward_decrements(self):
        path, metro = self._build_path_with_four_stations()
        metro.current_segment_idx = 1
        metro.current_segment = path.segments[1]
        metro.is_forward = False
        metro.position = metro.current_segment.segment_end
        path.move_metro(metro, 100000)
        self.assertEqual(metro.current_segment_idx, 0)

    def test_move_metro_looped_first_segment_backward_wraps(self):
        path, metro = self._build_path_with_four_stations()
        path.set_loop()
        metro.current_segment_idx = 0
        metro.current_segment = path.segments[0]
        metro.is_forward = False
        metro.position = metro.current_segment.segment_end
        path.move_metro(metro, 100000)
        self.assertEqual(metro.current_segment_idx, len(path.segments) - 1)

    def test_path_segment_keeps_parallel_offsets_for_reversed_station_pair(self):
        station_a = Station(Circle(station_color, station_size), Point(0, 0))
        station_b = Station(Circle(station_color, station_size), Point(100, 40))
        segment_ab = PathSegment((10, 10, 10), station_a, station_b, path_order=2)
        segment_ba = PathSegment((10, 10, 10), station_b, station_a, path_order=2)

        offset_from_a = segment_ab.segment_start - station_a.position
        offset_from_b = segment_ba.segment_start - station_b.position
        self.assertEqual(offset_from_a, offset_from_b)

    def test_move_metro_stops_at_station_when_requested(self):
        path = Path(get_random_color())
        station_a = Station(get_random_station_shape(), Point(0, 0))
        station_b = Station(get_random_station_shape(), Point(200, 0))
        path.add_station(station_a)
        path.add_station(station_b)
        metro = Metro()
        path.add_metro(metro)

        for _ in range(framerate * 3):
            path.move_metro(metro, ceil(1000 / framerate), should_stop_at_next_station=True)
            if metro.current_station is station_b:
                break

        self.assertIs(metro.current_station, station_b)
        self.assertEqual(metro.speed, 0)

    def test_move_metro_handles_short_segments_with_back_to_back_stops(self):
        path = Path(get_random_color())
        station_a = Station(get_random_station_shape(), Point(0, 0))
        station_b = Station(get_random_station_shape(), Point(20, 0))
        station_c = Station(get_random_station_shape(), Point(40, 0))
        path.add_station(station_a)
        path.add_station(station_b)
        path.add_station(station_c)
        metro = Metro()
        path.add_metro(metro)
        metro.speed = 0

        for _ in range(10):
            path.move_metro(metro, 200, should_stop_at_next_station=True)
            if metro.current_station is station_b:
                break

        self.assertIs(metro.current_station, station_b)
        self.assertEqual(metro.speed, 0)

        for _ in range(20):
            path.move_metro(metro, 200, should_stop_at_next_station=True)
            if metro.current_station is station_c:
                break

        self.assertIs(metro.current_station, station_c)
        self.assertEqual(metro.speed, 0)


if __name__ == "__main__":
    unittest.main()

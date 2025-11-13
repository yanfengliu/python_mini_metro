import os
import sys
import unittest
from math import ceil
from unittest.mock import MagicMock, create_autospec, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import framerate, plane_speed_per_ms
from entity.get_entity import get_random_airport, get_random_airports
from entity.plane import plane
from entity.path import Path
from entity.airport import airport
from geometry.point import Point
from utils import get_random_color, get_random_position, get_random_airport_shape


class TestPath(unittest.TestCase):
    def setUp(self):
        self.width, self.height = 640, 480
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()

    def test_init(self):
        path = Path(get_random_color())
        airport = get_random_airport()
        path.add_airport(airport)

        self.assertIn(airport, path.airports)

    def test_draw(self):
        path = Path(get_random_color())
        airports = get_random_airports(5)
        pygame.draw.line = MagicMock()
        for airport in airports:
            path.add_airport(airport)
        path.draw(self.screen, 0)

        self.assertEqual(pygame.draw.line.call_count, 4 + 3)

    def test_draw_temporary_point(self):
        path = Path(get_random_color())
        pygame.draw.line = MagicMock()
        path.add_airport(get_random_airport())
        path.set_temporary_point(Point(1, 1))
        path.draw(self.screen, 0)

        self.assertEqual(pygame.draw.line.call_count, 1)

    def test_plane_starts_at_beginning_of_first_line(self):
        path = Path(get_random_color())
        path.add_airport(get_random_airport())
        path.add_airport(get_random_airport())
        path.draw(self.screen, 0)
        plane = plane()
        path.add_plane(plane)

        self.assertEqual(plane.current_segment, path.segments[0])
        self.assertEqual(plane.current_segment_idx, 0)
        self.assertTrue(plane.is_forward)

    def test_plane_moves_from_beginning_to_end(self):
        path = Path(get_random_color())
        path.add_airport(airport(get_random_airport_shape(), Point(0, 0)))
        dist_in_one_sec = 1000 * plane_speed_per_ms
        path.add_airport(airport(get_random_airport_shape(), Point(dist_in_one_sec, 0)))
        path.draw(self.screen, 0)
        for airport in path.airports:
            airport.draw(self.screen)
        plane = plane()
        path.add_plane(plane)
        dt_ms = ceil(1000 / framerate)
        for _ in range(framerate):
            path.move_plane(plane, dt_ms)

        self.assertTrue(path.airports[1].contains(plane.position))

    def test_plane_turns_around_when_it_reaches_the_end(self):
        path = Path(get_random_color())
        path.add_airport(airport(get_random_airport_shape(), Point(0, 0)))
        dist_in_one_sec = 1000 * plane_speed_per_ms
        path.add_airport(airport(get_random_airport_shape(), Point(dist_in_one_sec, 0)))
        path.draw(self.screen, 0)
        for airport in path.airports:
            airport.draw(self.screen)
        plane = plane()
        path.add_plane(plane)
        dt_ms = ceil(1000 / framerate)
        for _ in range(framerate + 1):
            path.move_plane(plane, dt_ms)

        self.assertFalse(plane.is_forward)

    def test_plane_loops_around_the_path(self):
        path = Path(get_random_color())
        path.add_airport(airport(get_random_airport_shape(), Point(0, 0)))
        dist_in_one_sec = 1000 * plane_speed_per_ms
        path.add_airport(airport(get_random_airport_shape(), Point(dist_in_one_sec, 0)))
        path.add_airport(
            airport(get_random_airport_shape(), Point(dist_in_one_sec, dist_in_one_sec))
        )
        path.add_airport(airport(get_random_airport_shape(), Point(0, dist_in_one_sec)))
        path.set_loop()
        path.draw(self.screen, 0)
        for airport in path.airports:
            airport.draw(self.screen)
        plane = plane()
        path.add_plane(plane)
        dt_ms = ceil(1000 / framerate)
        for airport_idx in [1, 2, 3, 0, 1]:
            for _ in range(framerate):
                path.move_plane(plane, dt_ms)

            self.assertTrue(path.airports[airport_idx].contains(plane.position))


if __name__ == "__main__":
    unittest.main()

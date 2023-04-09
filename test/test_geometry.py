import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from copy import deepcopy

import pygame

from config import screen_height, screen_width
from geometry.circle import Circle
from geometry.line import Line
from geometry.point import Point
from geometry.rect import Rect
from geometry.triangle import Triangle
from utils import get_random_color, get_random_position


class TestGeometry(unittest.TestCase):
    def setUp(self):
        self.width, self.height = screen_width, screen_height
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()
        self.points = [Point(-1, -1), Point(0, 2), Point(2, -1)]
        self.start = get_random_position(self.width, self.height)
        self.end = get_random_position(self.width, self.height)
        self.linewidth = 1

    def test_circle_init(self):
        radius = 1
        circle = Circle(self.color, radius)

        self.assertSequenceEqual(circle.color, self.color)
        self.assertEqual(circle.radius, radius)

    def init_circle(self):
        return Circle(self.color, 1)

    def test_circle_draw(self):
        circle = self.init_circle()
        pygame.draw.circle = MagicMock()
        circle.draw(self.screen, self.position)
        pygame.draw.circle.assert_called_once()

    def test_circle_contains_point(self):
        circle = self.init_circle()
        pygame.draw.circle = MagicMock()
        circle.draw(self.screen, self.position)

        self.assertTrue(
            circle.contains(self.position + Point(circle.radius - 1, circle.radius - 1))
        )
        self.assertFalse(
            circle.contains(self.position + Point(circle.radius + 1, circle.radius + 1))
        )

    def test_rect_init(self):
        width = 2
        height = 3
        rect = Rect(self.color, width, height)

        self.assertSequenceEqual(rect.color, self.color)
        self.assertEqual(rect.width, width)
        self.assertEqual(rect.height, height)

    def init_rect(self):
        return Rect(self.color, 10, 20)

    def test_rect_draw(self):
        rect = self.init_rect()
        pygame.draw.polygon = MagicMock()
        rect.draw(self.screen, self.position)

        pygame.draw.polygon.assert_called_once()

    def test_rect_contains_point(self):
        rect = self.init_rect()
        pygame.draw.polygon = MagicMock()
        rect.draw(self.screen, self.position)

        self.assertTrue(rect.contains(rect.position + Point(1, 1)))
        self.assertFalse(rect.contains(rect.position + Point(rect.width, rect.height)))

    def test_rect_rotate(self):
        rect = self.init_rect()
        pygame.draw.polygon = MagicMock()
        rect.draw(self.screen, self.position)
        rect_points = deepcopy(rect.points)
        rect.rotate(180)
        for point in rect.points:
            self.assertIn(point, rect_points)
        rect.rotate(180)
        self.assertSequenceEqual(rect.points, rect_points)

    def test_rect_set_degrees(self):
        rect = self.init_rect()
        pygame.draw.polygon = MagicMock()
        rect.draw(self.screen, self.position)
        rect_points = deepcopy(rect.points)
        rect.set_degrees(180)
        for point in rect.points:
            self.assertIn(point, rect_points)
        rect.set_degrees(360)
        self.assertSequenceEqual(rect.points, rect_points)

    def test_line_init(self):
        line = Line(self.color, self.start, self.end, self.linewidth)

        self.assertSequenceEqual(line.color, self.color)
        self.assertEqual(line.start, self.start)
        self.assertEqual(line.end, self.end)
        self.assertEqual(line.width, self.linewidth)

    def init_line(self):
        return Line(self.color, self.start, self.end, self.linewidth)

    def test_line_draw(self):
        line = self.init_line()
        pygame.draw.line = MagicMock()
        line.draw(self.screen)

        pygame.draw.line.assert_called_once()

    def test_triangle_init(self):
        size = 10
        triangle = Triangle(self.color, size)

        self.assertSequenceEqual(triangle.color, self.color)
        self.assertEqual(triangle.size, size)

    def init_triangle(self):
        return Triangle(self.color, 10)

    def test_triangle_draw(self):
        triangle = self.init_triangle()
        pygame.draw.polygon = MagicMock()
        triangle.draw(self.screen, self.position)

        pygame.draw.polygon.assert_called_once()


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame
from config import button_color, button_size
from event.convert import convert_pygame_event
from event.type import KeyboardEventType, MouseEventType
from geometry.circle import Circle
from geometry.line import Line
from geometry.point import Point
from geometry.shape import Shape
from geometry.type import ShapeType
from ui.button import Button
from ui.path_button import PathButton, get_path_buttons
from utils import get_random_passenger_shape, tuple_to_point, within_time_window


class PassthroughShape(Shape):
    def __init__(self) -> None:
        super().__init__(ShapeType.RECT, (0, 0, 0))

    def draw(self, surface: pygame.surface.Surface, position: Point) -> None:
        super().draw(surface, position)

    def contains(self, point: Point) -> bool:
        return super().contains(point)

    def rotate(self, degree_diff: float) -> None:
        return super().rotate(degree_diff)

    def set_degrees(self, degree: float) -> None:
        return super().set_degrees(degree)


class PassthroughButton(Button):
    def __init__(self, shape: Shape) -> None:
        super().__init__(shape)
        self.position = Point(0, 0)

    def on_hover(self):
        return super().on_hover()

    def on_exit(self):
        return super().on_exit()

    def on_click(self):
        return super().on_click()


class TestCoverageUtils(unittest.TestCase):
    def setUp(self):
        self.screen = create_autospec(pygame.surface.Surface)

    def test_point_arithmetic_variants(self):
        point = Point(1, 2)
        self.assertIn("Point(", repr(point))
        self.assertEqual(point + 1, Point(2, 3))
        self.assertEqual(1 + point, Point(2, 3))
        self.assertEqual(point - 1, Point(0, 1))
        self.assertEqual(point.__rsub__(Point(5, 6)), Point(4, 4))
        self.assertEqual(5 - point, Point(4, 3))
        self.assertEqual(2 * point, Point(2, 4))

    def test_line_equality_uses_id(self):
        start = Point(0, 0)
        end = Point(1, 1)
        line_a = Line((0, 0, 0), start, end, 1)
        line_b = Line((0, 0, 0), start, end, 1)
        self.assertNotEqual(line_a, line_b)
        line_b.id = line_a.id
        self.assertEqual(line_a, line_b)

    def test_shape_base_methods_execute(self):
        shape = PassthroughShape()
        self.assertIsNone(shape.contains(Point(0, 0)))
        self.assertIsNone(shape.rotate(90))
        self.assertIsNone(shape.set_degrees(45))

    def test_button_abstract_methods_execute(self):
        button = PassthroughButton(PassthroughShape())
        self.assertIsNone(button.on_hover())
        self.assertIsNone(button.on_exit())
        self.assertIsNone(button.on_click())
        self.assertIsNone(button.contains(Point(0, 0)))
        self.assertIsNone(button.draw(self.screen))

    def test_path_button_interactions(self):
        button = PathButton(Circle(button_color, button_size), Point(0, 0))
        button.on_hover()
        self.assertTrue(button.show_cross)
        button.on_exit()
        self.assertFalse(button.show_cross)
        button.on_click()
        self.assertIsNone(button.path)
        self.assertIsNone(button.cross)

    def test_path_button_draws_cross_when_visible(self):
        button = PathButton(Circle(button_color, button_size), Point(0, 0))
        button.assign_path(MagicMock())
        button.on_hover()
        pygame.draw.circle = MagicMock()
        button.cross.draw = MagicMock()
        button.draw(self.screen)
        button.cross.draw.assert_called_once()

    def test_path_button_keeps_assigned_color_when_unlocked(self):
        button = PathButton(Circle(button_color, button_size), Point(0, 0))
        path = MagicMock()
        path.color = (10, 20, 30)
        button.assign_path(path)
        button.set_locked(False)
        self.assertEqual(button.shape.color, path.color)

    def test_get_path_buttons_positions(self):
        buttons = get_path_buttons(2)
        self.assertEqual(len(buttons), 2)

    def test_utils_helpers(self):
        passenger_shape = get_random_passenger_shape()
        self.assertIn(passenger_shape.type, list(ShapeType))
        point = tuple_to_point((3, 4))
        self.assertEqual(point, Point(3, 4))
        self.assertTrue(within_time_window(16, 10, 5))
        self.assertFalse(within_time_window(14, 10, 5))

    def test_convert_pygame_event(self):
        with patch("pygame.mouse.get_pos", return_value=(5, 6)):
            down_event = MagicMock(type=pygame.MOUSEBUTTONDOWN)
            down = convert_pygame_event(down_event)
            self.assertEqual(down.event_type, MouseEventType.MOUSE_DOWN)
            self.assertEqual(down.position, Point(5, 6))

            up_event = MagicMock(type=pygame.MOUSEBUTTONUP)
            up = convert_pygame_event(up_event)
            self.assertEqual(up.event_type, MouseEventType.MOUSE_UP)
            self.assertEqual(up.position, Point(5, 6))

            motion_event = MagicMock(type=pygame.MOUSEMOTION)
            motion = convert_pygame_event(motion_event)
            self.assertEqual(motion.event_type, MouseEventType.MOUSE_MOTION)
            self.assertEqual(motion.position, Point(5, 6))

        key_event = MagicMock(type=pygame.KEYUP, key=pygame.K_SPACE)
        key_up = convert_pygame_event(key_event)
        self.assertEqual(key_up.event_type, KeyboardEventType.KEY_UP)
        self.assertEqual(key_up.key, pygame.K_SPACE)


if __name__ == "__main__":
    unittest.main()

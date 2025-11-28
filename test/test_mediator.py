import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec

from entity.get_entity import get_random_airports
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.triangle import Triangle
from geometry.type import ShapeType

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from math import ceil

import pygame

from config import (
    framerate,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    screen_height,
    screen_width,
    airport_color,
    airport_size,
)
from entity.airport import airport
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from mediator import Mediator
from utils import get_random_color, get_random_position


class TestMediator(unittest.TestCase):
    def setUp(self):
        self.width, self.height = screen_width, screen_height
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()
        self.mediator = Mediator()
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

    def test_react_mouse_down(self):
        for airport in self.mediator.airports:
            airport.draw(self.screen)
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_DOWN, Point(-1, -1)))

        self.assertTrue(self.mediator.is_mouse_down)

    def test_get_containing_entity(self):
        self.assertTrue(
            self.mediator.get_containing_entity(
                self.mediator.airports[2].position + Point(1, 1)
            )
        )

    def test_react_mouse_up(self):
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_UP, Point(-1, -1)))

        self.assertFalse(self.mediator.is_mouse_down)

    def test_passengers_are_added_to_airports(self):
        self.mediator.spawn_passengers()

        self.assertEqual(len(self.mediator.passengers), len(self.mediator.airports))

    def test_is_passenger_spawn_time(self):
        self.mediator.spawn_passengers = MagicMock()
        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.mediator.spawn_passengers.assert_called_once()

        for _ in range(passenger_spawning_interval_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.assertEqual(self.mediator.spawn_passengers.call_count, 2)

    def test_passengers_spawned_at_a_airport_have_a_different_destination(self):
        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        for airport in self.mediator.airports:
            for passenger in airport.passengers:
                self.assertNotEqual(
                    passenger.destination_shape.type, airport.shape.type
                )

    def test_passengers_at_connected_airports_have_a_way_to_destination(self):
        self.mediator.airports = [
            airport(
                Rect(
                    color=airport_color,
                    width=2 * airport_size,
                    height=2 * airport_size,
                ),
                Point(100, 100),
            ),
            airport(
                Circle(
                    color=airport_color,
                    radius=airport_size,
                ),
                Point(100, 200),
            ),
        ]
        # Need to draw airports if you want to override them
        for airport in self.mediator.airports:
            airport.draw(self.screen)

        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.connect_airports([0, 1])
        self.mediator.increment_time(ceil(1000 / framerate))

        for passenger in self.mediator.passengers:
            self.assertIn(passenger, self.mediator.travel_plans)
            self.assertIsNotNone(self.mediator.travel_plans[passenger])
            self.assertIsNotNone(self.mediator.travel_plans[passenger].next_path)
            self.assertIsNotNone(self.mediator.travel_plans[passenger].next_airport)

    def test_passengers_at_isolated_airports_have_no_way_to_destination(self):
        # Run the game until first wave of passengers spawn, then 1 more frame
        for _ in range(passenger_spawning_start_step + 1):
            self.mediator.increment_time(ceil(1000 / framerate))

        for passenger in self.mediator.passengers:
            self.assertIn(passenger, self.mediator.travel_plans)
            self.assertIsNotNone(self.mediator.travel_plans[passenger])
            self.assertIsNone(self.mediator.travel_plans[passenger].next_path)
            self.assertIsNone(self.mediator.travel_plans[passenger].next_airport)

    def test_get_airport_for_shape_type(self):
        self.mediator.airports = [
            airport(
                Rect(
                    color=airport_color,
                    width=2 * airport_size,
                    height=2 * airport_size,
                ),
                get_random_position(self.width, self.height),
            ),
            airport(
                Circle(
                    color=airport_color,
                    radius=airport_size,
                ),
                get_random_position(self.width, self.height),
            ),
            airport(
                Circle(
                    color=airport_color,
                    radius=airport_size,
                ),
                get_random_position(self.width, self.height),
            ),
            airport(
                Triangle(
                    color=airport_color,
                    size=airport_size,
                ),
                get_random_position(self.width, self.height),
            ),
            airport(
                Triangle(
                    color=airport_color,
                    size=airport_size,
                ),
                get_random_position(self.width, self.height),
            ),
            airport(
                Triangle(
                    color=airport_color,
                    size=airport_size,
                ),
                get_random_position(self.width, self.height),
            ),
        ]
        rect_airports = self.mediator.get_airports_for_shape_type(ShapeType.RECT)
        circle_airports = self.mediator.get_airports_for_shape_type(ShapeType.CIRCLE)
        triangle_airports = self.mediator.get_airports_for_shape_type(
            ShapeType.TRIANGLE
        )

        self.assertCountEqual(rect_airports, self.mediator.airports[0:1])
        self.assertCountEqual(circle_airports, self.mediator.airports[1:3])
        self.assertCountEqual(triangle_airports, self.mediator.airports[3:])

    def test_skip_airports_on_same_path(self):
        self.mediator.airports = get_random_airports(5)
        for airport in self.mediator.airports:
            airport.draw(self.screen)
        self.connect_airports([i for i in range(5)])
        self.mediator.spawn_passengers()
        self.mediator.find_travel_plan_for_passengers()
        for airport in self.mediator.airports:
            for passenger in airport.passengers:
                self.assertEqual(
                    len(self.mediator.travel_plans[passenger].node_path), 1
                )


if __name__ == "__main__":
    unittest.main()

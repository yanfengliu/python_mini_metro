import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec

from entity.get_entity import get_random_stations
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
    station_color,
    station_size,
)
from entity.station import Station
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

    def connect_stations(self, station_idx):
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_DOWN,
                self.mediator.stations[station_idx[0]].position,
            )
        )
        for idx in station_idx[1:]:
            self.mediator.react(
                MouseEvent(
                    MouseEventType.MOUSE_MOTION, self.mediator.stations[idx].position
                )
            )
        self.mediator.react(
            MouseEvent(
                MouseEventType.MOUSE_UP,
                self.mediator.stations[station_idx[-1]].position,
            )
        )

    def test_react_mouse_down(self):
        for station in self.mediator.stations:
            station.draw(self.screen)
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_DOWN, Point(-1, -1)))

        self.assertTrue(self.mediator.is_mouse_down)

    def test_get_containing_entity(self):
        self.assertTrue(
            self.mediator.get_containing_entity(
                self.mediator.stations[2].position + Point(1, 1)
            )
        )

    def test_react_mouse_up(self):
        self.mediator.react(MouseEvent(MouseEventType.MOUSE_UP, Point(-1, -1)))

        self.assertFalse(self.mediator.is_mouse_down)

    def test_passengers_are_added_to_stations(self):
        self.mediator.spawn_passengers()

        self.assertEqual(len(self.mediator.passengers), len(self.mediator.stations))

    def test_is_passenger_spawn_time(self):
        self.mediator.spawn_passengers = MagicMock()
        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.mediator.spawn_passengers.assert_called_once()

        for _ in range(passenger_spawning_interval_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.assertEqual(self.mediator.spawn_passengers.call_count, 2)

    def test_passengers_spawned_at_a_station_have_a_different_destination(self):
        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        for station in self.mediator.stations:
            for passenger in station.passengers:
                self.assertNotEqual(
                    passenger.destination_shape.type, station.shape.type
                )

    def test_passengers_at_connected_stations_have_a_way_to_destination(self):
        self.mediator.stations = [
            Station(
                Rect(
                    color=station_color,
                    width=2 * station_size,
                    height=2 * station_size,
                ),
                Point(100, 100),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                Point(100, 200),
            ),
        ]
        # Need to draw stations if you want to override them
        for station in self.mediator.stations:
            station.draw(self.screen)

        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.connect_stations([0, 1])
        self.mediator.increment_time(ceil(1000 / framerate))

        for passenger in self.mediator.passengers:
            self.assertIn(passenger, self.mediator.travel_plans)
            self.assertIsNotNone(self.mediator.travel_plans[passenger])
            self.assertIsNotNone(self.mediator.travel_plans[passenger].next_path)
            self.assertIsNotNone(self.mediator.travel_plans[passenger].next_station)

    def test_passengers_at_isolated_stations_have_no_way_to_destination(self):
        # Run the game until first wave of passengers spawn, then 1 more frame
        for _ in range(passenger_spawning_start_step + 1):
            self.mediator.increment_time(ceil(1000 / framerate))

        for passenger in self.mediator.passengers:
            self.assertIn(passenger, self.mediator.travel_plans)
            self.assertIsNotNone(self.mediator.travel_plans[passenger])
            self.assertIsNone(self.mediator.travel_plans[passenger].next_path)
            self.assertIsNone(self.mediator.travel_plans[passenger].next_station)

    def test_get_station_for_shape_type(self):
        self.mediator.stations = [
            Station(
                Rect(
                    color=station_color,
                    width=2 * station_size,
                    height=2 * station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Triangle(
                    color=station_color,
                    size=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Triangle(
                    color=station_color,
                    size=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Triangle(
                    color=station_color,
                    size=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
        ]
        rect_stations = self.mediator.get_stations_for_shape_type(ShapeType.RECT)
        circle_stations = self.mediator.get_stations_for_shape_type(ShapeType.CIRCLE)
        triangle_stations = self.mediator.get_stations_for_shape_type(
            ShapeType.TRIANGLE
        )

        self.assertCountEqual(rect_stations, self.mediator.stations[0:1])
        self.assertCountEqual(circle_stations, self.mediator.stations[1:3])
        self.assertCountEqual(triangle_stations, self.mediator.stations[3:])

    def test_skip_stations_on_same_path(self):
        self.mediator.stations = get_random_stations(5)
        for station in self.mediator.stations:
            station.draw(self.screen)
        self.connect_stations([i for i in range(5)])
        self.mediator.spawn_passengers()
        self.mediator.find_travel_plan_for_passengers()
        for station in self.mediator.stations:
            for passenger in station.passengers:
                self.assertEqual(
                    len(self.mediator.travel_plans[passenger].node_path), 1
                )


if __name__ == "__main__":
    unittest.main()

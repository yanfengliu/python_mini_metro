import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame
from config import (
    passenger_display_buffer,
    passenger_max_wait_time_ms,
    passenger_size,
    station_color,
    station_size,
)
from entity.get_entity import get_metros
from entity.metro import Metro
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from graph.node import Node
from travel_plan import TravelPlan
from utils import get_random_position, get_random_station_shape


class TestStation(unittest.TestCase):
    def setUp(self) -> None:
        self.position = get_random_position(width=100, height=100)
        self.shape = get_random_station_shape()
        self.screen = create_autospec(pygame.surface.Surface)

    def test_init(self):
        station = Station(self.shape, self.position)

        self.assertEqual(station.shape, self.shape)
        self.assertEqual(station.position, self.position)

    def test_get_metros_count(self):
        metros = get_metros(3)
        self.assertEqual(len(metros), 3)
        self.assertTrue(all(isinstance(metro, Metro) for metro in metros))

    def test_passenger_repr_and_draw(self):
        shape = Circle((0, 0, 0), 3)
        passenger = Passenger(shape)
        self.assertIn(str(shape.type), repr(passenger))
        shape.draw = MagicMock()
        passenger.draw(self.screen)
        shape.draw.assert_called_once()

    def test_holder_draw_positions_and_move(self):
        station = Station(Circle(station_color, station_size), Point(100, 100))
        self.assertIn("Station-", repr(station))
        passengers = [Passenger(Circle((0, 0, 0), 1)) for _ in range(5)]
        for passenger in passengers:
            passenger.draw = MagicMock()
            station.add_passenger(passenger)

        pygame.draw.circle = MagicMock()
        station.draw(self.screen)

        base_offset = Point(
            (-2 * passenger_size - passenger_display_buffer),
            1.5 * station.size,
        )
        self.assertEqual(passengers[0].position, station.position + base_offset)
        self.assertEqual(
            passengers[4].position,
            station.position
            + base_offset
            + Point(0, passenger_size + passenger_display_buffer),
        )

        station.remove_passenger(passengers[0])
        self.assertNotIn(passengers[0], station.passengers)

        other_station = Station(Circle(station_color, station_size), Point(200, 100))
        station.move_passenger(passengers[1], other_station)
        self.assertNotIn(passengers[1], station.passengers)
        self.assertIn(passengers[1], other_station.passengers)

    def test_travel_plan_methods(self):
        station = Station(Rect(station_color, station_size, station_size), Point(0, 0))
        plan = TravelPlan([Node(station)])
        self.assertEqual(plan.get_next_station(), station)
        plan.increment_next_station()
        self.assertIn("TravelPlan", repr(plan))
        empty_plan = TravelPlan([])
        self.assertIsNone(empty_plan.get_next_station())

    def test_station_unlock_blink_hides_shape_during_off_phase(self):
        station = Station(Circle(station_color, station_size), Point(0, 0))
        station.shape.draw = MagicMock()
        station.start_unlock_blink(0)

        station.draw(self.screen, current_time_ms=0)
        station.shape.draw.assert_called_once()

        station.shape.draw.reset_mock()
        station.draw(self.screen, current_time_ms=200)
        station.shape.draw.assert_not_called()

    def test_station_draw_hides_warning_passenger_during_off_phase(self):
        station = Station(Circle(station_color, station_size), Point(0, 0))
        passenger = Passenger(Circle((0, 0, 0), 3))
        passenger.wait_ms = passenger_max_wait_time_ms - 5_000
        station.add_passenger(passenger)
        passenger.destination_shape.draw = MagicMock()

        station.draw(
            self.screen,
            current_time_ms=0,
            passenger_max_wait_time_ms=passenger_max_wait_time_ms,
        )
        passenger.destination_shape.draw.assert_called_once()

        passenger.destination_shape.draw.reset_mock()
        station.draw(
            self.screen,
            current_time_ms=250,
            passenger_max_wait_time_ms=passenger_max_wait_time_ms,
        )
        passenger.destination_shape.draw.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from passenger import Passenger
from station import Station
from utils import (
    get_random_passenger_shape,
    get_random_position,
    get_random_station_shape,
)


class TestStation(unittest.TestCase):
    def test_init(self):
        position = get_random_position(width=100, height=100)
        shape = get_random_station_shape()
        station = Station(shape, position)
        self.assertEqual(station.shape, shape)
        self.assertEqual(station.position, position)

    def setup_station(self):
        position = get_random_position(width=100, height=100)
        shape = get_random_station_shape()
        return Station(shape, position)

    def setup_passenger(self):
        return Passenger(shape=get_random_passenger_shape())

    def test_empty_station_has_capacity(self):
        station = self.setup_station()
        self.assertTrue(station.has_room())

    def test_half_full_station_has_capacity(self):
        station = self.setup_station()
        for i in range(5):
            passenger = self.setup_passenger()
            station.add_passenger(passenger)
        self.assertTrue(station.has_room())

    def test_full_station_does_not_have_capacity(self):
        station = self.setup_station()
        for i in range(station.capacity):
            passenger = self.setup_passenger()
            station.add_passenger(passenger)
        self.assertFalse(station.has_room())

    def test_full_station_raises_error_when_adding_passenger(self):
        station = self.setup_station()
        for i in range(station.capacity):
            passenger = self.setup_passenger()
            station.add_passenger(passenger)
        with self.assertRaises(RuntimeError):
            passenger = self.setup_passenger()
            station.add_passenger(passenger)

    def test_station_can_remove_passenger(self):
        station = self.setup_station()
        passenger = self.setup_passenger()
        station.add_passenger(passenger)
        station.remove_passenger(passenger)
        self.assertEqual(len(station.passengers), 0)

    def test_station_cannot_remove_invalid_passenger(self):
        station = self.setup_station()
        passenger_0 = self.setup_passenger()
        passenger_1 = self.setup_passenger()
        station.add_passenger(passenger_0)
        with self.assertRaises(LookupError):
            station.remove_passenger(passenger_1)


if __name__ == "__main__":
    unittest.main()

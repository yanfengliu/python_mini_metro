import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.station import Station
from utils import get_random_position, get_random_station_shape


class TestStation(unittest.TestCase):
    def setUp(self) -> None:
        self.position = get_random_position(width=100, height=100)
        self.shape = get_random_station_shape()

    def test_init(self):
        station = Station(self.shape, self.position)

        self.assertEqual(station.shape, self.shape)
        self.assertEqual(station.position, self.position)


if __name__ == "__main__":
    unittest.main()

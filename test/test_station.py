import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.station import Station
from utils import get_random_position, get_random_station_shape


class TestStation(unittest.TestCase):
    def test_init(self):
        position = get_random_position(width=100, height=100)
        shape = get_random_station_shape()
        station = Station(shape, position)
        self.assertEqual(station.shape, shape)
        self.assertEqual(station.position, position)


if __name__ == "__main__":
    unittest.main()

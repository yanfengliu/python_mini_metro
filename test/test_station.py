import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.airport import airport
from utils import get_random_position, get_random_airport_shape


class Testairport(unittest.TestCase):
    def setUp(self) -> None:
        self.position = get_random_position(width=100, height=100)
        self.shape = get_random_airport_shape()

    def test_init(self):
        airport = airport(self.shape, self.position)

        self.assertEqual(airport.shape, self.shape)
        self.assertEqual(airport.position, self.position)


if __name__ == "__main__":
    unittest.main()

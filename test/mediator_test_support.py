import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width, station_color, station_size
from entity.metro import Metro
from entity.path import Path
from entity.station import Station
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from mediator import Mediator
from utils import get_random_color, get_random_position


class MediatorTestCase(unittest.TestCase):
    def setUp(self):
        self.width, self.height = screen_width, screen_height
        self.screen = MagicMock()
        self.screen.get_width.return_value = self.width
        self.screen.get_height.return_value = self.height
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()
        self.mediator = Mediator()
        original_draw = pygame.draw
        self.addCleanup(setattr, pygame, "draw", original_draw)
        pygame.draw = MagicMock()
        self.mediator.prepare_layout(self.width, self.height)

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

    def _build_two_station_mediator(self):
        mediator = Mediator()
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(10, 0))
        mediator.stations = [station_a, station_b]
        path = Path((10, 20, 30))
        path.add_station(station_a)
        path.add_station(station_b)
        metro = Metro()
        path.add_metro(metro)
        mediator.paths = [path]
        mediator.metros = [metro]
        metro.current_station = station_a
        return mediator, station_a, station_b, path, metro

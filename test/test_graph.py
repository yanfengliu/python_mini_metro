import os
import sys
import unittest
from unittest.mock import create_autospec

from entity.get_entity import get_random_stations

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame
from config import screen_height, screen_width, station_color, station_size
from entity.path import Path
from entity.station import Station
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from graph.graph_algo import bfs, build_station_nodes_dict
from graph.node import Node
from mediator import Mediator
from utils import get_random_color, get_random_position


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.width, self.height = screen_width, screen_height
        self.screen = create_autospec(pygame.surface.Surface)
        self.position = get_random_position(self.width, self.height)
        self.color = get_random_color()
        self.mediator = Mediator()
        for station in self.mediator.stations:
            station.draw(self.screen)

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

    def test_build_station_nodes_dict(self):
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
        ]
        for station in self.mediator.stations:
            station.draw(self.screen)

        self.connect_stations([0, 1])

        station_nodes_dict = build_station_nodes_dict(
            self.mediator.stations, self.mediator.paths
        )
        self.assertCountEqual(list(station_nodes_dict.keys()), self.mediator.stations)
        for station, node in station_nodes_dict.items():
            self.assertEqual(node.station, station)

    def test_bfs_two_stations(self):
        self.mediator.stations = get_random_stations(2)
        for station in self.mediator.stations:
            station.draw(self.screen)

        self.connect_stations([0, 1])

        station_nodes_dict = build_station_nodes_dict(
            self.mediator.stations, self.mediator.paths
        )
        start_station = self.mediator.stations[0]
        end_station = self.mediator.stations[1]
        start_node = station_nodes_dict[start_station]
        end_node = station_nodes_dict[end_station]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [start_node, end_node],
        )

    def test_bfs_five_stations(self):
        self.mediator.stations = get_random_stations(5)
        for station in self.mediator.stations:
            station.draw(self.screen)

        self.connect_stations([0, 1, 2])
        self.mediator.total_travels_handled = 90
        self.mediator.update_unlocked_num_paths()
        self.connect_stations([0, 3])

        station_nodes_dict = build_station_nodes_dict(
            self.mediator.stations, self.mediator.paths
        )
        start_node = station_nodes_dict[self.mediator.stations[0]]
        end_node = station_nodes_dict[self.mediator.stations[2]]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [
                Node(self.mediator.stations[0]),
                Node(self.mediator.stations[1]),
                Node(self.mediator.stations[2]),
            ],
        )
        start_node = station_nodes_dict[self.mediator.stations[1]]
        end_node = station_nodes_dict[self.mediator.stations[3]]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [
                Node(self.mediator.stations[1]),
                Node(self.mediator.stations[0]),
                Node(self.mediator.stations[3]),
            ],
        )
        start_node = station_nodes_dict[self.mediator.stations[0]]
        end_node = station_nodes_dict[self.mediator.stations[4]]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [],
        )

    def test_node_repr(self):
        station = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        node = Node(station)
        self.assertIn("Node-", repr(node))

    def test_build_station_nodes_dict_skips_being_created_paths(self):
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(10, 0))
        path = Path((0, 0, 0))
        path.is_being_created = True
        path.add_station(station_a)
        path.add_station(station_b)

        station_nodes = build_station_nodes_dict([station_a, station_b], [path])
        for node in station_nodes.values():
            self.assertEqual(node.paths, set())


if __name__ == "__main__":
    unittest.main()

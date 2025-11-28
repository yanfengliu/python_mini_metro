import os
import sys
import unittest
from unittest.mock import create_autospec

from entity.get_entity import get_random_airports

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width, airport_color, airport_size
from entity.airport import airport
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.circle import Circle
from geometry.rect import Rect
from graph.graph_algo import bfs, build_airport_nodes_dict
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
        for airport in self.mediator.airports:
            airport.draw(self.screen)

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

    def test_build_airport_nodes_dict(self):
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
        ]
        for airport in self.mediator.airports:
            airport.draw(self.screen)

        self.connect_airports([0, 1])

        airport_nodes_dict = build_airport_nodes_dict(
            self.mediator.airports, self.mediator.paths
        )
        self.assertCountEqual(list(airport_nodes_dict.keys()), self.mediator.airports)
        for airport, node in airport_nodes_dict.items():
            self.assertEqual(node.airport, airport)

    def test_bfs_two_airports(self):
        self.mediator.airports = get_random_airports(2)
        for airport in self.mediator.airports:
            airport.draw(self.screen)

        self.connect_airports([0, 1])

        airport_nodes_dict = build_airport_nodes_dict(
            self.mediator.airports, self.mediator.paths
        )
        start_airport = self.mediator.airports[0]
        end_airport = self.mediator.airports[1]
        start_node = airport_nodes_dict[start_airport]
        end_node = airport_nodes_dict[end_airport]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [start_node, end_node],
        )

    def test_bfs_five_airports(self):
        self.mediator.airports = get_random_airports(5)
        for airport in self.mediator.airports:
            airport.draw(self.screen)

        self.connect_airports([0, 1, 2])
        self.connect_airports([0, 3])

        airport_nodes_dict = build_airport_nodes_dict(
            self.mediator.airports, self.mediator.paths
        )
        start_node = airport_nodes_dict[self.mediator.airports[0]]
        end_node = airport_nodes_dict[self.mediator.airports[2]]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [
                Node(self.mediator.airports[0]),
                Node(self.mediator.airports[1]),
                Node(self.mediator.airports[2]),
            ],
        )
        start_node = airport_nodes_dict[self.mediator.airports[1]]
        end_node = airport_nodes_dict[self.mediator.airports[3]]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [
                Node(self.mediator.airports[1]),
                Node(self.mediator.airports[0]),
                Node(self.mediator.airports[3]),
            ],
        )
        start_node = airport_nodes_dict[self.mediator.airports[0]]
        end_node = airport_nodes_dict[self.mediator.airports[4]]
        node_path = bfs(start_node, end_node)
        self.assertSequenceEqual(
            node_path,
            [],
        )


if __name__ == "__main__":
    unittest.main()

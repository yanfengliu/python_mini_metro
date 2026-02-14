import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec, patch

from entity.get_entity import get_random_stations
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.triangle import Triangle
from geometry.type import ShapeType

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from math import ceil

import pygame
from config import (
    button_color,
    framerate,
    initial_num_stations,
    num_stations,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    screen_height,
    screen_width,
    station_unlock_milestones,
    station_color,
    station_size,
)
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from graph.node import Node
from mediator import Mediator
from travel_plan import TravelPlan
from ui.button import Button
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

    def test_render_draws_paths_and_metros(self):
        mediator, _, _, path, metro = self._build_two_station_mediator()
        pygame.draw.line = MagicMock()
        pygame.draw.circle = MagicMock()
        pygame.draw.polygon = MagicMock()
        mediator.render(self.screen)
        self.assertIn(metro, mediator.metros)
        self.assertIn(path, mediator.paths)

    def test_render_single_path_uses_zero_centered_offset(self):
        mediator, _, _, path, _ = self._build_two_station_mediator()
        mediator.stations = []
        mediator.metros = []
        mediator.buttons = []
        path.draw = MagicMock()

        mediator.render(self.screen)

        path.draw.assert_called_once_with(self.screen, 0)

    def test_render_three_paths_uses_centered_offsets(self):
        mediator = Mediator()
        mediator.stations = []
        mediator.metros = []
        mediator.buttons = []
        path_a = MagicMock()
        path_b = MagicMock()
        path_c = MagicMock()
        mediator.paths = [path_a, path_b, path_c]

        mediator.render(self.screen)

        path_a.draw.assert_called_once_with(self.screen, -1)
        path_b.draw.assert_called_once_with(self.screen, 0)
        path_c.draw.assert_called_once_with(self.screen, 1)

    def test_render_game_over_overlay(self):
        mediator = Mediator()
        mediator.paths = []
        mediator.stations = []
        mediator.metros = []
        mediator.buttons = []
        mediator.is_game_over = True
        screen = MagicMock()
        overlay = MagicMock()
        with patch("mediator.pygame.Surface", return_value=overlay) as surface_mock:
            title_surface = MagicMock()
            title_surface.get_rect.return_value = MagicMock()
            score_surface = MagicMock()
            score_surface.get_rect.return_value = MagicMock()
            hint_surface = MagicMock()
            hint_surface.get_rect.return_value = MagicMock()
            hint_surface.get_width.return_value = 100
            hint_surface.get_height.return_value = 20
            mediator.game_over_font = MagicMock()
            mediator.game_over_font.render = MagicMock(return_value=title_surface)
            mediator.font = MagicMock()
            mediator.font.render = MagicMock(return_value=score_surface)
            mediator.game_over_hint_font = MagicMock()
            mediator.game_over_hint_font.render = MagicMock(return_value=hint_surface)
            mediator.render(screen)

        surface_mock.assert_called_once()
        overlay.fill.assert_called_once()
        screen.blit.assert_any_call(overlay, (0, 0))
        self.assertGreaterEqual(mediator.font.render.call_count, 1)
        mediator.game_over_font.render.assert_called_once()
        self.assertGreaterEqual(mediator.game_over_hint_font.render.call_count, 2)

    def test_handle_game_over_click(self):
        mediator = Mediator()
        mediator.is_game_over = True
        mediator.game_over_restart_rect = pygame.Rect(0, 0, 10, 10)
        mediator.game_over_exit_rect = pygame.Rect(20, 0, 10, 10)

        self.assertEqual(
            mediator.handle_game_over_click(Point(5, 5)), "restart"
        )
        self.assertEqual(
            mediator.handle_game_over_click(Point(25, 5)), "exit"
        )
        self.assertIsNone(mediator.handle_game_over_click(Point(50, 50)))

    def test_mouse_motion_no_entity_triggers_exit(self):
        mediator = Mediator()
        mediator.stations = []
        button = MagicMock()
        button.contains = MagicMock(return_value=False)
        mediator.buttons = [button]
        mediator.react_mouse_event(
            MouseEvent(MouseEventType.MOUSE_MOTION, Point(-1000, -1000))
        )
        button.on_exit.assert_called_once()

    def test_mouse_motion_over_button_triggers_hover(self):
        mediator = Mediator()
        mediator.stations = []

        class HoverButton(Button):
            def __init__(self):
                super().__init__(Circle(station_color, station_size))
                self.position = Point(0, 0)
                self.hovered = False

            def contains(self, point: Point) -> bool:
                return True

            def on_hover(self):
                self.hovered = True

            def on_exit(self):
                pass

            def on_click(self):
                pass

        button = HoverButton()
        mediator.buttons = [button]
        mediator.react_mouse_event(
            MouseEvent(MouseEventType.MOUSE_MOTION, Point(0, 0))
        )
        self.assertTrue(button.hovered)

    def test_remove_path_cleans_passengers(self):
        mediator, _, station_b, path, metro = self._build_two_station_mediator()
        passenger = Passenger(station_b.shape)
        metro.add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.path_buttons[0].assign_path(path)
        mediator.path_to_button[path] = mediator.path_buttons[0]
        mediator.path_to_color[path] = path.color
        mediator.remove_path(path)
        self.assertNotIn(passenger, mediator.passengers)
        self.assertNotIn(path, mediator.paths)

    def test_add_station_to_path_returns_on_duplicate(self):
        mediator = Mediator()
        station = mediator.stations[0]
        path = Path((0, 0, 0))
        path.add_station(station)
        mediator.path_being_created = path
        mediator.is_creating_path = True
        mediator.add_station_to_path(station)
        self.assertEqual(len(path.stations), 1)

    def test_add_station_to_path_removes_loop(self):
        mediator = Mediator()
        station_a = mediator.stations[0]
        station_b = mediator.stations[1]
        station_c = mediator.stations[2]
        path = Path((0, 0, 0))
        path.add_station(station_a)
        path.add_station(station_b)
        path.set_loop()
        mediator.path_being_created = path
        mediator.is_creating_path = True
        mediator.add_station_to_path(station_c)
        self.assertFalse(path.is_looped)

    def test_end_path_on_station_aborts(self):
        mediator = Mediator()
        station = mediator.stations[0]
        mediator.start_path_on_station(station)
        mediator.end_path_on_station(station)
        self.assertFalse(mediator.is_creating_path)
        self.assertIsNone(mediator.path_being_created)
        self.assertEqual(len(mediator.paths), 0)

    def test_increment_time_paused(self):
        mediator = Mediator()
        mediator.is_paused = True
        mediator.time_ms = 10
        mediator.steps = 5
        mediator.increment_time(100)
        self.assertEqual(mediator.time_ms, 10)
        self.assertEqual(mediator.steps, 5)

    def test_move_passengers_covers_all_transfers(self):
        mediator, station_a, station_b, path, metro = self._build_two_station_mediator()

        passenger_at_destination = Passenger(station_a.shape)
        passenger_to_station = Passenger(station_b.shape)
        passenger_to_metro = Passenger(station_b.shape)

        metro.add_passenger(passenger_at_destination)
        metro.add_passenger(passenger_to_station)
        station_a.add_passenger(passenger_to_metro)
        mediator.passengers.extend(
            [passenger_at_destination, passenger_to_station, passenger_to_metro]
        )

        mediator.travel_plans[passenger_at_destination] = TravelPlan([Node(station_a)])
        mediator.travel_plans[passenger_to_station] = TravelPlan(
            [Node(station_a), Node(station_b)]
        )
        mediator.travel_plans[passenger_to_metro] = TravelPlan([Node(station_b)])
        mediator.travel_plans[passenger_to_metro].next_path = path

        self.assertEqual(mediator.total_travels_handled, 0)
        mediator.move_passengers()

        self.assertNotIn(passenger_at_destination, mediator.passengers)
        self.assertTrue(passenger_at_destination.is_at_destination)
        self.assertNotIn(passenger_at_destination, mediator.travel_plans)
        self.assertEqual(mediator.score, 1)
        self.assertEqual(mediator.total_travels_handled, 1)

        self.assertIn(passenger_to_station, station_a.passengers)
        self.assertNotIn(passenger_to_station, metro.passengers)
        self.assertEqual(mediator.travel_plans[passenger_to_station].next_path, path)

        self.assertIn(passenger_to_metro, metro.passengers)
        self.assertNotIn(passenger_to_metro, station_a.passengers)

    def test_move_passengers_increments_total_travels_per_delivery(self):
        mediator, station_a, _, _, metro = self._build_two_station_mediator()

        passenger_one = Passenger(station_a.shape)
        passenger_two = Passenger(station_a.shape)
        metro.add_passenger(passenger_one)
        metro.add_passenger(passenger_two)
        mediator.passengers.extend([passenger_one, passenger_two])
        mediator.travel_plans[passenger_one] = TravelPlan([Node(station_a)])
        mediator.travel_plans[passenger_two] = TravelPlan([Node(station_a)])

        self.assertEqual(mediator.total_travels_handled, 0)
        mediator.move_passengers()

        self.assertEqual(mediator.score, 2)
        self.assertEqual(mediator.total_travels_handled, 2)

    def test_initial_path_button_locks_match_unlocked_lines(self):
        mediator = Mediator()
        self.assertEqual(mediator.unlocked_num_paths, 1)
        self.assertFalse(mediator.path_buttons[0].is_locked)
        for button in mediator.path_buttons[1:]:
            self.assertTrue(button.is_locked)
            self.assertEqual(button.shape.color, button_color)

    def test_update_unlocked_paths_updates_button_locks(self):
        mediator = Mediator()
        mediator.total_travels_handled = 100
        mediator.update_unlocked_num_paths()
        self.assertEqual(mediator.unlocked_num_paths, 2)
        self.assertFalse(mediator.path_buttons[0].is_locked)
        self.assertFalse(mediator.path_buttons[1].is_locked)
        for button in mediator.path_buttons[2:]:
            self.assertTrue(button.is_locked)

    def test_initial_station_unlock_state(self):
        mediator = Mediator()
        self.assertEqual(mediator.unlocked_num_stations, initial_num_stations)
        self.assertEqual(len(mediator.stations), initial_num_stations)

    def test_station_unlock_progression_uses_travel_thresholds(self):
        mediator = Mediator()
        self.assertEqual(station_unlock_milestones[:5], [30, 80, 150, 240, 350])

        mediator.total_travels_handled = 29
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, 3)
        self.assertEqual(len(mediator.stations), 3)

        mediator.total_travels_handled = 30
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, 4)
        self.assertEqual(len(mediator.stations), 4)

        mediator.total_travels_handled = 80
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, 5)
        self.assertEqual(len(mediator.stations), 5)

        mediator.total_travels_handled = station_unlock_milestones[-1]
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, num_stations)
        self.assertEqual(len(mediator.stations), num_stations)

    def test_find_shared_path_returns_none(self):
        mediator = Mediator()
        station_a = mediator.stations[0]
        station_b = mediator.stations[1]
        self.assertIsNone(mediator.find_shared_path(station_a, station_b))

    def test_find_travel_plan_handles_arrived_passenger(self):
        mediator = Mediator()
        station = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        mediator.stations = [station]
        passenger = Passenger(station.shape)
        station.add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.travel_plans[passenger] = TravelPlan([])

        mediator.find_travel_plan_for_passengers()

        self.assertNotIn(passenger, station.passengers)
        self.assertNotIn(passenger, mediator.passengers)
        self.assertTrue(passenger.is_at_destination)
        self.assertNotIn(passenger, mediator.travel_plans)


if __name__ == "__main__":
    unittest.main()

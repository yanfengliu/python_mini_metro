import os
import sys
import unittest
from unittest.mock import MagicMock, create_autospec, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame
from config import (
    passenger_display_buffer,
    passenger_max_wait_time_ms,
    passenger_size,
    station_color,
    station_snap_blip_duration_ms,
    station_size,
    station_unique_shape_type_list,
)
from entity.get_entity import (
    get_metros,
    get_random_stations,
    get_station_spawn_position,
)
from entity.metro import Metro
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from geometry.type import ShapeType
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

    def test_metro_draw_positions_passengers_in_3x2_grid(self):
        metro = Metro()
        metro.position = Point(100, 100)
        passengers = [Passenger(Circle((0, 0, 0), 1)) for _ in range(6)]
        for passenger in passengers:
            passenger.draw = MagicMock()
            metro.add_passenger(passenger)

        metro.draw(self.screen)

        grid_cols = metro.passengers_per_row
        grid_rows = 2
        metro_width = 2 * metro.size
        metro_height = metro.size
        passenger_diameter = 2 * passenger_size
        x_gap = (metro_width - (grid_cols * passenger_diameter)) / (grid_cols + 1)
        y_gap = (metro_height - (grid_rows * passenger_diameter)) / (grid_rows + 1)
        x_step = passenger_diameter + x_gap
        y_step = passenger_diameter + y_gap
        x_start = (-metro_width / 2) + x_gap + passenger_size
        y_start = (-metro_height / 2) + y_gap + passenger_size

        for idx, passenger in enumerate(passengers):
            col = idx % grid_cols
            row = idx // grid_cols
            x_offset = x_start + (col * x_step)
            y_offset = y_start + (row * y_step)
            expected_position = metro.position + Point(x_offset, y_offset).rotate(0)
            self.assertEqual(passenger.position, expected_position)

    def test_metro_draw_rotates_passenger_grid_with_metro(self):
        metro = Metro()
        metro.position = Point(200, 200)
        metro.shape.set_degrees(90)
        passenger = Passenger(Circle((0, 0, 0), 1))
        passenger.draw = MagicMock()
        metro.add_passenger(passenger)

        metro.draw(self.screen)

        grid_cols = metro.passengers_per_row
        grid_rows = 2
        metro_width = 2 * metro.size
        metro_height = metro.size
        passenger_diameter = 2 * passenger_size
        x_gap = (metro_width - (grid_cols * passenger_diameter)) / (grid_cols + 1)
        y_gap = (metro_height - (grid_rows * passenger_diameter)) / (grid_rows + 1)
        x_start = (-metro_width / 2) + x_gap + passenger_size
        y_start = (-metro_height / 2) + y_gap + passenger_size
        x_offset = x_start
        y_offset = y_start
        expected_position = metro.position + Point(x_offset, y_offset).rotate(90)
        self.assertEqual(passenger.position, expected_position)

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

    def test_station_draw_hides_overdue_passenger_during_off_phase(self):
        station = Station(Circle(station_color, station_size), Point(0, 0))
        passenger = Passenger(Circle((0, 0, 0), 3))
        passenger.wait_ms = passenger_max_wait_time_ms + 1_000
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

    def test_station_snap_blip_lifecycle(self):
        station = Station(Circle(station_color, station_size), Point(0, 0))
        station.start_snap_blip(100, (1, 2, 3))

        active_early = station.get_active_snap_blips(100)
        self.assertEqual(len(active_early), 1)

        active_late = station.get_active_snap_blips(
            100 + station_snap_blip_duration_ms
        )
        self.assertEqual(active_late, [])

    def test_station_draw_renders_snap_blip_as_expanding_ring(self):
        station = Station(Circle(station_color, station_size), Point(0, 0))
        station.start_snap_blip(0, (11, 22, 33))
        station.shape.draw = MagicMock()
        pygame.draw.circle = MagicMock()

        station.draw(self.screen, current_time_ms=200)

        self.assertGreaterEqual(pygame.draw.circle.call_count, 1)

    def test_unique_station_shapes_only_spawn_after_threshold_and_once(self):
        with (
            patch(
                "entity.get_entity.station_unique_spawn_start_index",
                2,
            ),
            patch(
                "entity.get_entity.station_unique_spawn_chance",
                1.0,
            ),
        ):
            stations = get_random_stations(8)

        unique_shape_types = set(station_unique_shape_type_list)
        first_two_shape_types = [station.shape.type for station in stations[:2]]
        self.assertTrue(
            all(
                shape_type not in unique_shape_types
                for shape_type in first_two_shape_types
            )
        )

        later_shape_types = [station.shape.type for station in stations[2:]]
        spawned_unique_shape_types = [
            shape_type
            for shape_type in later_shape_types
            if shape_type in unique_shape_types
        ]
        self.assertEqual(
            len(spawned_unique_shape_types), len(set(spawned_unique_shape_types))
        )
        self.assertEqual(
            len(spawned_unique_shape_types),
            min(len(unique_shape_types), len(stations) - 2),
        )
        for shape_type in spawned_unique_shape_types:
            self.assertIn(shape_type, list(ShapeType))

    def test_station_spawn_position_biases_toward_existing_station_mass(self):
        existing_positions = [Point(100, 100), Point(120, 110), Point(80, 90)]
        candidate_positions = [
            Point(105, 102),
            Point(900, 900),
            Point(400, 400),
            Point(300, 100),
            Point(100, 300),
            Point(50, 50),
            Point(1800, 1000),
            Point(600, 50),
        ]

        with patch(
            "entity.get_entity.get_random_position",
            side_effect=candidate_positions,
        ), patch(
            "entity.get_entity.random.choices",
            side_effect=lambda population, weights, k: [population[0]],
        ) as choices_mock:
            spawn_position = get_station_spawn_position(existing_positions)

        self.assertEqual(spawn_position, candidate_positions[0])
        weights = choices_mock.call_args.kwargs["weights"]
        self.assertGreater(weights[0], weights[1])
        self.assertGreater(weights[0], weights[2])

    def test_station_spawn_position_without_existing_is_uniform_random(self):
        expected_position = Point(333, 444)
        with patch(
            "entity.get_entity.get_random_position",
            return_value=expected_position,
        ) as random_position_mock:
            spawn_position = get_station_spawn_position([])

        self.assertEqual(spawn_position, expected_position)
        random_position_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

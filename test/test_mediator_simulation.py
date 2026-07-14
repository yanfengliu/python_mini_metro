from math import ceil
from unittest.mock import MagicMock

from test import mediator_test_support as support

# isort: split

from config import (
    framerate,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    station_color,
    station_size,
    station_snap_blip_duration_ms,
)
from entity.metro import Metro
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from mediator import Mediator


class TestMediatorSimulation(support.MediatorTestCase):
    def test_passengers_are_added_to_stations(self):
        self.mediator.spawn_passengers()

        self.assertEqual(len(self.mediator.passengers), len(self.mediator.stations))

    def test_is_passenger_spawn_time(self):
        for station in self.mediator.stations:
            self.mediator.station_spawn_interval_steps[station] = (
                passenger_spawning_interval_step
            )
            self.mediator.station_steps_since_last_spawn[station] = 0

        # Run until first wave of passengers spawn.
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.assertEqual(
            len(self.mediator.passengers),
            len(self.mediator.stations),
        )

        for _ in range(passenger_spawning_interval_step - 1):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.assertEqual(
            len(self.mediator.passengers),
            len(self.mediator.stations),
        )

        self.mediator.increment_time(ceil(1000 / framerate))
        self.assertEqual(
            len(self.mediator.passengers),
            2 * len(self.mediator.stations),
        )

    def test_stations_spawn_with_independent_rhythms(self):
        mediator = Mediator()
        mediator.passenger_spawning_step = 999999

        for idx, station in enumerate(mediator.stations):
            mediator.station_steps_since_last_spawn[station] = 0
            mediator.station_spawn_interval_steps[station] = 999999
            if idx == 0:
                mediator.station_spawn_interval_steps[station] = 2
            elif idx == 1:
                mediator.station_spawn_interval_steps[station] = 4

        dt_ms = ceil(1000 / framerate)
        mediator.increment_time(dt_ms)
        mediator.increment_time(dt_ms)

        self.assertEqual(len(mediator.stations[0].passengers), 1)
        self.assertEqual(len(mediator.stations[1].passengers), 0)

        mediator.increment_time(dt_ms)
        mediator.increment_time(dt_ms)

        self.assertEqual(len(mediator.stations[0].passengers), 2)
        self.assertEqual(len(mediator.stations[1].passengers), 1)

    def test_passengers_spawned_at_a_station_have_a_different_destination(self):
        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        for station in self.mediator.stations:
            for passenger in station.passengers:
                self.assertNotEqual(
                    passenger.destination_shape.type, station.shape.type
                )

    def test_increment_time_paused(self):
        mediator = Mediator()
        mediator.is_paused = True
        mediator.time_ms = 10
        mediator.steps = 5
        mediator.increment_time(100)
        self.assertEqual(mediator.time_ms, 10)
        self.assertEqual(mediator.steps, 5)

    def test_increment_time_prunes_expired_snap_blips(self):
        mediator = Mediator()
        station = mediator.stations[0]
        station.start_snap_blip(0, (1, 2, 3))

        mediator.increment_time(station_snap_blip_duration_ms)

        self.assertEqual(station.snap_blips, [])

    def test_increment_time_scales_with_game_speed_multiplier(self):
        mediator = Mediator()
        mediator.game_speed_multiplier = 4
        mediator.time_ms = 10
        mediator.steps = 5
        station = mediator.stations[0]
        station_steps_before = mediator.station_steps_since_last_spawn[station]

        mediator.is_passenger_spawn_time = MagicMock(return_value=False)
        mediator.find_travel_plan_for_passengers = MagicMock()
        mediator.move_passengers = MagicMock()
        mediator.update_waiting_and_game_over = MagicMock()

        mediator.increment_time(100)

        self.assertEqual(mediator.time_ms, 410)
        self.assertEqual(mediator.steps, 9)
        self.assertEqual(
            mediator.station_steps_since_last_spawn[station], station_steps_before + 4
        )
        mediator.move_passengers.assert_called_once_with(400)
        mediator.update_waiting_and_game_over.assert_called_once_with(400)

    def test_update_waiting_game_over_at_passenger_max_wait_boundary(self):
        mediator = Mediator()
        station = Station(Circle(station_color, station_size), Point(0, 0))
        mediator.stations = [station]
        passenger = Passenger(Circle(station_color, station_size))
        station.add_passenger(passenger)

        mediator.passenger_max_wait_time_ms = 100
        mediator.max_waiting_passengers = 1

        mediator.update_waiting_and_game_over(99)
        self.assertEqual(passenger.wait_ms, 99)
        self.assertFalse(mediator.is_game_over)

        mediator.update_waiting_and_game_over(1)
        self.assertEqual(passenger.wait_ms, 100)
        self.assertTrue(mediator.is_game_over)

    def test_update_waiting_game_over_respects_max_waiting_passengers(self):
        mediator = Mediator()
        station = Station(Circle(station_color, station_size), Point(0, 0))
        mediator.stations = [station]
        passenger_a = Passenger(Circle(station_color, station_size))
        passenger_b = Passenger(Circle(station_color, station_size))
        station.add_passenger(passenger_a)
        station.add_passenger(passenger_b)

        mediator.passenger_max_wait_time_ms = 100
        mediator.max_waiting_passengers = 2
        passenger_a.wait_ms = 100
        passenger_b.wait_ms = 99

        mediator.update_waiting_and_game_over(0)
        self.assertFalse(mediator.is_game_over)

        mediator.update_waiting_and_game_over(1)
        self.assertTrue(mediator.is_game_over)

    def test_update_waiting_ignores_metro_passengers_for_game_over(self):
        mediator = Mediator()
        station = Station(Circle(station_color, station_size), Point(0, 0))
        mediator.stations = [station]
        metro = Metro()
        passenger = Passenger(Circle(station_color, station_size))
        passenger.wait_ms = 10_000
        metro.add_passenger(passenger)
        mediator.metros = [metro]
        mediator.passengers = [passenger]

        mediator.passenger_max_wait_time_ms = 1
        mediator.max_waiting_passengers = 1

        mediator.update_waiting_and_game_over(0)
        self.assertFalse(mediator.is_game_over)

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.metro import Metro
from entity.passenger import Passenger
from env import MiniMetroEnv
from mediator import Mediator


class TestOverduePassengerThreshold(unittest.TestCase):
    @staticmethod
    def add_waiting_passenger(
        mediator: Mediator,
        *,
        wait_ms: int,
        station_index: int = 0,
    ) -> Passenger:
        destination = mediator.stations[(station_index + 1) % len(mediator.stations)]
        passenger = Passenger(destination.shape)
        passenger.wait_ms = wait_ms
        mediator.stations[station_index].add_passenger(passenger)
        return passenger

    def test_config_exports_canonical_default_and_legacy_value_alias(self) -> None:
        self.assertEqual(getattr(config, "overdue_passenger_threshold", None), 2)
        self.assertEqual(
            config.max_waiting_passengers,
            config.overdue_passenger_threshold,
        )

    def test_mediator_defaults_to_two_overdue_station_passengers(self) -> None:
        mediator = Mediator(seed=1)

        self.assertEqual(getattr(mediator, "overdue_passenger_threshold", None), 2)
        self.assertEqual(mediator.max_waiting_passengers, 2)

    def test_canonical_assignment_updates_legacy_runtime_alias(self) -> None:
        mediator = Mediator(seed=2)

        mediator.overdue_passenger_threshold = 3

        self.assertEqual(mediator.max_waiting_passengers, 3)

    def test_legacy_assignment_updates_canonical_runtime_field(self) -> None:
        mediator = Mediator(seed=3)

        mediator.max_waiting_passengers = 4

        self.assertEqual(mediator.overdue_passenger_threshold, 4)

    def test_first_overdue_passenger_warns_and_second_ends_at_boundary(self) -> None:
        mediator = Mediator(seed=4)
        mediator.passenger_max_wait_time_ms = 100
        first = self.add_waiting_passenger(mediator, wait_ms=100)
        second = self.add_waiting_passenger(mediator, wait_ms=99)

        mediator.update_waiting_and_game_over(0)

        self.assertEqual(first.wait_ms, 100)
        self.assertEqual(second.wait_ms, 99)
        self.assertFalse(mediator.is_game_over)

        mediator.update_waiting_and_game_over(1)

        self.assertEqual(second.wait_ms, 100)
        self.assertTrue(mediator.is_game_over)

    def test_explicit_threshold_one_preserves_legacy_terminal_behavior(self) -> None:
        mediator = Mediator(seed=5)
        mediator.passenger_max_wait_time_ms = 100
        mediator.overdue_passenger_threshold = 1
        passenger = self.add_waiting_passenger(mediator, wait_ms=99)

        mediator.update_waiting_and_game_over(1)

        self.assertEqual(passenger.wait_ms, 100)
        self.assertTrue(mediator.is_game_over)

    def test_overdue_metro_riders_do_not_count_toward_threshold(self) -> None:
        mediator = Mediator(seed=6)
        mediator.passenger_max_wait_time_ms = 100
        mediator.overdue_passenger_threshold = 1
        metro = Metro()
        passenger = Passenger(mediator.stations[0].shape)
        passenger.wait_ms = 100
        metro.add_passenger(passenger)
        mediator.metros = [metro]
        mediator.passengers = [passenger]

        mediator.update_waiting_and_game_over(0)

        self.assertFalse(mediator.is_game_over)

    def test_environment_reset_restores_repository_default(self) -> None:
        env = MiniMetroEnv()
        env.mediator.max_waiting_passengers = 9

        env.reset(seed=7)

        self.assertEqual(env.mediator.overdue_passenger_threshold, 2)
        self.assertEqual(env.mediator.max_waiting_passengers, 2)


if __name__ == "__main__":
    unittest.main()

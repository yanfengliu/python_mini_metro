from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import call, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import passenger_spawning_interval_step
from game_clock import FixedStepClock
from mediator import Mediator


class TestSpawnCadence(unittest.TestCase):
    def test_base_interval_is_fifteen_seconds_at_sixty_steps_per_second(self):
        self.assertEqual(passenger_spawning_interval_step, 900)
        self.assertEqual(Mediator(seed=1).passenger_spawning_interval_step, 900)

    def test_station_intervals_sample_inclusive_bounds_once_per_station(self):
        mediator = Mediator(seed=1)
        stations = mediator.stations[:2]
        for station in stations:
            mediator.station_spawn_interval_steps.pop(station)
            mediator.station_steps_since_last_spawn.pop(station)

        with patch.object(
            mediator.context.python_random,
            "randint",
            side_effect=[630, 1170],
        ) as randint:
            mediator.initialize_station_spawning_state(stations)
            mediator.station_steps_since_last_spawn[stations[0]] = 123
            mediator.initialize_station_spawning_state(stations)

        self.assertEqual(
            randint.call_args_list,
            [call(630, 1170), call(630, 1170)],
        )
        self.assertEqual(mediator.station_spawn_interval_steps[stations[0]], 630)
        self.assertEqual(mediator.station_spawn_interval_steps[stations[1]], 1170)
        self.assertEqual(mediator.station_steps_since_last_spawn[stations[0]], 123)
        self.assertEqual(mediator.station_steps_since_last_spawn[stations[1]], 1170)

    def test_active_stations_attempt_spawn_on_first_unpaused_tick_at_each_speed(self):
        for speed_multiplier in (1, 2, 4):
            with self.subTest(speed_multiplier=speed_multiplier):
                mediator = Mediator(seed=1)
                fixed_dt_ms = FixedStepClock().take_exact_steps(1)[0]
                mediator.set_game_speed(speed_multiplier)

                mediator.increment_time(fixed_dt_ms)

                self.assertEqual(len(mediator.passengers), len(mediator.stations))
                self.assertTrue(
                    all(len(station.passengers) == 1 for station in mediator.stations)
                )
                self.assertTrue(
                    all(
                        mediator.station_steps_since_last_spawn[station] == 0
                        for station in mediator.stations
                    )
                )

    def test_due_full_station_skips_passenger_but_resets_counter(self):
        mediator = Mediator(seed=1)
        target_station = mediator.stations[0]
        target_station.passengers = [object()] * target_station.capacity
        mediator.passenger_spawning_step = 1_000_000
        for station in mediator.stations:
            mediator.station_steps_since_last_spawn[station] = 0
            mediator.station_spawn_interval_steps[station] = 1_000_000
        mediator.station_steps_since_last_spawn[target_station] = 900
        mediator.station_spawn_interval_steps[target_station] = 900
        passenger_count = len(mediator.passengers)

        mediator.spawn_passengers()

        self.assertEqual(len(target_station.passengers), target_station.capacity)
        self.assertEqual(len(mediator.passengers), passenger_count)
        self.assertEqual(mediator.station_steps_since_last_spawn[target_station], 0)

    def test_speed_changes_wall_ticks_but_preserves_spawn_simulation_time(self):
        expected_ticks = {1: 900, 2: 450, 4: 225}
        observed_simulation_times_ms: set[int] = set()

        for speed_multiplier, tick_count in expected_ticks.items():
            with self.subTest(speed_multiplier=speed_multiplier):
                mediator = Mediator(seed=1)
                target_station = mediator.stations[0]
                mediator.passenger_spawning_step = 1_000_000
                for station in mediator.stations:
                    mediator.station_steps_since_last_spawn[station] = 0
                    mediator.station_spawn_interval_steps[station] = 1_000_000
                mediator.station_spawn_interval_steps[target_station] = 900
                mediator.set_game_speed(speed_multiplier)

                fixed_dts_ms = FixedStepClock().take_exact_steps(tick_count)
                for fixed_dt_ms in fixed_dts_ms[:-1]:
                    mediator.increment_time(fixed_dt_ms)

                self.assertEqual(target_station.passengers, [])

                mediator.increment_time(fixed_dts_ms[-1])

                self.assertEqual(len(target_station.passengers), 1)
                self.assertEqual(mediator.steps, 900)
                self.assertEqual(mediator.time_ms, 15_000)
                self.assertEqual(
                    sum(fixed_dts_ms),
                    15_000 // speed_multiplier,
                )
                observed_simulation_times_ms.add(mediator.time_ms)

        self.assertEqual(observed_simulation_times_ms, {15_000})

    def test_non_divisible_interval_uses_first_whole_speed_tick(self):
        mediator = Mediator(seed=1)
        target_station = mediator.stations[0]
        mediator.passenger_spawning_step = 1_000_000
        for station in mediator.stations:
            mediator.station_steps_since_last_spawn[station] = 0
            mediator.station_spawn_interval_steps[station] = 1_000_000
        mediator.station_spawn_interval_steps[target_station] = 1170
        mediator.set_game_speed(4)
        fixed_dts_ms = FixedStepClock().take_exact_steps(293)

        for fixed_dt_ms in fixed_dts_ms[:-1]:
            mediator.increment_time(fixed_dt_ms)
        self.assertEqual(target_station.passengers, [])

        mediator.increment_time(fixed_dts_ms[-1])

        self.assertEqual(len(target_station.passengers), 1)
        self.assertEqual(mediator.steps, 1172)
        self.assertEqual(mediator.time_ms, 19_536)
        self.assertEqual(sum(fixed_dts_ms), 4_884)


if __name__ == "__main__":
    unittest.main()

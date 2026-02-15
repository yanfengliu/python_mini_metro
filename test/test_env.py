import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import station_color, station_size
from env import MiniMetroEnv
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from travel_plan import TravelPlan
from utils import get_random_color


class TestEnv(unittest.TestCase):
    def test_reset_is_deterministic_with_seed(self):
        env = MiniMetroEnv()
        obs_a = env.reset(seed=123)
        positions_a = [
            station["position"] for station in obs_a["structured"]["stations"]
        ]

        obs_b = env.reset(seed=123)
        positions_b = [
            station["position"] for station in obs_b["structured"]["stations"]
        ]

        self.assertEqual(positions_a, positions_b)

    def test_step_create_path(self):
        env = MiniMetroEnv()
        env.reset(seed=1)
        obs, reward, done, info = env.step(
            {"type": "create_path", "stations": [0, 1], "loop": False}
        )

        self.assertTrue(info["action_ok"])
        self.assertFalse(done)
        self.assertIsInstance(reward, int)
        self.assertEqual(len(env.mediator.paths), 1)
        self.assertEqual(len(env.mediator.metros), 1)
        self.assertIn("arrays", obs)
        self.assertIn("structured", obs)

    def test_remove_path_by_index(self):
        env = MiniMetroEnv()
        env.reset(seed=2)
        env.step({"type": "create_path", "stations": [0, 1, 2], "loop": False})

        self.assertEqual(len(env.mediator.paths), 1)
        obs, reward, done, info = env.step(
            {"type": "remove_path", "path_index": 0}
        )

        self.assertTrue(info["action_ok"])
        self.assertFalse(done)
        self.assertEqual(len(env.mediator.paths), 0)
        self.assertIn("structured", obs)

    def test_remove_path_by_id(self):
        env = MiniMetroEnv()
        env.reset(seed=3)
        env.step({"type": "create_path", "stations": [0, 1], "loop": False})

        path_id = env.mediator.paths[0].id
        obs, reward, done, info = env.step(
            {"type": "remove_path", "path_id": path_id}
        )

        self.assertTrue(info["action_ok"])
        self.assertFalse(done)
        self.assertEqual(len(env.mediator.paths), 0)
        self.assertIn("arrays", obs)

    def test_pause_and_resume(self):
        env = MiniMetroEnv(dt_ms=10)
        env.reset(seed=4)
        time_before = env.mediator.time_ms
        steps_before = env.mediator.steps

        env.step({"type": "pause"})
        self.assertTrue(env.mediator.is_paused)
        self.assertEqual(env.mediator.time_ms, time_before)
        self.assertEqual(env.mediator.steps, steps_before)

        env.step({"type": "resume"})
        self.assertFalse(env.mediator.is_paused)
        self.assertGreater(env.mediator.time_ms, time_before)
        self.assertGreater(env.mediator.steps, steps_before)

    def test_step_advances_time(self):
        env = MiniMetroEnv()
        env.reset(seed=5)
        time_before = env.mediator.time_ms
        steps_before = env.mediator.steps

        env.step({"type": "noop"}, dt_ms=7)

        self.assertEqual(env.mediator.time_ms, time_before + 7)
        self.assertEqual(env.mediator.steps, steps_before + 1)

    def test_invalid_action_returns_false(self):
        env = MiniMetroEnv()
        env.reset(seed=6)
        _, _, _, info = env.step({"type": "remove_path", "path_index": 99})

        self.assertFalse(info["action_ok"])

    def test_observation_arrays_shapes(self):
        env = MiniMetroEnv()
        obs = env.reset(seed=7)
        arrays = obs["arrays"]
        structured = obs["structured"]

        self.assertEqual(
            arrays["station_positions"].shape[0],
            len(structured["stations"]),
        )
        self.assertEqual(
            arrays["station_shape_types"].shape[0],
            len(structured["stations"]),
        )
        self.assertEqual(
            arrays["station_passenger_counts"].shape[0],
            len(structured["stations"]),
        )

        env.step({"type": "create_path", "stations": [0, 1], "loop": False})
        obs = env.observe()
        arrays = obs["arrays"]
        structured = obs["structured"]
        self.assertEqual(
            len(arrays["path_station_indices"]),
            len(structured["paths"]),
        )

    def test_passengers_spawn_and_get_travel_plans(self):
        env = MiniMetroEnv()
        env.reset(seed=8)
        env.mediator.stations = [
            Station(
                Rect(
                    color=station_color,
                    width=2 * station_size,
                    height=2 * station_size,
                ),
                Point(0, 0),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                Point(100, 0),
            ),
        ]

        env.step({"type": "create_path", "stations": [0, 1], "loop": False})
        env.step({"type": "noop"}, dt_ms=1)

        self.assertEqual(len(env.mediator.passengers), 2)
        self.assertEqual(len(env.mediator.travel_plans), 2)
        for plan in env.mediator.travel_plans.values():
            self.assertIsNotNone(plan.next_path)

    def test_metro_moves_along_path(self):
        env = MiniMetroEnv()
        env.reset(seed=9)
        env.mediator.stations = [
            Station(
                Rect(
                    color=station_color,
                    width=2 * station_size,
                    height=2 * station_size,
                ),
                Point(0, 0),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                Point(200, 0),
            ),
        ]

        env.step({"type": "create_path", "stations": [0, 1], "loop": False})
        env.step({"type": "noop"}, dt_ms=2000)

        metro = env.mediator.metros[0]
        self.assertIsNotNone(metro.current_station)
        self.assertIn(
            metro.current_station.id,
            [station.id for station in env.mediator.stations],
        )

    def test_create_looped_path(self):
        env = MiniMetroEnv()
        env.reset(seed=10)
        obs, _, _, info = env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": True}
        )

        self.assertTrue(info["action_ok"])
        self.assertEqual(len(env.mediator.paths), 1)
        self.assertTrue(env.mediator.paths[0].is_looped)
        self.assertIn("structured", obs)

    def test_invalid_create_path_inputs(self):
        env = MiniMetroEnv()
        env.reset(seed=11)
        _, _, _, info = env.step(
            {"type": "create_path", "stations": [0], "loop": False}
        )
        self.assertFalse(info["action_ok"])
        self.assertEqual(len(env.mediator.paths), 0)

        _, _, _, info = env.step(
            {"type": "create_path", "stations": [0, 999], "loop": False}
        )
        self.assertFalse(info["action_ok"])
        self.assertEqual(len(env.mediator.paths), 0)

    def test_path_creation_limit(self):
        env = MiniMetroEnv()
        env.reset(seed=12)
        env.mediator.purchased_num_paths = env.mediator.num_paths
        env.mediator.total_travels_handled = 10000
        env.mediator.update_unlocked_num_paths()
        env.mediator.update_unlocked_num_stations()
        for idx in range(env.mediator.num_paths):
            _, _, _, info = env.step(
                {"type": "create_path", "stations": [idx, idx + 1], "loop": False}
            )
            self.assertTrue(info["action_ok"])

        _, _, _, info = env.step(
            {"type": "create_path", "stations": [0, 2], "loop": False}
        )
        self.assertFalse(info["action_ok"])
        self.assertEqual(len(env.mediator.paths), env.mediator.num_paths)

    def test_path_unlock_progression_uses_score_purchases(self):
        env = MiniMetroEnv()
        env.reset(seed=16)

        self.assertEqual(env.mediator.unlocked_num_paths, 1)
        second_button = env.mediator.path_buttons[1]

        env.mediator.total_travels_handled = 10000
        env.mediator.update_unlocked_num_paths()
        self.assertEqual(env.mediator.unlocked_num_paths, 1)

        env.mediator.score = env.mediator.path_purchase_prices[0] - 1
        self.assertFalse(env.mediator.try_purchase_path_button(second_button))
        self.assertEqual(env.mediator.unlocked_num_paths, 1)

        env.mediator.score += 1
        self.assertTrue(env.mediator.try_purchase_path_button(second_button))
        self.assertEqual(env.mediator.unlocked_num_paths, 2)

    def test_reward_increments_on_passenger_delivery(self):
        env = MiniMetroEnv()
        env.reset(seed=13)
        station_a = Station(
            Rect(
                color=station_color,
                width=2 * station_size,
                height=2 * station_size,
            ),
            Point(0, 0),
        )
        station_b = Station(
            Circle(
                color=station_color,
                radius=station_size,
            ),
            Point(0, 0),
        )
        env.mediator.stations = [station_a, station_b]

        metro = Metro()
        metro.current_station = station_b
        metro.position = station_b.position
        env.mediator.paths = []
        env.mediator.metros = [metro]

        passenger = Passenger(destination_shape=station_b.shape)
        metro.add_passenger(passenger)
        env.mediator.passengers = [passenger]
        env.mediator.travel_plans = {passenger: TravelPlan([])}

        env.mediator.passenger_spawning_step = 999999
        env.mediator.passenger_spawning_interval_step = 999999
        for station in env.mediator.stations:
            env.mediator.station_steps_since_last_spawn[station] = 0
            env.mediator.station_spawn_interval_steps[station] = 999999

        _, reward, _, info = env.step({"type": "noop"}, dt_ms=500)

        self.assertTrue(info["action_ok"])
        self.assertEqual(reward, 1)
        self.assertEqual(env.mediator.score, 1)
        self.assertEqual(env.mediator.total_travels_handled, 1)
        self.assertEqual(len(env.mediator.passengers), 0)

    def test_observation_passenger_locations(self):
        env = MiniMetroEnv()
        env.reset(seed=14)
        station_a = Station(
            Rect(
                color=station_color,
                width=2 * station_size,
                height=2 * station_size,
            ),
            Point(0, 0),
        )
        station_b = Station(
            Circle(
                color=station_color,
                radius=station_size,
            ),
            Point(200, 0),
        )
        env.mediator.stations = [station_a, station_b]

        path = Path(get_random_color())
        path.add_station(station_a)
        path.add_station(station_b)
        metro = Metro()
        path.add_metro(metro)
        metro.current_station = station_a
        env.mediator.paths = [path]
        env.mediator.metros = [metro]

        passenger_station = Passenger(destination_shape=station_b.shape)
        station_a.add_passenger(passenger_station)
        passenger_metro = Passenger(destination_shape=station_a.shape)
        metro.add_passenger(passenger_metro)

        env.mediator.passengers = [passenger_station, passenger_metro]
        env.mediator.travel_plans = {
            passenger_station: TravelPlan([station_b]),
            passenger_metro: TravelPlan([]),
        }

        obs = env.observe()["structured"]
        locations = {p["id"]: p["location"] for p in obs["passengers"]}

        self.assertEqual(locations[passenger_station.id], ("station", station_a.id))
        self.assertEqual(locations[passenger_metro.id], ("metro", metro.id))

    def test_game_over_when_waiting_too_long(self):
        env = MiniMetroEnv()
        env.reset(seed=15)
        env.mediator.passenger_max_wait_time_ms = 0
        env.mediator.max_waiting_passengers = 1

        _, _, done, _ = env.step({"type": "noop"}, dt_ms=1)

        self.assertTrue(done)
        self.assertTrue(env.mediator.is_game_over)
if __name__ == "__main__":
    unittest.main()

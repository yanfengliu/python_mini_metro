import json
import os
import sys
import unittest
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from recursive_playtest import (
    LINE_CREDITS_REWARD_CONTRACT,
    canonical_checkpoint,
    normalize_checkpoint,
)


class TestCheckpoint(unittest.TestCase):
    def setUp(self):
        self.env = MiniMetroEnv()
        self.env.reset(seed=77)

    def checkpoint(self):
        return canonical_checkpoint(self.env)

    def test_checkpoint_is_strict_json_and_uuid_free(self):
        self.env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
            dt_ms=1,
        )
        checkpoint = self.checkpoint()
        encoded = json.dumps(checkpoint, allow_nan=False, sort_keys=True)

        for entity in (
            *self.env.mediator.all_stations,
            *self.env.mediator.paths,
            *self.env.mediator.metros,
            *self.env.mediator.passengers,
        ):
            self.assertNotIn(entity.id, encoded)
        self.assertNotIn("_id_to_index", encoded)
        self.assertEqual(checkpoint["schemaVersion"], 2)
        self.assertIn("structured", checkpoint)
        self.assertIn("arrays", checkpoint)
        self.assertIn("rng", checkpoint)
        self.assertEqual(
            checkpoint["progression"]["deliveries"],
            checkpoint["progression"]["total_travels_handled"],
        )
        self.assertEqual(
            checkpoint["progression"]["line_credits"],
            checkpoint["progression"]["score"],
        )
        self.assertEqual(
            checkpoint["progression"]["limits"]["overdue_passenger_threshold"],
            checkpoint["progression"]["limits"]["max_waiting_passengers"],
        )
        self.assertIn("last_deliveries", checkpoint["environment"])
        self.assertIn("last_line_credits", checkpoint["environment"])
        self.assertIn("last_score", checkpoint["environment"])
        self.assertEqual(checkpoint["environment"]["reward_mode"], "deliveries")

    def test_genuine_v1_checkpoint_normalizes_without_mutating_legacy_shape(self):
        legacy_env = MiniMetroEnv(reward_mode=LINE_CREDITS_REWARD_CONTRACT)
        legacy_env.reset(seed=77)
        legacy = canonical_checkpoint(legacy_env, schema_version=1)
        encoded = json.dumps(legacy, allow_nan=False, sort_keys=True)

        normalized = normalize_checkpoint(legacy)

        self.assertEqual(legacy["schemaVersion"], 1)
        self.assertNotIn("deliveries", legacy["progression"])
        self.assertNotIn("line_credits", legacy["progression"])
        self.assertNotIn("overdue_passenger_threshold", legacy["progression"]["limits"])
        self.assertNotIn("last_deliveries", legacy["environment"])
        self.assertNotIn("last_line_credits", legacy["environment"])
        self.assertEqual(json.dumps(legacy, allow_nan=False, sort_keys=True), encoded)
        self.assertEqual(normalized["schemaVersion"], 2)
        self.assertEqual(
            normalized["progression"]["deliveries"],
            legacy["progression"]["total_travels_handled"],
        )
        self.assertEqual(
            normalized["progression"]["line_credits"],
            legacy["progression"]["score"],
        )
        self.assertEqual(
            normalized["environment"]["last_deliveries"],
            legacy["progression"]["total_travels_handled"],
        )
        self.assertEqual(
            normalized["environment"]["last_line_credits"],
            legacy["environment"]["last_score"],
        )
        self.assertEqual(
            normalized["environment"]["reward_mode"],
            LINE_CREDITS_REWARD_CONTRACT,
        )

    def test_v1_checkpoint_rejects_a_delivery_reward_environment(self):
        with self.assertRaisesRegex(ValueError, "checkpoint v1"):
            canonical_checkpoint(self.env, schema_version=1)

    def test_checkpoint_distinguishes_next_step_reward_contract(self):
        legacy_reward_env = MiniMetroEnv(reward_mode=LINE_CREDITS_REWARD_CONTRACT)
        legacy_reward_env.reset(seed=77)

        current = canonical_checkpoint(self.env)
        legacy = canonical_checkpoint(legacy_reward_env)
        current_without_mode = deepcopy(current)
        legacy_without_mode = deepcopy(legacy)
        current_without_mode["environment"].pop("reward_mode")
        legacy_without_mode["environment"].pop("reward_mode")

        self.assertNotEqual(current, legacy)
        self.assertEqual(current_without_mode, legacy_without_mode)
        self.assertEqual(current["environment"]["reward_mode"], "deliveries")
        self.assertEqual(
            legacy["environment"]["reward_mode"], LINE_CREDITS_REWARD_CONTRACT
        )

    def test_checkpoint_normalizer_rejects_unknown_or_incomplete_schemas(self):
        checkpoint = self.checkpoint()
        with self.assertRaises(ValueError):
            normalize_checkpoint({**checkpoint, "schemaVersion": 3})
        incomplete = json.loads(json.dumps(checkpoint))
        del incomplete["progression"]["deliveries"]
        with self.assertRaises(ValueError):
            normalize_checkpoint(incomplete)

    def test_checkpoint_changes_for_each_latent_state_family(self):
        def assert_perturbed(mutator):
            before = self.checkpoint()
            mutator()
            after = self.checkpoint()
            self.assertNotEqual(before, after)

        with self.subTest(family="station spawn counter"):
            station = self.env.mediator.all_stations[0]
            assert_perturbed(
                lambda: self.env.mediator.station_steps_since_last_spawn.__setitem__(
                    station,
                    self.env.mediator.station_steps_since_last_spawn[station] + 1,
                )
            )
        with self.subTest(family="station spawn interval"):
            station = self.env.mediator.all_stations[1]
            assert_perturbed(
                lambda: self.env.mediator.station_spawn_interval_steps.__setitem__(
                    station,
                    self.env.mediator.station_spawn_interval_steps[station] + 1,
                )
            )
        with self.subTest(family="progression and unlocks"):
            assert_perturbed(
                lambda: setattr(
                    self.env.mediator,
                    "total_travels_handled",
                    self.env.mediator.total_travels_handled + 1,
                )
            )
        with self.subTest(family="station pool"):
            assert_perturbed(
                lambda: setattr(
                    self.env.mediator.all_stations[-1].position,
                    "left",
                    self.env.mediator.all_stations[-1].position.left + 1,
                )
            )
        with self.subTest(family="environment reward baseline"):
            assert_perturbed(lambda: setattr(self.env, "last_score", 1))
        with self.subTest(family="environment default timing"):
            assert_perturbed(lambda: setattr(self.env, "dt_ms_default", 16))

    def test_checkpoint_changes_for_topology_travel_plans_and_metro_motion(self):
        self.env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
            dt_ms=1,
        )
        baseline = self.checkpoint()

        metro = self.env.mediator.metros[0]
        metro.stop_time_remaining_ms += 1
        self.assertNotEqual(baseline, self.checkpoint())
        metro.stop_time_remaining_ms -= 1

        path = self.env.mediator.paths[0]
        path.stations[0], path.stations[1] = path.stations[1], path.stations[0]
        self.assertNotEqual(baseline, self.checkpoint())
        path.stations[0], path.stations[1] = path.stations[1], path.stations[0]

        self.assertTrue(self.env.mediator.travel_plans)
        plan = next(iter(self.env.mediator.travel_plans.values()))
        plan.next_station_idx += 1
        self.assertNotEqual(baseline, self.checkpoint())

    def test_checkpoint_changes_for_python_and_numpy_rng(self):
        initial = self.checkpoint()
        self.env.mediator.context.python_random.random()
        after_python = self.checkpoint()
        self.assertNotEqual(initial, after_python)

        self.env.mediator.context.numpy_random.random()
        after_numpy = self.checkpoint()
        self.assertNotEqual(after_python, after_numpy)


if __name__ == "__main__":
    unittest.main()

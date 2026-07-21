import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.metro import Metro
from env import MiniMetroEnv, legacy_auto_assignment_step
from recursive_checkpoint import canonical_checkpoint, normalize_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"


def build_checkpoint_fixture(version):
    reward_mode = "line_credits_delta" if version == 1 else "deliveries"
    env = MiniMetroEnv(reward_mode=reward_mode)
    env.reset(seed=606)
    env.mediator.max_waiting_passengers = version
    legacy_auto_assignment_step(
        env,
        {"type": "create_path", "stations": [0, 1, 2], "loop": False},
        dt_ms=17,
    )
    checkpoint = canonical_checkpoint(env, schema_version=version)
    return (
        json.dumps(
            checkpoint,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def build_env_with_path(*, reward_mode="deliveries", seed=613):
    env = MiniMetroEnv(reward_mode=reward_mode)
    env.reset(seed=seed)
    observation, _, _, info = env.step(
        {"type": "create_path", "stations": [0, 1, 2], "loop": False},
        dt_ms=0,
    )
    if not info["action_ok"]:
        raise AssertionError("checkpoint fixture path creation failed")
    observation, _, _, info = env.step(
        {"type": "assign_locomotive", "path_index": 0},
        dt_ms=0,
    )
    if not info["action_ok"]:
        raise AssertionError("checkpoint fixture locomotive assignment failed")
    return env, observation


class TestGM06bCheckpointContract(unittest.TestCase):
    def test_frozen_v1_v2_generation_bytes_match_the_pre_change_baseline(self):
        for version in (1, 2):
            with self.subTest(version=version):
                expected = (FIXTURE_ROOT / f"checkpoint-v{version}.json").read_text(
                    encoding="utf-8"
                )
                self.assertEqual(build_checkpoint_fixture(version), expected)

    def test_runtime_observation_exposes_exact_queue_state_and_complete_fleet(self):
        env, observation = build_env_with_path()
        metro = env.mediator.metros[0]

        self.assertTrue(hasattr(metro, "is_unassignment_queued"))
        self.assertIs(type(metro.is_unassignment_queued), bool)
        self.assertFalse(metro.is_unassignment_queued)
        self.assertIs(
            type(observation["structured"]["metros"][0]["unassignment_queued"]), bool
        )
        self.assertFalse(observation["structured"]["metros"][0]["unassignment_queued"])
        self.assertEqual(
            observation["structured"]["fleet"],
            {
                "locomotives_total": env.mediator.num_metros,
                "locomotives_assigned": 1,
                "locomotives_available": env.mediator.num_metros - 1,
                "locomotives_queued": 0,
                "carriages_total": env.mediator.num_carriages,
                "carriages_assigned": 0,
                "carriages_available": env.mediator.num_carriages,
            },
        )

    def test_default_checkpoint_v4_has_complete_fleet_and_two_queue_encodings(self):
        env, _ = build_env_with_path()
        checkpoint = canonical_checkpoint(env)

        self.assertEqual(checkpoint["schemaVersion"], 4)
        fleet = checkpoint["structured"]["fleet"]
        self.assertEqual(
            fleet,
            {
                "locomotives_total": env.mediator.num_metros,
                "locomotives_assigned": 1,
                "locomotives_available": env.mediator.num_metros - 1,
                "locomotives_queued": 0,
                "carriages_total": env.mediator.num_carriages,
                "carriages_assigned": 0,
                "carriages_available": env.mediator.num_carriages,
            },
        )
        self.assertIs(
            type(checkpoint["structured"]["metros"][0]["unassignment_queued"]),
            bool,
        )
        self.assertIs(type(checkpoint["metroMotion"][0]["unassignment_queued"]), bool)

    def test_queued_prefix_is_counted_and_old_checkpoint_generation_refuses_it(self):
        for version, reward_mode in ((1, "line_credits_delta"), (2, "deliveries")):
            with self.subTest(version=version):
                env, _ = build_env_with_path(
                    reward_mode=reward_mode, seed=617 + version
                )
                env.mediator.metros[0].is_unassignment_queued = True

                with self.assertRaises(ValueError):
                    canonical_checkpoint(env, schema_version=version)

                current = canonical_checkpoint(env)
                self.assertTrue(
                    current["structured"]["metros"][0]["unassignment_queued"]
                )
                self.assertTrue(current["metroMotion"][0]["unassignment_queued"])
                self.assertEqual(
                    current["structured"]["fleet"]["locomotives_queued"], 1
                )

    def test_queued_path_only_suffix_is_persisted_but_not_counted_and_blocks_v1_v2(
        self,
    ):
        for version, reward_mode in ((1, "line_credits_delta"), (2, "deliveries")):
            with self.subTest(version=version):
                env, _ = build_env_with_path(
                    reward_mode=reward_mode, seed=619 + version
                )
                path = env.mediator.paths[0]
                suffix = Metro()
                path.add_metro(suffix)
                suffix.is_unassignment_queued = True

                self.assertNotIn(suffix, env.mediator.metros)
                current = canonical_checkpoint(env)
                self.assertEqual(current["schemaVersion"], 4)
                prefix_length = len(current["structured"]["metros"])
                self.assertEqual(len(current["metroMotion"]), prefix_length + 1)
                self.assertIn(
                    "unassignment_queued", current["metroMotion"][prefix_length]
                )
                self.assertTrue(
                    current["metroMotion"][prefix_length]["unassignment_queued"]
                )
                self.assertEqual(
                    current["structured"]["fleet"]["locomotives_queued"], 0
                )
                with self.assertRaises(ValueError):
                    canonical_checkpoint(env, schema_version=version)

    def test_v1_v2_normalization_is_immutable_and_synthesizes_false_queue_state(self):
        for version in (1, 2):
            with self.subTest(version=version):
                legacy = json.loads(
                    (FIXTURE_ROOT / f"checkpoint-v{version}.json").read_text(
                        encoding="utf-8"
                    )
                )
                before = deepcopy(legacy)

                normalized = normalize_checkpoint(legacy)

                self.assertEqual(legacy, before)
                self.assertEqual(normalized["schemaVersion"], 4)
                self.assertTrue(
                    all(
                        item["unassignment_queued"] is False
                        for item in normalized["structured"]["metros"]
                    )
                )
                self.assertTrue(
                    all(
                        item["unassignment_queued"] is False
                        for item in normalized["metroMotion"]
                    )
                )
                total = normalized["progression"]["limits"]["num_metros"]
                assigned = len(normalized["structured"]["metros"])
                self.assertEqual(
                    normalized["structured"]["fleet"],
                    {
                        "locomotives_total": total,
                        "locomotives_assigned": assigned,
                        "locomotives_available": max(0, total - assigned),
                        "locomotives_queued": 0,
                        "carriages_total": 0,
                        "carriages_assigned": 0,
                        "carriages_available": 0,
                    },
                )

    def test_v3_normalizer_rejects_every_fleet_alias_or_prefix_disagreement(self):
        env, _ = build_env_with_path(seed=623)
        valid = canonical_checkpoint(env, schema_version=3)
        self.assertEqual(valid["schemaVersion"], 3)
        self.assertEqual(normalize_checkpoint(valid)["schemaVersion"], 4)

        def total_alias(value):
            fleet = value["structured"]["fleet"]
            fleet["locomotives_total"] += 1
            fleet["locomotives_available"] += 1

        mutations = {
            "boolean queue": lambda value: value["metroMotion"][0].__setitem__(
                "unassignment_queued", 1
            ),
            "total alias": total_alias,
            "assigned count": lambda value: value["structured"]["fleet"].__setitem__(
                "locomotives_assigned", 2
            ),
            "available formula": lambda value: value["structured"]["fleet"].__setitem__(
                "locomotives_available", 99
            ),
            "queued count": lambda value: value["structured"]["fleet"].__setitem__(
                "locomotives_queued", 1
            ),
            "declared path": lambda value: value["metroMotion"][0].__setitem__(
                "declared_path_index", None
            ),
            "position": lambda value: value["metroMotion"][0].__setitem__(
                "position", [1, 2]
            ),
            "station": lambda value: value["metroMotion"][0].__setitem__(
                "current_station_index", 0
            ),
            "passengers": lambda value: value["metroMotion"][0].__setitem__(
                "passenger_indices", [0]
            ),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(valid)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                normalize_checkpoint(candidate)

    def test_v3_generation_rejects_a_stale_caller_observation(self):
        env = MiniMetroEnv()
        stale = env.reset(seed=631)
        env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
            dt_ms=0,
        )
        env.step({"type": "assign_locomotive", "path_index": 0}, dt_ms=0)

        with self.assertRaises(ValueError):
            canonical_checkpoint(env, stale)

    def test_v3_normalizer_rejects_a_swapped_global_motion_prefix(self):
        env, _ = build_env_with_path(seed=641)
        path = env.mediator.paths[0]
        second = Metro()
        path.add_metro(second)
        env.mediator.metros.append(second)
        second.position.left += 19
        valid = canonical_checkpoint(env)
        self.assertEqual(len(valid["structured"]["metros"]), 2)

        swapped = deepcopy(valid)
        swapped["metroMotion"][0], swapped["metroMotion"][1] = (
            swapped["metroMotion"][1],
            swapped["metroMotion"][0],
        )
        with self.assertRaises(ValueError):
            normalize_checkpoint(swapped)


if __name__ == "__main__":
    unittest.main()

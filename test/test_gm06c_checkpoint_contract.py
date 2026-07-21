import importlib
import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import recursive_checkpoint_schema as checkpoint_schema
from entity.metro import Metro
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint, normalize_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"


def jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def apply(env, action):
    observation, _, _, info = env.step(action, dt_ms=0)
    if not info["action_ok"]:
        raise AssertionError(f"fixture action was rejected: {action!r}")
    return observation


def attached_env(*, count=1, metros=1, seed=701):
    env = MiniMetroEnv()
    env.reset(seed=seed)
    apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    for _ in range(metros):
        observation = apply(env, {"type": "assign_locomotive", "path_index": 0})
    env.mediator.num_carriages = max(env.mediator.num_carriages, count)
    before_arrays = deepcopy(observation["arrays"])
    for _ in range(count):
        observation = apply(env, {"type": "attach_carriage", "path_index": 0})
    return env, observation, before_arrays


def new_carriage():
    module = importlib.import_module("entity.carriage")
    return module.Carriage()


def add_path_only_suffix(env, *, queued=True):
    path = env.mediator.paths[0]
    suffix = Metro()
    path.add_metro(suffix)
    suffix.is_unassignment_queued = queued
    suffix.carriages.append(new_carriage())
    return suffix


def assert_uuid_free(case, value):
    if isinstance(value, dict):
        for key, item in value.items():
            case.assertNotEqual(key, "id")
            case.assertFalse(key.endswith("_id"), key)
            case.assertFalse(key.endswith("_ids"), key)
            assert_uuid_free(case, item)
    elif isinstance(value, list):
        for item in value:
            assert_uuid_free(case, item)
    elif isinstance(value, str):
        for prefix in ("Metro-", "Carriage-", "Path-", "Station-", "Passenger-"):
            case.assertNotIn(prefix, value)


def assert_checkpoint_bijection(case, checkpoint):
    top = checkpoint["carriages"]
    motion = checkpoint["metroMotion"]
    record_keys = {"capacity", "metro_motion_index", "attachment_index"}
    cursor = 0
    for metro_index, metro in enumerate(motion):
        expected = list(range(cursor, cursor + len(metro["carriage_indices"])))
        case.assertEqual(metro["carriage_indices"], expected)
        for attachment_index, carriage_index in enumerate(expected):
            carriage = top[carriage_index]
            case.assertEqual(set(carriage), record_keys)
            case.assertEqual(carriage["metro_motion_index"], metro_index)
            case.assertEqual(carriage["attachment_index"], attachment_index)
        cursor += len(expected)
    case.assertEqual(cursor, len(top))

    structured = checkpoint["structured"]
    global_count = len(structured["metros"])
    global_carriage_count = sum(
        len(metro["carriage_indices"]) for metro in motion[:global_count]
    )
    case.assertEqual(len(structured["carriages"]), global_carriage_count)
    case.assertEqual(structured["carriages"], top[:global_carriage_count])
    for carriage in structured["carriages"]:
        case.assertEqual(set(carriage), record_keys)
    for index, metro in enumerate(structured["metros"]):
        case.assertEqual(metro["carriage_indices"], motion[index]["carriage_indices"])
        case.assertEqual(metro["capacity"], motion[index]["capacity"])
        for carriage_index in metro["carriage_indices"]:
            case.assertGreaterEqual(carriage_index, 0)
            case.assertLess(carriage_index, global_carriage_count)
    for metro in motion[global_count:]:
        for carriage_index in metro["carriage_indices"]:
            case.assertGreaterEqual(carriage_index, global_carriage_count)
    assert_uuid_free(case, checkpoint)


class TestGM06cStructuredObservation(unittest.TestCase):
    def test_raw_observation_exposes_exact_composition_without_changing_arrays(self):
        env, observation, before_arrays = attached_env(count=1)
        metro = env.mediator.metros[0]
        carriage = metro.carriages[0]
        structured = observation["structured"]

        self.assertEqual(jsonable(observation["arrays"]), jsonable(before_arrays))
        self.assertEqual(structured["metros"][0]["capacity"], 12)
        self.assertEqual(structured["metros"][0]["carriage_ids"], [carriage.id])
        self.assertEqual(
            structured["carriages"],
            [
                {
                    "id": carriage.id,
                    "capacity": 6,
                    "metro_id": metro.id,
                    "attachment_index": 0,
                }
            ],
        )
        self.assertEqual(
            structured["fleet"],
            {
                "locomotives_total": env.mediator.num_metros,
                "locomotives_assigned": 1,
                "locomotives_available": env.mediator.num_metros - 1,
                "locomotives_queued": 0,
                "carriages_total": 2,
                "carriages_assigned": 1,
                "carriages_available": 1,
            },
        )

    def test_raw_carriages_flatten_by_global_metro_then_attachment_order(self):
        env, observation, _ = attached_env(count=4, metros=2, seed=702)
        metros = env.mediator.metros
        expected = [carriage for metro in metros for carriage in metro.carriages]
        structured = observation["structured"]

        self.assertEqual([len(metro.carriages) for metro in metros], [2, 2])
        self.assertEqual(
            [metro["carriage_ids"] for metro in structured["metros"]],
            [[carriage.id for carriage in metro.carriages] for metro in metros],
        )
        self.assertEqual(
            structured["carriages"],
            [
                {
                    "id": carriage.id,
                    "capacity": carriage.capacity,
                    "metro_id": metro.id,
                    "attachment_index": attachment_index,
                }
                for metro in metros
                for attachment_index, carriage in enumerate(metro.carriages)
            ],
        )
        self.assertEqual(
            [item["id"] for item in structured["carriages"]],
            [carriage.id for carriage in expected],
        )

    def test_checkpoint_v4_is_uuid_free_and_bijective_across_motion_suffix(self):
        env, _, _ = attached_env(count=2, seed=703)
        suffix = add_path_only_suffix(env)
        checkpoint = canonical_checkpoint(env, schema_version=4)

        self.assertEqual(checkpoint["schemaVersion"], 4)
        self.assertEqual(checkpoint["progression"]["limits"]["num_carriages"], 2)
        self.assertEqual(len(checkpoint["structured"]["carriages"]), 2)
        self.assertEqual(len(checkpoint["carriages"]), 3)
        self.assertEqual(len(checkpoint["metroMotion"]), 2)
        self.assertEqual(
            set(checkpoint["carriages"][0]),
            {"capacity", "metro_motion_index", "attachment_index"},
        )
        self.assertEqual(checkpoint["metroMotion"][0]["base_capacity"], 6)
        self.assertEqual(checkpoint["metroMotion"][0]["capacity"], 18)
        self.assertEqual(checkpoint["metroMotion"][1]["capacity"], 12)
        self.assertEqual(checkpoint["structured"]["fleet"]["carriages_assigned"], 2)
        assert_checkpoint_bijection(self, checkpoint)

        encoded = json.dumps(checkpoint, allow_nan=False, sort_keys=True)
        entities = [
            *env.mediator.metros,
            suffix,
            *(
                item
                for metro in [*env.mediator.metros, suffix]
                for item in metro.carriages
            ),
        ]
        for entity in entities:
            self.assertNotIn(entity.id, encoded)
        self.assertNotIn("_id_to_index", encoded)
        self.assertEqual(normalize_checkpoint(checkpoint), checkpoint)

    def test_v4_generation_rejects_nonqueued_path_only_motion_divergence(self):
        env, _, _ = attached_env(count=1, seed=705)
        suffix = add_path_only_suffix(env, queued=False)

        self.assertNotIn(suffix, env.mediator.metros)
        with self.assertRaises(ValueError):
            canonical_checkpoint(env, schema_version=4)

    def test_v4_generation_rejects_every_stale_composition_observation(self):
        env, stale, _ = attached_env(count=1, seed=709)
        apply(env, {"type": "attach_carriage", "path_index": 0})
        with self.assertRaises(ValueError):
            canonical_checkpoint(env, stale, schema_version=4)

        current = env.observe()
        mutations = {
            "metro capacity": lambda value: value["structured"]["metros"][
                0
            ].__setitem__("capacity", 99),
            "metro carriage order": lambda value: value["structured"]["metros"][0][
                "carriage_ids"
            ].reverse(),
            "carriage order": lambda value: value["structured"]["carriages"].reverse(),
            "carriage capacity": lambda value: value["structured"]["carriages"][
                0
            ].__setitem__("capacity", 7),
            "carriage owner": lambda value: value["structured"]["carriages"][
                0
            ].__setitem__("metro_id", ""),
            "carriage id": lambda value: value["structured"]["carriages"][
                0
            ].__setitem__("id", ""),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(current)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                canonical_checkpoint(env, candidate, schema_version=4)

    def test_v4_normalizer_rejects_orphans_owner_mismatch_and_invalid_scalars(self):
        env, _, _ = attached_env(count=2, seed=719)
        add_path_only_suffix(env)
        valid = canonical_checkpoint(env, schema_version=4)

        mutations = {
            "orphan suffix": lambda value: value["metroMotion"][1].__setitem__(
                "carriage_indices", []
            ),
            "wrong owner": lambda value: value["carriages"][-1].__setitem__(
                "metro_motion_index", 0
            ),
            "wrong attachment index": lambda value: value["carriages"][-1].__setitem__(
                "attachment_index", 4
            ),
            "duplicate reference": lambda value: value["metroMotion"][0][
                "carriage_indices"
            ].__setitem__(1, 0),
            "out of range": lambda value: value["metroMotion"][0][
                "carriage_indices"
            ].__setitem__(0, 99),
            "zero carriage capacity": lambda value: value["carriages"][0].__setitem__(
                "capacity", 0
            ),
            "boolean base capacity": lambda value: value["metroMotion"][0].__setitem__(
                "base_capacity", True
            ),
            "structured prefix reorder": lambda value: value["structured"][
                "carriages"
            ].reverse(),
            "structured metro capacity": lambda value: value["structured"]["metros"][
                0
            ].__setitem__("capacity", 99),
            "fleet formula": lambda value: value["structured"]["fleet"].__setitem__(
                "carriages_available", 99
            ),
            "nonqueued path-only suffix": lambda value: value["metroMotion"][
                1
            ].__setitem__("unassignment_queued", False),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(valid)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                normalize_checkpoint(candidate)


class TestGM06cCheckpointCompatibility(unittest.TestCase):
    def test_version_aliases_advance_without_renaming_history(self):
        self.assertEqual(checkpoint_schema.CHECKPOINT_SCHEMA_VERSION_V1, 1)
        self.assertEqual(checkpoint_schema.CHECKPOINT_SCHEMA_VERSION_V2, 2)
        self.assertEqual(checkpoint_schema.CHECKPOINT_SCHEMA_VERSION_V3, 3)
        self.assertEqual(checkpoint_schema.CHECKPOINT_SCHEMA_VERSION_V4, 4)
        self.assertEqual(checkpoint_schema.CHECKPOINT_SCHEMA_VERSION, 4)

    def test_legacy_normalization_synthesizes_exact_zero_carriage_v4_state(self):
        for version in (1, 2, 3):
            with self.subTest(version=version):
                legacy = json.loads(
                    (FIXTURE_ROOT / f"checkpoint-v{version}.json").read_text()
                )
                before = deepcopy(legacy)
                normalized = normalize_checkpoint(legacy)
                self.assertEqual(legacy, before)
                self.assertEqual(normalized["schemaVersion"], 4)
                self.assertEqual(normalized["carriages"], [])
                self.assertEqual(normalized["structured"]["carriages"], [])
                self.assertEqual(
                    normalized["progression"]["limits"]["num_carriages"], 0
                )
                fleet = normalized["structured"]["fleet"]
                self.assertEqual(fleet["carriages_total"], 0)
                self.assertEqual(fleet["carriages_assigned"], 0)
                self.assertEqual(fleet["carriages_available"], 0)
                for metro, motion in zip(
                    normalized["structured"]["metros"],
                    normalized["metroMotion"],
                    strict=True,
                ):
                    self.assertEqual(metro["carriage_indices"], [])
                    self.assertEqual(metro["capacity"], motion["capacity"])
                    self.assertEqual(motion["carriage_indices"], [])
                    self.assertEqual(motion["base_capacity"], motion["capacity"])

    def test_legacy_normalizers_reject_every_forward_carriage_field(self):
        def mutations(value):
            result = {
                "top-level carriages": lambda item: item.__setitem__("carriages", []),
                "structured carriages": lambda item: item["structured"].__setitem__(
                    "carriages", []
                ),
                "carriage limit": lambda item: item["progression"][
                    "limits"
                ].__setitem__("num_carriages", 0),
                "structured metro capacity": lambda item: item["structured"]["metros"][
                    0
                ].__setitem__("capacity", 6),
                "structured metro references": lambda item: item["structured"][
                    "metros"
                ][0].__setitem__("carriage_indices", []),
                "motion base": lambda item: item["metroMotion"][0].__setitem__(
                    "base_capacity", 6
                ),
                "motion references": lambda item: item["metroMotion"][0].__setitem__(
                    "carriage_indices", []
                ),
            }
            for field in (
                "carriages_total",
                "carriages_assigned",
                "carriages_available",
            ):
                if "fleet" in value["structured"]:
                    result[f"fleet {field}"] = lambda item, field=field: item[
                        "structured"
                    ]["fleet"].__setitem__(field, 0)
                else:
                    result[f"forward fleet {field}"] = lambda item, field=field: item[
                        "structured"
                    ].__setitem__("fleet", {field: 0})
            return result

        for version in (1, 2, 3):
            legacy = json.loads(
                (FIXTURE_ROOT / f"checkpoint-v{version}.json").read_text()
            )
            for name, mutate in mutations(legacy).items():
                candidate = deepcopy(legacy)
                mutate(candidate)
                with (
                    self.subTest(version=version, field=name),
                    self.assertRaises(ValueError),
                ):
                    normalize_checkpoint(candidate)

    def test_direct_v3_validator_rejects_every_forward_carriage_surface(self):
        legacy = json.loads((FIXTURE_ROOT / "checkpoint-v3.json").read_text())
        checkpoint_schema.validate_checkpoint_v3(legacy)
        mutations = {
            "top-level carriages": lambda item: item.__setitem__("carriages", []),
            "structured carriages": lambda item: item["structured"].__setitem__(
                "carriages", []
            ),
            "carriage limit": lambda item: item["progression"]["limits"].__setitem__(
                "num_carriages", 0
            ),
            "carriage fleet": lambda item: item["structured"]["fleet"].__setitem__(
                "carriages_total", 0
            ),
            "structured capacity": lambda item: item["structured"]["metros"][
                0
            ].__setitem__("capacity", 6),
            "structured references": lambda item: item["structured"]["metros"][
                0
            ].__setitem__("carriage_indices", []),
            "structured ids": lambda item: item["structured"]["metros"][0].__setitem__(
                "carriage_ids", []
            ),
            "motion base": lambda item: item["metroMotion"][0].__setitem__(
                "base_capacity", 6
            ),
            "motion references": lambda item: item["metroMotion"][0].__setitem__(
                "carriage_indices", []
            ),
            "motion ids": lambda item: item["metroMotion"][0].__setitem__(
                "carriage_ids", []
            ),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(legacy)
            mutate(candidate)
            with self.subTest(field=name), self.assertRaises(ValueError):
                checkpoint_schema.validate_checkpoint_v3(candidate)

    def test_legacy_generation_refuses_global_and_path_only_attachments(self):
        for version in (1, 2, 3):
            reward = "line_credits_delta" if version == 1 else "deliveries"
            with self.subTest(version=version, owner="global"):
                env = MiniMetroEnv(reward_mode=reward)
                env.reset(seed=730 + version)
                apply(
                    env,
                    {"type": "create_path", "stations": [0, 1, 2], "loop": False},
                )
                apply(env, {"type": "assign_locomotive", "path_index": 0})
                apply(env, {"type": "attach_carriage", "path_index": 0})
                with self.assertRaises(ValueError):
                    canonical_checkpoint(env, schema_version=version)

            with self.subTest(version=version, owner="path-only"):
                env = MiniMetroEnv(reward_mode=reward)
                env.reset(seed=740 + version)
                apply(
                    env,
                    {"type": "create_path", "stations": [0, 1, 2], "loop": False},
                )
                apply(env, {"type": "assign_locomotive", "path_index": 0})
                add_path_only_suffix(env)
                with self.assertRaises(ValueError):
                    canonical_checkpoint(env, schema_version=version)


if __name__ == "__main__":
    unittest.main()

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import recursive_contract
import recursive_playtest
from env import MiniMetroEnv
from recursive_playtest import (
    DELIVERIES_REWARD_CONTRACT,
    LINE_CREDITS_REWARD_CONTRACT,
    main,
    run_scenario,
    validate_inputs,
    validate_scenario,
)


def operation():
    return {
        "name": "noop",
        "action": {"type": "noop"},
        "expectedActionOk": True,
    }


def scenario(version, *, threshold=None):
    document = {
        "schemaVersion": version,
        "seed": 37,
        "defaultDtMs": 0,
        "operations": [operation()],
    }
    if version >= 2:
        document["environmentRewardContract"] = DELIVERIES_REWARD_CONTRACT
    if threshold is not None:
        document["overduePassengerThreshold"] = threshold
    return document


def recorded_inputs(version, *, threshold=None):
    document = {
        "schemaVersion": version,
        "runId": f"recorded-v{version}",
        "sourcePath": f"missing-v{version}-scenario.json",
        "seed": 37,
        "defaultDtMs": 0,
        "pythonExecutable": sys.executable,
        "pythonHashSeed": "37",
        "operations": [operation()],
    }
    if version >= 2:
        document["environmentRewardContract"] = DELIVERIES_REWARD_CONTRACT
    if threshold is not None:
        document["overduePassengerThreshold"] = threshold
    return document


def checkpoint_threshold(checkpoint):
    limits = checkpoint["progression"]["limits"]
    return limits.get("overdue_passenger_threshold", limits["max_waiting_passengers"])


class TestRecursiveThresholdSchema(unittest.TestCase):
    def test_schema_versions_have_immutable_names_and_current_v4_alias(self):
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V1", None), 1)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V2", None), 2)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V3", None), 3)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V4", None), 4)
        self.assertEqual(recursive_contract.LEGACY_SCHEMA_VERSION, 1)
        self.assertEqual(recursive_contract.SCHEMA_VERSION, 4)
        self.assertEqual(recursive_playtest.LEGACY_SCHEMA_VERSION, 1)
        self.assertEqual(recursive_playtest.SCHEMA_VERSION, 4)

    def test_v1_v2_and_v3_scenarios_are_supported_with_exact_versioned_keys(self):
        documents = (
            scenario(1),
            scenario(2),
            scenario(3, threshold=2),
        )

        for document in documents:
            with self.subTest(version=document["schemaVersion"]):
                self.assertEqual(validate_scenario(document), document)

        for invalid in (
            {
                key: value
                for key, value in documents[2].items()
                if key != "overduePassengerThreshold"
            },
            {
                key: value
                for key, value in documents[2].items()
                if key != "environmentRewardContract"
            },
            {
                **documents[2],
                "environmentRewardContract": LINE_CREDITS_REWARD_CONTRACT,
            },
            {**documents[2], "extra": True},
            {**documents[1], "overduePassengerThreshold": 1},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_scenario(invalid)

    def test_v3_threshold_is_a_positive_non_boolean_integer(self):
        for invalid in (0, -1, True, False, 1.0, "2", None):
            document = scenario(3, threshold=invalid)
            if invalid is None:
                document["overduePassengerThreshold"] = None
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_scenario(document)

        self.assertEqual(
            validate_scenario(scenario(3, threshold=1))["overduePassengerThreshold"],
            1,
        )

    def test_v3_inputs_are_strict_and_validate_the_same_threshold_contract(self):
        document = recorded_inputs(3, threshold=2)
        self.assertEqual(validate_inputs(document), document)

        for invalid in (0, -1, True, 1.0, "2", None):
            candidate = {**document, "overduePassengerThreshold": invalid}
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_inputs(candidate)
        with self.assertRaises(ValueError):
            validate_inputs({**document, "extra": True})
        with self.assertRaises(ValueError):
            validate_inputs(
                {
                    **document,
                    "environmentRewardContract": LINE_CREDITS_REWARD_CONTRACT,
                }
            )
        with self.assertRaises(ValueError):
            validate_inputs(recorded_inputs(2, threshold=1))

    def test_each_scenario_reconstructs_reward_threshold_and_checkpoint_version(self):
        expected = {
            1: (LINE_CREDITS_REWARD_CONTRACT, 1, 1),
            2: (DELIVERIES_REWARD_CONTRACT, 1, 2),
            3: (DELIVERIES_REWARD_CONTRACT, 2, 2),
        }

        with patch.dict(os.environ, {"PYTHONHASHSEED": "37"}):
            for version, (
                reward_contract,
                threshold,
                checkpoint_version,
            ) in expected.items():
                with self.subTest(version=version):
                    document = scenario(
                        version,
                        threshold=threshold if version == 3 else None,
                    )
                    inputs, rows, findings, result = run_scenario(
                        document,
                        run_id=f"scenario-v{version}",
                        source_path=f"scenario-v{version}.json",
                    )
                    self.assertEqual(
                        rows[0]["checkpoint"]["schemaVersion"], checkpoint_version
                    )
                    self.assertEqual(
                        checkpoint_threshold(rows[0]["checkpoint"]), threshold
                    )
                    self.assertEqual(result["schemaVersion"], version)
                    self.assertEqual(findings, [])
                    if version == 1:
                        self.assertNotIn("environmentRewardContract", inputs)
                    else:
                        self.assertEqual(
                            inputs["environmentRewardContract"], reward_contract
                        )
                    if version == 3:
                        self.assertEqual(inputs["overduePassengerThreshold"], threshold)
                    else:
                        self.assertNotIn("overduePassengerThreshold", inputs)

    def test_threshold_is_applied_after_factories_replace_the_mediator(self):
        created = []

        class ReplacingResetEnv(MiniMetroEnv):
            def reset(self, seed=None):
                observation = super().reset(seed=seed)
                self.mediator.max_waiting_passengers = 99
                return observation

        def keyword_factory(*, reward_mode):
            env = ReplacingResetEnv(reward_mode=reward_mode)
            created.append(env)
            return env

        def zero_argument_factory():
            env = ReplacingResetEnv()
            created.append(env)
            return env

        with patch.dict(os.environ, {"PYTHONHASHSEED": "37"}):
            keyword_run = run_scenario(
                scenario(3, threshold=2),
                run_id="keyword-factory-v3",
                source_path="keyword-factory-v3.json",
                env_factory=keyword_factory,
            )
            zero_argument_run = run_scenario(
                scenario(3, threshold=2),
                run_id="zero-argument-factory-v3",
                source_path="zero-argument-factory-v3.json",
                env_factory=zero_argument_factory,
            )

        for artifacts in (keyword_run, zero_argument_run):
            checkpoint = artifacts[1][0]["checkpoint"]
            self.assertEqual(checkpoint_threshold(checkpoint), 2)
        self.assertEqual(
            [env.mediator.max_waiting_passengers for env in created],
            [2, 2],
        )

    def test_inputs_mode_reconstructs_literal_v2_and_v3(self):
        cases = (
            (recorded_inputs(2), 1),
            (recorded_inputs(3, threshold=2), 2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for document, expected_threshold in cases:
                version = document["schemaVersion"]
                with self.subTest(version=version):
                    input_path = Path(temp_dir, f"inputs-v{version}.json")
                    out_dir = Path(temp_dir, f"replay-v{version}")
                    input_path.write_text(json.dumps(document), encoding="utf-8")
                    with patch.dict(os.environ, {"PYTHONHASHSEED": "37"}):
                        result = main(
                            [
                                "--inputs",
                                str(input_path),
                                "--out",
                                str(out_dir),
                                "--run-id",
                                f"replay-v{version}",
                            ]
                        )
                    self.assertEqual(result, 0)
                    replayed = json.loads(
                        Path(out_dir, "inputs.json").read_text("utf-8")
                    )
                    row = json.loads(
                        Path(out_dir, "transcript.jsonl")
                        .read_text("utf-8")
                        .splitlines()[0]
                    )
                    self.assertEqual(replayed["schemaVersion"], version)
                    self.assertEqual(
                        replayed["environmentRewardContract"],
                        DELIVERIES_REWARD_CONTRACT,
                    )
                    self.assertEqual(row["checkpoint"]["schemaVersion"], 2)
                    self.assertEqual(
                        checkpoint_threshold(row["checkpoint"]), expected_threshold
                    )
                    if version == 3:
                        self.assertEqual(replayed["overduePassengerThreshold"], 2)
                    else:
                        self.assertNotIn("overduePassengerThreshold", replayed)


if __name__ == "__main__":
    unittest.main()

import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from recursive_playtest import (
    DELIVERIES_REWARD_CONTRACT,
    LINE_CREDITS_REWARD_CONTRACT,
    main,
    run_scenario,
    validate_inputs,
    validate_scenario,
)


def scenario(*operations, schema_version=1, reward_contract=None):
    document = {
        "schemaVersion": schema_version,
        "seed": 123,
        "defaultDtMs": 7,
        "operations": list(operations)
        or [
            {
                "name": "noop",
                "action": {"type": "noop"},
                "expectedActionOk": True,
            }
        ],
    }
    if reward_contract is not None:
        document["environmentRewardContract"] = reward_contract
    elif schema_version == 2:
        document["environmentRewardContract"] = DELIVERIES_REWARD_CONTRACT
    return document


def operation(name="noop", action=None, expected=True, **extra):
    return {
        "name": name,
        "action": {"type": "noop"} if action is None else action,
        "expectedActionOk": expected,
        **extra,
    }


class TestScenarioValidation(unittest.TestCase):
    def test_valid_scenario_is_json_deep_copied(self):
        original = scenario(
            operation(
                "create-line",
                {"type": "create_path", "stations": [0, 1], "loop": False},
                dtMs=0,
            )
        )

        validated = validate_scenario(original)
        original["operations"][0]["action"]["stations"][0] = 99

        self.assertEqual(validated["operations"][0]["action"]["stations"], [0, 1])
        self.assertIsNot(validated, original)

    def test_v2_scenario_requires_the_delivery_reward_contract(self):
        document = scenario(schema_version=2)

        self.assertEqual(validate_scenario(document), document)
        for invalid in (
            {
                key: value
                for key, value in document.items()
                if key != "environmentRewardContract"
            },
            {**document, "environmentRewardContract": LINE_CREDITS_REWARD_CONTRACT},
            {**document, "environmentRewardContract": True},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_scenario(invalid)

        with self.assertRaises(ValueError):
            validate_scenario(
                scenario(
                    schema_version=1,
                    reward_contract=LINE_CREDITS_REWARD_CONTRACT,
                )
            )

    def test_scenario_contract_is_strict(self):
        invalid_documents = {
            "wrong version": {**scenario(), "schemaVersion": 3},
            "boolean version": {**scenario(), "schemaVersion": True},
            "negative seed": {**scenario(), "seed": -1},
            "oversized seed": {**scenario(), "seed": 4_294_967_296},
            "boolean seed": {**scenario(), "seed": True},
            "negative default dt": {**scenario(), "defaultDtMs": -1},
            "boolean default dt": {**scenario(), "defaultDtMs": False},
            "empty operations": {**scenario(), "operations": []},
            "unknown scenario key": {**scenario(), "extra": 1},
            "blank name": scenario(operation(" ")),
            "duplicate names": scenario(operation("same"), operation("same")),
            "negative operation dt": scenario(operation(dtMs=-1)),
            "boolean operation dt": scenario(operation(dtMs=True)),
            "non-boolean expectation": scenario(operation(expected=1)),
            "unknown operation key": scenario(operation(extra=1)),
            "non-finite action": scenario(
                operation(action={"type": "noop", "x": math.nan})
            ),
        }

        for label, document in invalid_documents.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                validate_scenario(document)

    def test_recorded_inputs_contract_is_strict(self):
        document = {
            "schemaVersion": 1,
            "runId": "original-run",
            "sourcePath": "missing-but-recorded.json",
            "seed": 4,
            "defaultDtMs": 3,
            "pythonExecutable": "python",
            "pythonHashSeed": "4",
            "operations": [operation()],
        }

        self.assertEqual(validate_inputs(document), document)
        for field, value in (
            ("runId", ""),
            ("sourcePath", ""),
            ("pythonExecutable", ""),
            ("pythonHashSeed", 4),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_inputs({**document, field: value})
        with self.assertRaises(ValueError):
            validate_inputs({**document, "extra": True})
        with self.assertRaises(ValueError):
            validate_inputs({**document, "schemaVersion": True})
        for invalid_hash_seed in ("random", "4294967296"):
            with self.subTest(python_hash_seed=invalid_hash_seed):
                with self.assertRaises(ValueError):
                    validate_inputs({**document, "pythonHashSeed": invalid_hash_seed})

    def test_v2_recorded_inputs_require_the_delivery_reward_contract(self):
        document = {
            "schemaVersion": 2,
            "runId": "v2-run",
            "sourcePath": "scenario-v2.json",
            "seed": 4,
            "defaultDtMs": 3,
            "pythonExecutable": "python",
            "pythonHashSeed": "4",
            "environmentRewardContract": DELIVERIES_REWARD_CONTRACT,
            "operations": [operation()],
        }

        self.assertEqual(validate_inputs(document), document)
        for invalid in (
            {
                key: value
                for key, value in document.items()
                if key != "environmentRewardContract"
            },
            {**document, "environmentRewardContract": LINE_CREDITS_REWARD_CONTRACT},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_inputs(invalid)


class TestDrive(unittest.TestCase):
    def test_cli_writes_one_strict_transcript_row_per_operation(self):
        document = scenario(
            operation(
                "create-line",
                {"type": "create_path", "stations": [0, 1], "loop": False},
            ),
            operation("pause", {"type": "pause"}, dtMs=11),
            operation("paused-noop"),
            operation("resume", {"type": "resume"}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario_path = Path(temp_dir, "scenario.json")
            out_dir = Path(temp_dir, "run")
            scenario_path.write_text(json.dumps(document), encoding="utf-8")

            with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
                result = main(
                    [
                        "--scenario",
                        str(scenario_path),
                        "--out",
                        str(out_dir),
                        "--run-id",
                        "test-run",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(
                {path.name for path in out_dir.iterdir()},
                {
                    "inputs.json",
                    "transcript.jsonl",
                    "findings.authored.json",
                    "run-result.json",
                },
            )
            inputs = json.loads(Path(out_dir, "inputs.json").read_text("utf-8"))
            rows = [
                json.loads(line)
                for line in Path(out_dir, "transcript.jsonl")
                .read_text("utf-8")
                .splitlines()
            ]
            findings = json.loads(
                Path(out_dir, "findings.authored.json").read_text("utf-8")
            )
            run_result = json.loads(Path(out_dir, "run-result.json").read_text("utf-8"))

            self.assertEqual(len(rows), len(document["operations"]))
            self.assertEqual(inputs["runId"], "test-run")
            self.assertEqual(rows[1]["requestedDtMs"], 11)
            self.assertEqual(rows[1]["effectiveDtMs"], 11)
            self.assertEqual(rows[2]["requestedDtMs"], None)
            self.assertEqual(rows[2]["effectiveDtMs"], document["defaultDtMs"])
            self.assertEqual(findings, [])
            self.assertEqual(run_result["transcriptRows"], 4)
            self.assertTrue(run_result["completed"])
            for artifact in out_dir.iterdir():
                text = artifact.read_text("utf-8")
                self.assertNotIn("NaN", text)
                self.assertNotIn("Infinity", text)

    def test_inputs_mode_replays_without_reading_source_path(self):
        recorded = {
            "schemaVersion": 1,
            "runId": "first-run",
            "sourcePath": "this-file-does-not-exist.json",
            "seed": 8,
            "defaultDtMs": 1,
            "pythonExecutable": sys.executable,
            "pythonHashSeed": "8",
            "operations": [operation()],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir, "recorded.json")
            out_dir = Path(temp_dir, "replay")
            input_path.write_text(json.dumps(recorded), encoding="utf-8")

            with patch.dict(os.environ, {"PYTHONHASHSEED": "8"}):
                result = main(
                    [
                        "--inputs",
                        str(input_path),
                        "--out",
                        str(out_dir),
                        "--run-id",
                        "replay-run",
                    ]
                )

            self.assertEqual(result, 0)
            replay_inputs = json.loads(Path(out_dir, "inputs.json").read_text("utf-8"))
            self.assertEqual(replay_inputs["sourcePath"], recorded["sourcePath"])
            self.assertEqual(replay_inputs["runId"], "replay-run")

    def test_v2_inputs_mode_preserves_the_delivery_reward_contract(self):
        recorded = {
            "schemaVersion": 2,
            "runId": "first-v2-run",
            "sourcePath": "missing-v2-scenario.json",
            "seed": 18,
            "defaultDtMs": 1,
            "pythonExecutable": sys.executable,
            "pythonHashSeed": "18",
            "environmentRewardContract": DELIVERIES_REWARD_CONTRACT,
            "operations": [operation()],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir, "recorded-v2.json")
            out_dir = Path(temp_dir, "replay-v2")
            input_path.write_text(json.dumps(recorded), encoding="utf-8")

            with patch.dict(os.environ, {"PYTHONHASHSEED": "18"}):
                result = main(
                    [
                        "--inputs",
                        str(input_path),
                        "--out",
                        str(out_dir),
                        "--run-id",
                        "replay-v2-run",
                    ]
                )

            self.assertEqual(result, 0)
            replay_inputs = json.loads(Path(out_dir, "inputs.json").read_text("utf-8"))
            self.assertEqual(replay_inputs["schemaVersion"], 2)
            self.assertEqual(
                replay_inputs["environmentRewardContract"],
                DELIVERIES_REWARD_CONTRACT,
            )
            row = json.loads(
                Path(out_dir, "transcript.jsonl").read_text("utf-8").splitlines()[0]
            )
            self.assertEqual(row["checkpoint"]["schemaVersion"], 2)

    def test_reward_contract_preserves_v1_purchase_penalty_and_v2_delivery_reward(self):
        class FundedEnv(MiniMetroEnv):
            def __init__(self, *, reward_mode):
                super().__init__(reward_mode=reward_mode)

            def reset(self, seed=None):
                super().reset(seed=seed)
                self.mediator.score = 100
                self.last_score = 100
                self.last_line_credits = 100
                self.last_deliveries = self.mediator.total_travels_handled
                return self.observe()

        purchase = operation("buy-line", {"type": "buy_line"})
        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            legacy = run_scenario(
                scenario(purchase),
                run_id="legacy-buy",
                source_path="legacy-v1.json",
                env_factory=FundedEnv,
            )
            current = run_scenario(
                scenario(purchase, schema_version=2),
                run_id="deliveries-buy",
                source_path="current-v2.json",
                env_factory=FundedEnv,
            )

        legacy_inputs, legacy_rows, legacy_findings, legacy_result = legacy
        current_inputs, current_rows, current_findings, current_result = current
        self.assertNotIn("environmentRewardContract", legacy_inputs)
        self.assertEqual(legacy_rows[0]["reward"], -90)
        self.assertEqual(legacy_rows[0]["checkpoint"]["schemaVersion"], 1)
        self.assertEqual(legacy_findings, [])
        self.assertEqual(legacy_result["schemaVersion"], 1)
        self.assertEqual(
            current_inputs["environmentRewardContract"],
            DELIVERIES_REWARD_CONTRACT,
        )
        self.assertEqual(current_rows[0]["reward"], 0)
        self.assertEqual(current_rows[0]["checkpoint"]["schemaVersion"], 2)
        self.assertEqual(current_findings, [])
        self.assertEqual(current_result["schemaVersion"], 2)

    def test_run_scenario_preserves_zero_argument_environment_factories(self):
        created = []

        def factory():
            env = MiniMetroEnv()
            created.append(env)
            return env

        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            run_scenario(
                scenario(),
                run_id="legacy-zero-argument-factory",
                source_path="legacy-zero-argument-factory.json",
                env_factory=factory,
            )
            run_scenario(
                scenario(schema_version=2),
                run_id="v2-zero-argument-factory",
                source_path="v2-zero-argument-factory.json",
                env_factory=factory,
            )

        self.assertEqual(
            [env.reward_mode for env in created],
            [LINE_CREDITS_REWARD_CONTRACT, DELIVERIES_REWARD_CONTRACT],
        )


if __name__ == "__main__":
    unittest.main()

import json
import math
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from recursive_playtest import (
    canonical_checkpoint,
    main,
    validate_inputs,
    validate_scenario,
)


def scenario(*operations):
    return {
        "schemaVersion": 1,
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

    def test_scenario_contract_is_strict(self):
        invalid_documents = {
            "wrong version": {**scenario(), "schemaVersion": 2},
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
        self.assertEqual(checkpoint["schemaVersion"], 1)
        self.assertIn("structured", checkpoint)
        self.assertIn("arrays", checkpoint)
        self.assertIn("rng", checkpoint)

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
        random.random()
        after_python = self.checkpoint()
        self.assertNotEqual(initial, after_python)

        np.random.random()
        after_numpy = self.checkpoint()
        self.assertNotEqual(after_python, after_numpy)


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


if __name__ == "__main__":
    unittest.main()

import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from agent_play import iter_playthrough_observations, run_agent_playthrough
from env import MiniMetroEnv, legacy_auto_assignment_step
from recursive_checkpoint import canonical_checkpoint
from recursive_playtest import run_scenario

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"
OUTCOMES_PATH = FIXTURE_ROOT / "gm06c-pre-carriage-outcomes.json"
EXPECTED_FIXTURE_SHA256 = {
    "checkpoint-v1.json": "a2ca592cd34befcdf3aced1793a500ba348ee6f7816feb7d80f4146790d2c7f0",
    "checkpoint-v2.json": "1a18165f5aef625359ba72f5bc438f87ca2ac5713b697c3528b62603d0ba1350",
    "checkpoint-v3.json": "9ca2f5bce174a8c59c608cb08bc3e5903151ab0ad04df6553c21f166bed63c02",
    "recursive-playtest-v1.json": "e6ce51a06423675d4b933a7fc34bfdb235f46b0c941124786c5ae49c52f1eab4",
    "recursive-playtest-v2.json": "e9f78980ce5d3dcf2ca243b4d8b142a803fba7a8518b1a62b089f6151a4d2228",
    "recursive-playtest-v3.json": "c1eb0f8541a1614398abef6a8e2f9dc333ba95717d78f64eecc281d3177cb9ed",
    "recursive-playtest-v4.json": "807429bf99283a79341c1e78d4984880ec53deaccab1d5bc36ec2b4cf9610cee",
    "gm06b-legacy-outcomes.json": "5b234533ede170d9b4419a42e0e2d8f1e4dfa5005a4932c09ddeb8df8b22cbfe",
    "gm06c-pre-carriage-outcomes.json": "d070943f3de09df8cb18ef6e96caea875dd72541f5b5598c669e35563459e67a",
}


def canonical_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def digest(value):
    payload = canonical_bytes(value)
    return {
        "canonical_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def checkpoint_fixture(version):
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
    return canonical_bytes(checkpoint) + b"\n"


def projected_v4_record(record, expected):
    return {
        "seed": record.seed,
        "dt_ms": record.dt_ms,
        "actions": record.actions,
        "steps": [dataclasses.asdict(step) for step in record.steps],
        "final_score": record.final_score,
        "max_steps": record.max_steps,
        "schema": expected["schema"],
        "reward_contract": record.reward_contract,
        "final_deliveries": record.final_deliveries,
        "final_line_credits": record.final_line_credits,
        "overdue_passenger_threshold": record.overdue_passenger_threshold,
        "fleet_action_contract": expected["fleet_action_contract"],
    }


class TestGM06cHistoricalCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outcomes = json.loads(OUTCOMES_PATH.read_text(encoding="utf-8"))

    def test_frozen_fixture_bytes_and_checkpoint_v3_generation_are_exact(self):
        for name, expected_hash in EXPECTED_FIXTURE_SHA256.items():
            with self.subTest(name=name):
                payload = (FIXTURE_ROOT / name).read_bytes()
                self.assertNotIn(b"\r", payload)
                self.assertTrue(payload.endswith(b"\n"))
                self.assertEqual(hashlib.sha256(payload).hexdigest(), expected_hash)

        self.assertEqual(len(checkpoint_fixture(3)), 16_262)
        for version in (1, 2, 3):
            with self.subTest(generated_checkpoint=version):
                self.assertEqual(
                    checkpoint_fixture(version),
                    (FIXTURE_ROOT / f"checkpoint-v{version}.json").read_bytes(),
                )

    def test_recursive_v4_full_transcript_and_checkpoint_vector_are_exact(self):
        expected = self.outcomes["recursiveV4"]
        scenario = json.loads((FIXTURE_ROOT / "recursive-playtest-v4.json").read_text())
        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            _, transcript, findings, result = run_scenario(
                scenario,
                run_id=expected["run_id"],
                source_path=expected["source_path"],
            )
        checkpoints = [row["checkpoint"] for row in transcript]
        evidence = [
            {key: value for key, value in row.items() if key != "checkpoint"}
            for row in transcript
        ]
        outcome = {"transcript": transcript, "findings": findings, "result": result}

        self.assertEqual(digest(transcript), expected["transcript"])
        self.assertEqual(evidence, expected["transcript_evidence"])
        self.assertEqual(digest(checkpoints), expected["checkpoint_vector"])
        self.assertEqual(
            [hashlib.sha256(canonical_bytes(item)).hexdigest() for item in checkpoints],
            expected["checkpoint_sha256"],
        )
        self.assertEqual(findings, expected["findings"])
        self.assertEqual(result, expected["result"])
        self.assertEqual(digest(outcome), expected["outcome"])

    def test_recursive_v4_outcome_is_exact_across_two_fresh_hash_seed_zero_runs(self):
        expected = self.outcomes["recursiveV4"]
        runner = REPO_ROOT / "src" / "recursive_playtest.py"
        environment = {**os.environ, "PYTHONHASHSEED": "0"}
        outcomes = []
        with tempfile.TemporaryDirectory() as directory:
            for index in range(2):
                out_dir = Path(directory) / f"run-{index}"
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(runner),
                        "--scenario",
                        expected["source_path"],
                        "--out",
                        str(out_dir),
                        "--run-id",
                        expected["run_id"],
                    ],
                    cwd=REPO_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    completed.returncode, 0, completed.stderr or completed.stdout
                )
                transcript = [
                    json.loads(line)
                    for line in (out_dir / "transcript.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                    if line
                ]
                findings = json.loads(
                    (out_dir / "findings.authored.json").read_text(encoding="utf-8")
                )
                result = json.loads(
                    (out_dir / "run-result.json").read_text(encoding="utf-8")
                )
                outcome = {
                    "transcript": transcript,
                    "findings": findings,
                    "result": result,
                }
                self.assertEqual(digest(transcript), expected["transcript"])
                self.assertEqual(
                    digest([row["checkpoint"] for row in transcript]),
                    expected["checkpoint_vector"],
                )
                self.assertEqual(findings, expected["findings"])
                self.assertEqual(result, expected["result"])
                self.assertEqual(digest(outcome), expected["outcome"])
                outcomes.append(outcome)

        self.assertEqual(outcomes[0], outcomes[1])

    def test_agent_v4_actions_uuid_free_checkpoints_and_result_are_exact(self):
        expected = self.outcomes["agentV4"]
        score, current_record = run_agent_playthrough(
            seed=expected["seed"],
            max_steps=expected["max_steps"],
            dt_ms=expected["dt_ms"],
        )
        self.assertEqual(current_record.actions, expected["actions"])
        self.assertEqual(digest(current_record.actions), expected["actions_digest"])
        record_projection = projected_v4_record(current_record, expected)
        self.assertEqual(digest(record_projection), expected["record"])

        replay_record = SimpleNamespace(
            seed=expected["seed"],
            dt_ms=expected["dt_ms"],
            schema=expected["schema"],
            reward_contract=expected["reward_contract"],
            overdue_passenger_threshold=expected["overdue_passenger_threshold"],
            fleet_action_contract=expected["fleet_action_contract"],
            carriage_action_contract=None,
            actions=expected["actions"],
        )
        env = MiniMetroEnv(reward_mode=expected["reward_contract"])
        checkpoints = []
        for observation in iter_playthrough_observations(replay_record, env=env):
            checkpoints.append(canonical_checkpoint(env, observation, schema_version=3))

        encoded = canonical_bytes(checkpoints)
        for forbidden in (b"Metro-", b"Path-", b"Station-", b"Passenger-"):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(len(checkpoints), expected["checkpoint_count"])
        self.assertEqual(digest(checkpoints), expected["checkpoint_vector"])
        self.assertEqual(
            [hashlib.sha256(canonical_bytes(item)).hexdigest() for item in checkpoints],
            expected["checkpoint_sha256"],
        )
        result = {
            "returned_score": score,
            "observation_count": len(checkpoints),
            "final_deliveries": env.mediator.deliveries,
            "final_line_credits": env.mediator.line_credits,
        }
        self.assertEqual(result, expected["result"])
        self.assertEqual(digest(result), expected["result_digest"])
        outcome = {
            "actions": expected["actions"],
            "checkpoints": checkpoints,
            "record": record_projection,
            "result": result,
        }
        self.assertEqual(digest(outcome), expected["outcome"])


if __name__ == "__main__":
    unittest.main()

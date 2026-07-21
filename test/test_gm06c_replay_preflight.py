import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import recursive_contract
import recursive_playtest
from agent_play import iter_playthrough_observations, run_agent_playthrough
from env import MiniMetroEnv

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"
FLEET_CONTRACT = "explicit_locomotive_assignment_v1"
CARRIAGE_CONTRACT = "explicit_carriage_attachment_v1"
AGENT_V5 = "mini-metro-agent-play-v5"


class ResetCountingEnv(MiniMetroEnv):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset_count = 0

    def reset(self, seed=None):
        self.reset_count += 1
        return super().reset(seed=seed)


class SequenceAgent:
    def __init__(self, actions):
        self.actions = actions
        self.index = 0

    def reset(self, observation):
        self.index = 0

    def act(self, observation):
        action = self.actions[self.index]
        self.index += 1
        return action


def legacy_inputs(version):
    scenario = json.loads(
        (FIXTURE_ROOT / f"recursive-playtest-v{version}.json").read_text(
            encoding="utf-8"
        )
    )
    inputs = {
        "schemaVersion": version,
        "runId": f"legacy-v{version}",
        "sourcePath": f"scripts/fixtures/recursive-playtest-v{version}.json",
        "seed": scenario["seed"],
        "defaultDtMs": scenario["defaultDtMs"],
        "pythonExecutable": sys.executable,
        "pythonHashSeed": "0",
        "operations": deepcopy(scenario["operations"]),
    }
    for field in (
        "environmentRewardContract",
        "overduePassengerThreshold",
        "fleetActionContract",
    ):
        if field in scenario:
            inputs[field] = scenario[field]
    return inputs


def v5_inputs():
    inputs = legacy_inputs(4)
    inputs["schemaVersion"] = 5
    inputs["runId"] = "gm06c-recorded-v5"
    inputs["sourcePath"] = "recorded-v5.json"
    inputs["carriageActionContract"] = CARRIAGE_CONTRACT
    inputs["defaultDtMs"] = 0
    inputs["operations"] = [
        {
            "name": "create",
            "action": {"type": "create_path", "stations": [0, 1], "loop": False},
            "expectedActionOk": True,
        },
        {
            "name": "assign",
            "action": {"type": "assign_locomotive", "path_index": 0},
            "expectedActionOk": True,
        },
        {
            "name": "attach",
            "action": {"type": "attach_carriage", "path_index": 0},
            "expectedActionOk": True,
        },
        {
            "name": "detach",
            "action": {"type": "detach_carriage", "path_index": 0},
            "expectedActionOk": True,
        },
    ]
    return inputs


def assert_drive_preflight_rejects(case, document):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        input_path = root / "inputs.json"
        out_dir = root / "out"
        input_path.write_text(json.dumps(document), encoding="utf-8")
        with patch.object(
            recursive_playtest,
            "run_scenario",
            return_value=({}, [], [], {}),
        ) as runner:
            with case.assertRaises(ValueError):
                recursive_playtest.drive_from_file(
                    input_path,
                    out_dir,
                    "must-not-run",
                    recorded_inputs=True,
                )
        runner.assert_not_called()
        case.assertFalse(out_dir.exists())


class TestGM06cRecordedInputPreflight(unittest.TestCase):
    def test_v1_through_v4_inputs_reject_both_carriage_actions_before_drive(self):
        for version in (1, 2, 3, 4):
            for action_type in ("attach_carriage", "detach_carriage"):
                candidate = legacy_inputs(version)
                candidate["operations"] = [
                    {
                        "name": f"incompatible-{action_type}",
                        "action": {"type": action_type, "path_index": 0},
                        "expectedActionOk": False,
                    }
                ]
                with (
                    self.subTest(version=version, action=action_type),
                    self.assertRaises(ValueError),
                ):
                    recursive_contract.validate_inputs(candidate)
                assert_drive_preflight_rejects(self, candidate)

    def test_v1_through_v4_inputs_reject_forward_carriage_contract_before_drive(self):
        for version in (1, 2, 3, 4):
            candidate = legacy_inputs(version)
            candidate["carriageActionContract"] = CARRIAGE_CONTRACT
            with self.subTest(version=version), self.assertRaises(ValueError):
                recursive_contract.validate_inputs(candidate)
            assert_drive_preflight_rejects(self, candidate)

    def test_v5_inputs_require_exact_contracts_before_recorded_drive(self):
        valid = v5_inputs()
        for field, invalid_values in (
            (
                "fleetActionContract",
                (None, "", "explicit_locomotive_assignment_v2", True),
            ),
            (
                "carriageActionContract",
                (None, "", "explicit_carriage_attachment_v2", True),
            ),
        ):
            missing = {key: value for key, value in valid.items() if key != field}
            with self.subTest(field=field, invalid="missing"):
                with self.assertRaises(ValueError):
                    recursive_contract.validate_inputs(missing)
                assert_drive_preflight_rejects(self, missing)
            for invalid in invalid_values:
                candidate = {**valid, field: invalid}
                with self.subTest(field=field, invalid=invalid):
                    with self.assertRaises(ValueError):
                        recursive_contract.validate_inputs(candidate)
                    assert_drive_preflight_rejects(self, candidate)

    def test_v5_inputs_reject_every_malformed_carriage_action_before_drive(self):
        invalid_selectors = (
            {"path_id": "Path-process-local"},
            {"path_index": True},
            {"path_index": -1},
            {"path_index": 0.0},
            {"path_index": "0"},
            {"path_index": None},
            {"path_index": 0, "extra": 1},
            {},
        )
        for action_type in ("attach_carriage", "detach_carriage"):
            for selector in invalid_selectors:
                candidate = v5_inputs()
                candidate["operations"][2]["action"] = {
                    "type": action_type,
                    **selector,
                }
                with self.subTest(action=action_type, selector=selector):
                    with self.assertRaises(ValueError):
                        recursive_contract.validate_inputs(candidate)
                    assert_drive_preflight_rejects(self, candidate)

    def test_v5_exact_attach_detach_inputs_validate_and_redrive(self):
        document = v5_inputs()
        self.assertEqual(recursive_contract.validate_inputs(document), document)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "inputs.json"
            out_dir = root / "out"
            input_path.write_text(json.dumps(document), encoding="utf-8")
            with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
                recursive_playtest.drive_from_file(
                    input_path,
                    out_dir,
                    "gm06c-recorded-v5-redrive",
                    recorded_inputs=True,
                )
            rows = [
                json.loads(line)
                for line in (out_dir / "transcript.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line
            ]

        self.assertEqual(
            [row["action"] for row in rows],
            [operation["action"] for operation in document["operations"]],
        )
        self.assertEqual([row["actionOk"] for row in rows], [True] * 4)
        self.assertEqual(len(rows[2]["checkpoint"]["carriages"]), 1)
        self.assertEqual(rows[3]["checkpoint"]["carriages"], [])


class TestGM06cAgentRecordPreflight(unittest.TestCase):
    def assert_rejected_before_reset(self, record, *, reward="deliveries"):
        env = ResetCountingEnv(reward_mode=reward)
        with self.assertRaises(ValueError):
            list(iter_playthrough_observations(record, env=env))
        self.assertEqual(env.reset_count, 0)

    def test_v1_through_v4_reject_contract_and_both_actions_before_reset(self):
        legacy_cases = (
            ("mini-metro-agent-play-v1", "line_credits_delta", None, None),
            ("mini-metro-agent-play-v2", "deliveries", None, None),
            ("mini-metro-agent-play-v3", "deliveries", 2, None),
            ("mini-metro-agent-play-v4", "deliveries", 2, FLEET_CONTRACT),
        )
        for schema, reward, threshold, fleet_contract in legacy_cases:
            declared = SimpleNamespace(
                seed=839,
                dt_ms=0,
                schema=schema,
                reward_contract=reward,
                overdue_passenger_threshold=threshold,
                fleet_action_contract=fleet_contract,
                carriage_action_contract=CARRIAGE_CONTRACT,
                actions=[],
            )
            with self.subTest(schema=schema, case="contract"):
                self.assert_rejected_before_reset(declared, reward=reward)

            for action_type in ("attach_carriage", "detach_carriage"):
                record = SimpleNamespace(
                    seed=839,
                    dt_ms=0,
                    schema=schema,
                    reward_contract=reward,
                    overdue_passenger_threshold=threshold,
                    fleet_action_contract=fleet_contract,
                    carriage_action_contract=None,
                    actions=[{"type": action_type, "path_index": 0}],
                )
                with self.subTest(schema=schema, action=action_type):
                    self.assert_rejected_before_reset(record, reward=reward)

    def test_v5_requires_present_exact_fleet_and_carriage_contracts(self):
        fields = {
            "seed": 841,
            "dt_ms": 0,
            "schema": AGENT_V5,
            "reward_contract": "deliveries",
            "overdue_passenger_threshold": 2,
            "fleet_action_contract": FLEET_CONTRACT,
            "carriage_action_contract": CARRIAGE_CONTRACT,
            "actions": [],
        }
        for field, invalid_values in (
            (
                "fleet_action_contract",
                (None, "explicit_locomotive_assignment_v2", True),
            ),
            (
                "carriage_action_contract",
                (None, "explicit_carriage_attachment_v2", True),
            ),
        ):
            missing = {key: value for key, value in fields.items() if key != field}
            with self.subTest(field=field, value="missing"):
                self.assert_rejected_before_reset(SimpleNamespace(**missing))
            for value in invalid_values:
                candidate = {**fields, field: value}
                with self.subTest(field=field, value=value):
                    self.assert_rejected_before_reset(SimpleNamespace(**candidate))

    def test_v5_exact_carriage_actions_receive_full_record_preflight(self):
        invalid_actions = (
            {"type": "attach_carriage", "path_id": "Path-local"},
            {"type": "attach_carriage", "path_index": True},
            {"type": "attach_carriage", "path_index": -1},
            {"type": "attach_carriage", "path_index": "0"},
            {"type": "attach_carriage", "path_index": 0, "extra": 1},
            {"type": "attach_carriage"},
            {"type": "detach_carriage", "path_id": "Path-local"},
            {"type": "detach_carriage", "path_index": True},
            {"type": "detach_carriage", "path_index": -1},
            {"type": "detach_carriage", "path_index": "0"},
            {"type": "detach_carriage", "path_index": 0, "extra": 1},
            {"type": "detach_carriage"},
            {"type": True, "path_index": 0},
        )
        valid_prefix = {"type": "create_path", "stations": [0, 1], "loop": False}
        for action in invalid_actions:
            record = SimpleNamespace(
                seed=843,
                dt_ms=0,
                schema=AGENT_V5,
                reward_contract="deliveries",
                overdue_passenger_threshold=2,
                fleet_action_contract=FLEET_CONTRACT,
                carriage_action_contract=CARRIAGE_CONTRACT,
                actions=[valid_prefix, action],
            )
            with self.subTest(action=action):
                self.assert_rejected_before_reset(record)

    def test_v5_attach_then_detach_record_replays_exactly(self):
        actions = [
            {"type": "create_path", "stations": [0, 1], "loop": False},
            {"type": "assign_locomotive", "path_index": 0},
            {"type": "attach_carriage", "path_index": 0},
            {"type": "detach_carriage", "path_index": 0},
        ]
        _, record = run_agent_playthrough(
            SequenceAgent(actions), seed=847, max_steps=len(actions), dt_ms=0
        )
        self.assertEqual(record.schema, AGENT_V5)
        self.assertEqual(record.fleet_action_contract, FLEET_CONTRACT)
        self.assertEqual(record.carriage_action_contract, CARRIAGE_CONTRACT)
        self.assertEqual(record.actions, actions)

        env = ResetCountingEnv(reward_mode="deliveries")
        observations = list(iter_playthrough_observations(record, env=env))
        self.assertEqual(env.reset_count, 1)
        self.assertEqual(len(observations[3]["structured"]["carriages"]), 1)
        self.assertEqual(
            observations[3]["structured"]["fleet"]["carriages_available"], 1
        )
        self.assertEqual(observations[-1]["structured"]["carriages"], [])
        self.assertEqual(
            observations[-1]["structured"]["fleet"]["carriages_available"], 2
        )


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import agent_play
import recursive_contract
import recursive_playtest
from agent_play import (
    PlaythroughRecord,
    iter_playthrough_observations,
    run_agent_playthrough,
)
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"
FLEET_CONTRACT = "explicit_locomotive_assignment_v1"
AGENT_V4 = "mini-metro-agent-play-v4"
AGENT_V5 = "mini-metro-agent-play-v5"


def load_fixture(name):
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def checkpoint_digest(checkpoint):
    payload = json.dumps(
        checkpoint,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def legacy_scenario(case, oracle):
    document = {
        "schemaVersion": case["recursiveSchemaVersion"],
        "seed": oracle["seed"],
        "defaultDtMs": 0,
        "operations": [
            {
                "name": "create",
                "action": oracle["action"],
                "dtMs": oracle["dtMs"],
                "expectedActionOk": True,
            }
        ],
    }
    if case["recursiveSchemaVersion"] >= 2:
        document["environmentRewardContract"] = "deliveries"
    if case["recursiveSchemaVersion"] == 3:
        document["overduePassengerThreshold"] = case["overduePassengerThreshold"]
    return document


class ResetCountingEnv(MiniMetroEnv):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset_count = 0

    def reset(self, seed=None):
        self.reset_count += 1
        return super().reset(seed=seed)


class TestGM06bRecursiveReplayContract(unittest.TestCase):
    def test_recursive_schema_aliases_advance_to_v5_without_renaming_history(self):
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V1", None), 1)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V2", None), 2)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V3", None), 3)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V4", None), 4)
        self.assertEqual(getattr(recursive_contract, "SCHEMA_VERSION_V5", None), 5)
        self.assertEqual(recursive_contract.LEGACY_SCHEMA_VERSION, 1)
        self.assertEqual(recursive_contract.SCHEMA_VERSION, 5)
        self.assertEqual(recursive_playtest.LEGACY_SCHEMA_VERSION, 1)
        self.assertEqual(recursive_playtest.SCHEMA_VERSION, 5)

    def test_default_v4_fixture_is_strict_and_maps_to_checkpoint_v3(self):
        document = load_fixture("recursive-playtest-v4.json")
        self.assertEqual(recursive_playtest.validate_scenario(document), document)

        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            inputs, rows, findings, result = recursive_playtest.run_scenario(
                document,
                run_id="gm06b-v4",
                source_path="scripts/fixtures/recursive-playtest.json",
            )

        self.assertEqual(inputs["schemaVersion"], 4)
        self.assertEqual(inputs["fleetActionContract"], FLEET_CONTRACT)
        self.assertTrue(all(row["checkpoint"]["schemaVersion"] == 3 for row in rows))
        self.assertEqual(
            rows[0]["checkpoint"]["structured"]["fleet"]["locomotives_assigned"],
            0,
        )
        self.assertEqual(rows[1]["action"]["type"], "assign_locomotive")
        self.assertTrue(rows[1]["actionOk"])
        self.assertEqual(
            rows[1]["checkpoint"]["structured"]["fleet"]["locomotives_assigned"],
            1,
        )
        self.assertEqual(findings, [])
        self.assertEqual(result["schemaVersion"], 4)

    def test_v4_requires_all_contract_fields_and_index_only_fleet_actions(self):
        valid = load_fixture("recursive-playtest.json")
        self.assertEqual(recursive_playtest.validate_scenario(valid), valid)

        for missing in (
            "environmentRewardContract",
            "overduePassengerThreshold",
            "fleetActionContract",
        ):
            candidate = {key: value for key, value in valid.items() if key != missing}
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                recursive_playtest.validate_scenario(candidate)
        for contract in ("", "explicit_locomotive_assignment_v2", None, True):
            candidate = {**valid, "fleetActionContract": contract}
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                recursive_playtest.validate_scenario(candidate)

        assignment_index = next(
            index
            for index, operation in enumerate(valid["operations"])
            if operation["action"]["type"] == "assign_locomotive"
        )
        invalid_actions = (
            {"type": "assign_locomotive", "path_id": "Path-process-local"},
            {"type": "assign_locomotive", "path_index": True},
            {
                "type": "assign_locomotive",
                "path_index": 0,
                "path_id": "Path-process-local",
            },
            {"type": "unassign_locomotive", "path_id": "Path-process-local"},
        )
        for action in invalid_actions:
            candidate = json.loads(json.dumps(valid))
            candidate["operations"][assignment_index]["action"] = action
            with self.subTest(action=action), self.assertRaises(ValueError):
                recursive_playtest.validate_scenario(candidate)

    def test_v1_v2_v3_reject_new_actions_before_environment_construction(self):
        for version in (1, 2, 3):
            document = load_fixture(f"recursive-playtest-v{version}.json")
            document["operations"] = [
                {
                    "name": "incompatible-fleet-action",
                    "action": {"type": "assign_locomotive", "path_index": 0},
                    "expectedActionOk": False,
                }
            ]
            constructed = []

            def factory(*, reward_mode):
                constructed.append(reward_mode)
                return MiniMetroEnv(reward_mode=reward_mode)

            with (
                self.subTest(version=version),
                patch.dict(os.environ, {"PYTHONHASHSEED": "0"}),
                self.assertRaises(ValueError),
            ):
                recursive_playtest.run_scenario(
                    document,
                    run_id=f"legacy-v{version}",
                    source_path=f"legacy-v{version}.json",
                    env_factory=factory,
                )
            self.assertEqual(constructed, [])

    def test_v1_v2_v3_reject_the_v4_contract_field(self):
        for version in (1, 2, 3):
            document = load_fixture(f"recursive-playtest-v{version}.json")
            document["fleetActionContract"] = FLEET_CONTRACT
            with self.subTest(version=version), self.assertRaises(ValueError):
                recursive_playtest.validate_scenario(document)

    def test_frozen_nonzero_dt_legacy_recursive_and_agent_outcomes_remain_exact(self):
        oracle = load_fixture("gm06b-legacy-outcomes.json")
        expected = oracle["expected"]
        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            for case in oracle["cases"]:
                version = case["recursiveSchemaVersion"]
                with self.subTest(lane="recursive", version=version):
                    _, rows, findings, _ = recursive_playtest.run_scenario(
                        legacy_scenario(case, oracle),
                        run_id=f"oracle-recursive-v{version}",
                        source_path=f"oracle-v{version}.json",
                    )
                    self.assertEqual(len(rows), expected["transcriptRows"])
                    self.assertEqual(findings, [])
                    self.assertEqual(rows[0]["actionOk"], expected["actionOk"])
                    self.assert_legacy_checkpoint(
                        rows[0]["checkpoint"],
                        case["recursiveCheckpointSha256"],
                        case,
                        expected,
                    )

                with self.subTest(lane="agent", version=version):
                    record = PlaythroughRecord(
                        seed=oracle["seed"],
                        dt_ms=oracle["dtMs"],
                        actions=[oracle["action"]],
                        schema=case["agentRecordSchema"],
                        reward_contract=case["rewardContract"],
                        overdue_passenger_threshold=case["overduePassengerThreshold"]
                        if version == 3
                        else None,
                    )
                    env = MiniMetroEnv(reward_mode=case["rewardContract"])
                    observations = list(iter_playthrough_observations(record, env=env))
                    checkpoint = canonical_checkpoint(
                        env,
                        observations[-1],
                        schema_version=case["checkpointSchemaVersion"],
                    )
                    self.assert_legacy_checkpoint(
                        checkpoint,
                        case["agentCheckpointSha256"],
                        case,
                        expected,
                    )

    def assert_legacy_checkpoint(self, checkpoint, digest, case, expected):
        self.assertEqual(checkpoint["schemaVersion"], case["checkpointSchemaVersion"])
        self.assertEqual(checkpoint_digest(checkpoint), digest)
        self.assertEqual(checkpoint["structured"]["time_ms"], expected["timeMs"])
        self.assertEqual(checkpoint["structured"]["steps"], expected["steps"])
        self.assertEqual(len(checkpoint["metroMotion"]), expected["metroCount"])
        motion = checkpoint["metroMotion"][0]
        self.assertEqual(motion["position"], expected["metroPosition"])
        self.assertEqual(
            motion["current_station_index"], expected["currentStationIndex"]
        )
        self.assertEqual(
            motion["current_segment_index"], expected["currentSegmentIndex"]
        )
        self.assertEqual(
            motion["stop_time_remaining_ms"], expected["stopTimeRemainingMs"]
        )

    def test_legacy_assignment_failure_aborts_before_tick_without_a_row(self):
        created = []

        class RejectingEnv(MiniMetroEnv):
            def reset(self, seed=None):
                observation = super().reset(seed=seed)
                self.assignment_calls = []

                def reject(path):
                    self.assignment_calls.append(path)
                    return False

                self.mediator.assign_locomotive = reject
                return observation

        def factory(*, reward_mode):
            env = RejectingEnv(reward_mode=reward_mode)
            created.append(env)
            return env

        document = legacy_scenario(
            load_fixture("gm06b-legacy-outcomes.json")["cases"][2],
            load_fixture("gm06b-legacy-outcomes.json"),
        )
        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            try:
                recursive_playtest.run_scenario(
                    document,
                    run_id="legacy-reject",
                    source_path="legacy-reject.json",
                    env_factory=factory,
                )
            except (RuntimeError, ValueError):
                pass
            else:
                self.fail("legacy replay accepted a failed compatibility assignment")

        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0].assignment_calls), 1)
        self.assertEqual(created[0].mediator.time_ms, 0)
        self.assertEqual(created[0].mediator.steps, 0)


class TestGM06bAgentReplayContract(unittest.TestCase):
    def test_agent_schema_aliases_advance_to_v5_and_simple_agent_assigns_by_index(self):
        self.assertEqual(
            getattr(agent_play, "PLAYTHROUGH_RECORD_SCHEMA_V4", None), AGENT_V4
        )
        self.assertEqual(
            getattr(agent_play, "PLAYTHROUGH_RECORD_SCHEMA_V5", None), AGENT_V5
        )
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA, AGENT_V5)

        _, record = run_agent_playthrough(seed=653, max_steps=2, dt_ms=0)

        self.assertEqual(record.schema, AGENT_V5)
        self.assertEqual(record.fleet_action_contract, FLEET_CONTRACT)
        self.assertEqual(
            record.carriage_action_contract,
            agent_play.CARRIAGE_ACTION_CONTRACT,
        )
        self.assertEqual(
            record.actions,
            [
                {"type": "create_path", "stations": [0, 1], "loop": False},
                {"type": "assign_locomotive", "path_index": 0},
            ],
        )
        encoded = json.dumps(record.actions, sort_keys=True)
        self.assertNotIn("path_id", encoded)
        self.assertNotIn("Path-", encoded)

    def test_agent_v1_v2_v3_preflight_rejects_fleet_actions_before_reset(self):
        cases = (
            ("mini-metro-agent-play-v1", "line_credits_delta", None),
            ("mini-metro-agent-play-v2", "deliveries", None),
            ("mini-metro-agent-play-v3", "deliveries", 2),
        )
        for schema, reward, threshold in cases:
            record = SimpleNamespace(
                seed=659,
                dt_ms=17,
                schema=schema,
                reward_contract=reward,
                overdue_passenger_threshold=threshold,
                actions=[{"type": "assign_locomotive", "path_index": 0}],
            )
            env = ResetCountingEnv(reward_mode=reward)
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                list(iter_playthrough_observations(record, env=env))
            self.assertEqual(env.reset_count, 0)
            self.assertEqual(env.mediator.time_ms, 0)

    def test_agent_v1_v2_v3_reject_nonempty_v4_contract_before_reset(self):
        for schema, reward, threshold in (
            ("mini-metro-agent-play-v1", "line_credits_delta", None),
            ("mini-metro-agent-play-v2", "deliveries", None),
            ("mini-metro-agent-play-v3", "deliveries", 2),
        ):
            record = SimpleNamespace(
                seed=661,
                dt_ms=0,
                schema=schema,
                reward_contract=reward,
                overdue_passenger_threshold=threshold,
                fleet_action_contract=FLEET_CONTRACT,
                actions=[],
            )
            env = ResetCountingEnv(reward_mode=reward)
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                list(iter_playthrough_observations(record, env=env))
            self.assertEqual(env.reset_count, 0)

    def test_agent_v4_rejects_path_id_after_reset_but_before_step(self):
        record = SimpleNamespace(
            seed=673,
            dt_ms=17,
            schema=AGENT_V4,
            reward_contract="deliveries",
            overdue_passenger_threshold=2,
            fleet_action_contract=FLEET_CONTRACT,
            actions=[{"type": "assign_locomotive", "path_id": "Path-process-local"}],
        )
        env = ResetCountingEnv(reward_mode="deliveries")
        with self.assertRaises(ValueError):
            list(iter_playthrough_observations(record, env=env))
        self.assertEqual(env.reset_count, 1)
        self.assertEqual(env.mediator.time_ms, 0)

    def test_agent_v4_index_actions_create_then_assign_without_uuid_state(self):
        record = SimpleNamespace(
            seed=677,
            dt_ms=0,
            schema=AGENT_V4,
            reward_contract="deliveries",
            overdue_passenger_threshold=2,
            fleet_action_contract=FLEET_CONTRACT,
            actions=[
                {"type": "create_path", "stations": [0, 1], "loop": False},
                {"type": "assign_locomotive", "path_index": 0},
            ],
        )
        env = ResetCountingEnv(reward_mode="deliveries")
        observations = list(iter_playthrough_observations(record, env=env))

        self.assertEqual(len(observations), 3)
        self.assertEqual(
            observations[1]["structured"]["fleet"]["locomotives_assigned"], 0
        )
        self.assertEqual(
            observations[2]["structured"]["fleet"]["locomotives_assigned"], 1
        )
        self.assertNotIn("path_id", json.dumps(record.actions, sort_keys=True))

    def test_agent_legacy_assignment_failure_aborts_before_tick(self):
        record = SimpleNamespace(
            seed=683,
            dt_ms=137,
            schema="mini-metro-agent-play-v3",
            reward_contract="deliveries",
            overdue_passenger_threshold=2,
            actions=[{"type": "create_path", "stations": [0, 1, 2], "loop": False}],
        )

        class RejectingEnv(ResetCountingEnv):
            def reset(self, seed=None):
                observation = super().reset(seed=seed)
                self.assignment_calls = []

                def reject(path):
                    self.assignment_calls.append(path)
                    return False

                self.mediator.assign_locomotive = reject
                return observation

        env = RejectingEnv(reward_mode="deliveries")
        try:
            list(iter_playthrough_observations(record, env=env))
        except (RuntimeError, ValueError):
            pass
        else:
            self.fail("agent replay accepted a failed compatibility assignment")

        self.assertEqual(len(env.assignment_calls), 1)
        self.assertEqual(env.mediator.time_ms, 0)
        self.assertEqual(env.mediator.steps, 0)


if __name__ == "__main__":
    unittest.main()

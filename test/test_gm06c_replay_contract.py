import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import agent_play
import recursive_contract
import recursive_playtest
from agent_play import iter_playthrough_observations, run_agent_playthrough
from env import MiniMetroEnv

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"
DEFAULT_SCENARIO = FIXTURE_ROOT / "recursive-playtest.json"
FLEET_CONTRACT = "explicit_locomotive_assignment_v1"
CARRIAGE_CONTRACT = "explicit_carriage_attachment_v1"
AGENT_V5 = "mini-metro-agent-play-v5"


def load_fixture(name):
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def v5_scenario():
    document = load_fixture("recursive-playtest-v4.json")
    document["schemaVersion"] = 5
    document["carriageActionContract"] = CARRIAGE_CONTRACT
    assignment_index = next(
        index
        for index, operation in enumerate(document["operations"])
        if operation["action"]["type"] == "assign_locomotive"
    )
    document["operations"].insert(
        assignment_index + 1,
        {
            "name": "attach-initial-carriage",
            "action": {"type": "attach_carriage", "path_index": 0},
            "expectedActionOk": True,
        },
    )
    return document


def assert_bijection(case, checkpoint):
    carriages = checkpoint["carriages"]
    record_keys = {"capacity", "metro_motion_index", "attachment_index"}
    cursor = 0
    for metro_index, metro in enumerate(checkpoint["metroMotion"]):
        expected = list(range(cursor, cursor + len(metro["carriage_indices"])))
        case.assertEqual(metro["carriage_indices"], expected)
        for attachment_index, carriage_index in enumerate(expected):
            carriage = carriages[carriage_index]
            case.assertEqual(set(carriage), record_keys)
            case.assertEqual(carriage["metro_motion_index"], metro_index)
            case.assertEqual(carriage["attachment_index"], attachment_index)
        cursor += len(expected)
    case.assertEqual(cursor, len(carriages))

    global_count = len(checkpoint["structured"]["metros"])
    global_carriage_count = sum(
        len(metro["carriage_indices"])
        for metro in checkpoint["metroMotion"][:global_count]
    )
    case.assertEqual(len(checkpoint["structured"]["carriages"]), global_carriage_count)
    case.assertEqual(
        checkpoint["structured"]["carriages"],
        carriages[:global_carriage_count],
    )
    for carriage in checkpoint["structured"]["carriages"]:
        case.assertEqual(set(carriage), record_keys)
    for index, metro in enumerate(checkpoint["structured"]["metros"]):
        case.assertEqual(
            metro["carriage_indices"],
            checkpoint["metroMotion"][index]["carriage_indices"],
        )
        case.assertEqual(
            metro["capacity"], checkpoint["metroMotion"][index]["capacity"]
        )
        for carriage_index in metro["carriage_indices"]:
            case.assertGreaterEqual(carriage_index, 0)
            case.assertLess(carriage_index, global_carriage_count)
    for metro in checkpoint["metroMotion"][global_count:]:
        for carriage_index in metro["carriage_indices"]:
            case.assertGreaterEqual(carriage_index, global_carriage_count)

    def assert_uuid_free(value):
        if isinstance(value, dict):
            for key, item in value.items():
                case.assertNotEqual(key, "id")
                case.assertFalse(key.endswith("_id"), key)
                case.assertFalse(key.endswith("_ids"), key)
                assert_uuid_free(item)
        elif isinstance(value, list):
            for item in value:
                assert_uuid_free(item)
        elif isinstance(value, str):
            for prefix in (
                "Metro-",
                "Carriage-",
                "Path-",
                "Station-",
                "Passenger-",
            ):
                case.assertNotIn(prefix, value)

    assert_uuid_free(checkpoint)


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


class TestGM06cRecursiveV5Contract(unittest.TestCase):
    def test_version_aliases_and_default_v5_contract_are_exact(self):
        self.assertEqual(recursive_contract.SCHEMA_VERSION_V1, 1)
        self.assertEqual(recursive_contract.SCHEMA_VERSION_V2, 2)
        self.assertEqual(recursive_contract.SCHEMA_VERSION_V3, 3)
        self.assertEqual(recursive_contract.SCHEMA_VERSION_V4, 4)
        self.assertEqual(recursive_contract.SCHEMA_VERSION_V5, 5)
        self.assertEqual(recursive_contract.SCHEMA_VERSION, 5)
        self.assertEqual(recursive_contract.FLEET_ACTION_CONTRACT, FLEET_CONTRACT)
        self.assertEqual(recursive_contract.CARRIAGE_ACTION_CONTRACT, CARRIAGE_CONTRACT)

        document = load_fixture("recursive-playtest.json")
        self.assertEqual(recursive_playtest.validate_scenario(document), document)
        self.assertEqual(
            set(document),
            {
                "schemaVersion",
                "environmentRewardContract",
                "overduePassengerThreshold",
                "fleetActionContract",
                "carriageActionContract",
                "seed",
                "defaultDtMs",
                "operations",
            },
        )
        self.assertEqual(document["schemaVersion"], 5)
        self.assertEqual(document["fleetActionContract"], FLEET_CONTRACT)
        self.assertEqual(document["carriageActionContract"], CARRIAGE_CONTRACT)
        attachment = next(
            operation
            for operation in document["operations"]
            if operation["action"].get("type") == "attach_carriage"
        )
        self.assertEqual(
            attachment["action"], {"type": "attach_carriage", "path_index": 0}
        )

    def test_default_v5_maps_to_nonempty_uuid_free_checkpoint_v4(self):
        document = load_fixture("recursive-playtest.json")
        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            inputs, rows, findings, result = recursive_playtest.run_scenario(
                document,
                run_id="gm06c-v5",
                source_path="scripts/fixtures/recursive-playtest.json",
            )
        self.assertEqual(inputs["schemaVersion"], 5)
        self.assertEqual(inputs["fleetActionContract"], FLEET_CONTRACT)
        self.assertEqual(inputs["carriageActionContract"], CARRIAGE_CONTRACT)
        self.assertTrue(all(row["checkpoint"]["schemaVersion"] == 4 for row in rows))
        attachment = next(
            row for row in rows if row["action"].get("type") == "attach_carriage"
        )
        self.assertTrue(attachment["actionOk"])
        checkpoint = attachment["checkpoint"]
        self.assertGreater(len(checkpoint["carriages"]), 0)
        self.assertGreater(len(checkpoint["structured"]["carriages"]), 0)
        assert_bijection(self, checkpoint)
        encoded = json.dumps(checkpoint, allow_nan=False, sort_keys=True)
        self.assertNotIn("Carriage-", encoded)
        self.assertEqual(findings, [])
        self.assertEqual(result["schemaVersion"], 5)

    def test_v1_through_v4_reject_carriage_fields_and_actions_before_construction(self):
        for version in (1, 2, 3, 4):
            for action_type in ("attach_carriage", "detach_carriage"):
                document = load_fixture(f"recursive-playtest-v{version}.json")
                document["operations"] = [
                    {
                        "name": "incompatible-carriage-action",
                        "action": {"type": action_type, "path_index": 0},
                        "expectedActionOk": False,
                    }
                ]
                constructed = []

                def factory(*, reward_mode):
                    constructed.append(reward_mode)
                    return MiniMetroEnv(reward_mode=reward_mode)

                with (
                    self.subTest(
                        version=version, boundary="action", action=action_type
                    ),
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

            original = load_fixture(f"recursive-playtest-v{version}.json")
            original["carriageActionContract"] = CARRIAGE_CONTRACT
            with (
                self.subTest(version=version, boundary="field"),
                self.assertRaises(ValueError),
            ):
                recursive_playtest.validate_scenario(original)

    def test_v5_requires_both_contracts_and_exact_index_only_carriage_actions(self):
        valid = v5_scenario()
        self.assertEqual(recursive_playtest.validate_scenario(valid), valid)
        for missing in ("fleetActionContract", "carriageActionContract"):
            candidate = {key: value for key, value in valid.items() if key != missing}
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                recursive_playtest.validate_scenario(candidate)
        for field, values in (
            ("fleetActionContract", ("", "explicit_locomotive_assignment_v2", True)),
            ("carriageActionContract", ("", "explicit_carriage_attachment_v2", True)),
        ):
            for value in values:
                candidate = {**valid, field: value}
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(ValueError),
                ):
                    recursive_playtest.validate_scenario(candidate)

        attachment_index = next(
            index
            for index, operation in enumerate(valid["operations"])
            if operation["action"].get("type") == "attach_carriage"
        )
        invalid_actions = (
            {"type": "attach_carriage", "path_id": "Path-process-local"},
            {"type": "attach_carriage", "path_index": True},
            {"type": "attach_carriage", "path_index": -1},
            {"type": "attach_carriage", "path_index": 0.0},
            {"type": "attach_carriage", "path_index": "0"},
            {"type": "attach_carriage", "path_index": None},
            {"type": "attach_carriage", "path_index": 0, "extra": 1},
            {"type": "detach_carriage"},
            {"type": "detach_carriage", "path_index": 0.0},
            {"type": "detach_carriage", "path_index": "0"},
            {"type": "detach_carriage", "path_index": None},
            {
                "type": "detach_carriage",
                "path_index": 0,
                "path_id": "Path-process-local",
            },
        )
        for action in invalid_actions:
            candidate = deepcopy(valid)
            candidate["operations"][attachment_index]["action"] = action
            constructed = []

            def factory(*, reward_mode):
                constructed.append(reward_mode)
                return MiniMetroEnv(reward_mode=reward_mode)

            with (
                self.subTest(action=action),
                patch.dict(os.environ, {"PYTHONHASHSEED": "0"}),
                self.assertRaises(ValueError),
            ):
                recursive_playtest.run_scenario(
                    candidate,
                    run_id="invalid-v5",
                    source_path="invalid-v5.json",
                    env_factory=factory,
                )
            self.assertEqual(constructed, [])

    def test_reused_mutable_v5_actions_are_copied_before_environment_mutation(self):
        shared = {"type": "attach_carriage", "path_index": 0}
        scenario = {
            "schemaVersion": 5,
            "environmentRewardContract": "deliveries",
            "overduePassengerThreshold": 2,
            "fleetActionContract": FLEET_CONTRACT,
            "carriageActionContract": CARRIAGE_CONTRACT,
            "seed": 751,
            "defaultDtMs": 0,
            "operations": [
                {
                    "name": "create",
                    "action": {
                        "type": "create_path",
                        "stations": [0, 1, 2],
                        "loop": False,
                    },
                    "expectedActionOk": True,
                },
                {
                    "name": "assign",
                    "action": {"type": "assign_locomotive", "path_index": 0},
                    "expectedActionOk": True,
                },
                {"name": "attach-one", "action": shared, "expectedActionOk": True},
                {"name": "attach-two", "action": shared, "expectedActionOk": True},
            ],
        }
        self.assertIs(scenario["operations"][2]["action"], shared)
        self.assertIs(scenario["operations"][3]["action"], shared)

        class MutatingEnv(MiniMetroEnv):
            def step(self, action=None, dt_ms=None):
                result = super().step(action, dt_ms=dt_ms)
                if isinstance(action, dict) and action.get("type") == "attach_carriage":
                    action["path_index"] = 99
                    action["mutated"] = True
                return result

        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            inputs, rows, findings, _ = recursive_playtest.run_scenario(
                scenario,
                run_id="reused-v5",
                source_path="reused-v5.json",
                env_factory=MutatingEnv,
            )
        expected = {"type": "attach_carriage", "path_index": 0}
        self.assertEqual(shared, expected)
        self.assertEqual(inputs["operations"][2]["action"], expected)
        self.assertEqual(inputs["operations"][3]["action"], expected)
        self.assertIsNot(
            inputs["operations"][2]["action"], inputs["operations"][3]["action"]
        )
        self.assertEqual(rows[2]["action"], expected)
        self.assertEqual(rows[3]["action"], expected)
        self.assertEqual(len(rows[2]["checkpoint"]["carriages"]), 1)
        self.assertEqual(len(rows[3]["checkpoint"]["carriages"]), 2)
        self.assertEqual(findings, [])


class TestGM06cAgentV5Contract(unittest.TestCase):
    def test_generated_v5_record_requires_both_contracts_and_replays_attachment(self):
        actions = [
            {"type": "create_path", "stations": [0, 1], "loop": False},
            {"type": "assign_locomotive", "path_index": 0},
            {"type": "attach_carriage", "path_index": 0},
        ]
        _, record = run_agent_playthrough(
            SequenceAgent(actions), seed=761, max_steps=len(actions), dt_ms=0
        )
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA_V5, AGENT_V5)
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA, AGENT_V5)
        self.assertEqual(record.schema, AGENT_V5)
        self.assertEqual(record.fleet_action_contract, FLEET_CONTRACT)
        self.assertEqual(record.carriage_action_contract, CARRIAGE_CONTRACT)
        self.assertEqual(record.actions, actions)

        env = ResetCountingEnv(reward_mode="deliveries")
        observations = list(iter_playthrough_observations(record, env=env))
        self.assertEqual(env.reset_count, 1)
        self.assertEqual(len(observations[-1]["structured"]["carriages"]), 1)
        self.assertEqual(
            observations[-1]["structured"]["fleet"]["carriages_available"], 1
        )

    def test_all_record_contract_and_action_errors_fail_before_reset(self):
        legacy_cases = (
            ("mini-metro-agent-play-v1", "line_credits_delta", None, None),
            ("mini-metro-agent-play-v2", "deliveries", None, None),
            ("mini-metro-agent-play-v3", "deliveries", 2, None),
            ("mini-metro-agent-play-v4", "deliveries", 2, FLEET_CONTRACT),
        )
        for schema, reward, threshold, fleet_contract in legacy_cases:
            record = SimpleNamespace(
                seed=769,
                dt_ms=0,
                schema=schema,
                reward_contract=reward,
                overdue_passenger_threshold=threshold,
                fleet_action_contract=fleet_contract,
                carriage_action_contract=None,
                actions=[{"type": "attach_carriage", "path_index": 0}],
            )
            env = ResetCountingEnv(reward_mode=reward)
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                list(iter_playthrough_observations(record, env=env))
            self.assertEqual(env.reset_count, 0)

        invalid_v5 = (
            SimpleNamespace(
                seed=773,
                dt_ms=0,
                schema=AGENT_V5,
                reward_contract="deliveries",
                overdue_passenger_threshold=2,
                fleet_action_contract=FLEET_CONTRACT,
                actions=[],
            ),
            SimpleNamespace(
                seed=773,
                dt_ms=0,
                schema=AGENT_V5,
                reward_contract="deliveries",
                overdue_passenger_threshold=2,
                fleet_action_contract=FLEET_CONTRACT,
                carriage_action_contract="explicit_carriage_attachment_v2",
                actions=[],
            ),
            SimpleNamespace(
                seed=773,
                dt_ms=0,
                schema=AGENT_V5,
                reward_contract="deliveries",
                overdue_passenger_threshold=2,
                fleet_action_contract=FLEET_CONTRACT,
                carriage_action_contract=CARRIAGE_CONTRACT,
                actions=[{"type": "attach_carriage", "path_id": "Path-local"}],
            ),
        )
        for record in invalid_v5:
            env = ResetCountingEnv(reward_mode="deliveries")
            with self.subTest(record=record), self.assertRaises(ValueError):
                list(iter_playthrough_observations(record, env=env))
            self.assertEqual(env.reset_count, 0)


if __name__ == "__main__":
    unittest.main()

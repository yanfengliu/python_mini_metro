import json
import os
import sys
import unittest
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from recursive_oracles import reference_errors
from recursive_playtest import (
    DELIVERIES_REWARD_CONTRACT,
    canonical_checkpoint,
    evaluate_oracles,
)


def operation(name="noop", action=None, expected=True, **extra):
    return {
        "name": name,
        "action": {"type": "noop"} if action is None else action,
        "expectedActionOk": expected,
        **extra,
    }


class TestRecursiveOracles(unittest.TestCase):
    def test_cross_view_topology_oracle_authors_unverified_stable_finding(self):
        env = MiniMetroEnv()
        env.reset(seed=5)
        initial = canonical_checkpoint(env)
        observation, reward, done, info = env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False}
        )
        checkpoint = canonical_checkpoint(env, observation)
        checkpoint["arrays"]["path_station_indices"][0].reverse()
        op = operation(
            "create-line",
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
        )
        row = {
            "index": 0,
            "name": op["name"],
            "action": deepcopy(op["action"]),
            "requestedDtMs": None,
            "effectiveDtMs": 7,
            "actionOk": info["action_ok"],
            "reward": reward,
            "done": done,
            "checkpoint": checkpoint,
        }

        first = evaluate_oracles([row], [op], initial)
        second = evaluate_oracles(deepcopy([row]), deepcopy([op]), deepcopy(initial))

        self.assertEqual(first, second)
        finding = next(
            item
            for item in first
            if item["data"]["class"] == "observation-path-topology-mismatch"
        )
        self.assertEqual(finding["verificationStatus"], "unverified")
        self.assertEqual(finding["nextAction"], "autoFix")
        self.assertEqual(finding["promotionTarget"], "test")
        self.assertNotIn("run", json.dumps(finding).lower())

    def test_contract_oracles_cover_all_required_classes(self):
        env = MiniMetroEnv(reward_mode="line_credits_delta")
        env.reset(seed=9)
        initial = canonical_checkpoint(env, schema_version=1)
        broken = deepcopy(initial)
        broken["structured"]["score"] = 2
        broken["structured"]["time_ms"] = 10
        broken["structured"]["is_paused"] = True
        broken["structured"]["paths"] = [
            {"station_indices": [999], "is_looped": False, "color": [0, 0, 0]}
        ]
        broken["arrays"]["path_station_indices"] = [[999]]
        broken["structured"]["stations"][0]["position"][0] = {"$nonFinite": "NaN"}
        op = operation("bad", {"type": "remove_path", "path_index": 999}, True)
        row = {
            "index": 0,
            "name": "bad",
            "action": deepcopy(op["action"]),
            "requestedDtMs": None,
            "effectiveDtMs": 7,
            "actionOk": False,
            "reward": 0,
            "done": False,
            "checkpoint": broken,
        }

        classes = {
            finding["data"]["class"]
            for finding in evaluate_oracles([row], [op, operation("missing")], initial)
        }

        self.assertTrue(
            {
                "input-transcript-cardinality-mismatch",
                "expected-action-result-mismatch",
                "reward-score-mismatch",
                "rejected-action-mutation",
                "invalid-reference",
                "non-finite-coordinate",
            }.issubset(classes)
        )
        legacy_reward_finding = next(
            finding
            for finding in evaluate_oracles([row], [op, operation("missing")], initial)
            if finding["data"]["class"] == "reward-score-mismatch"
        )
        self.assertEqual(
            legacy_reward_finding["observed"],
            "reward 0 differs from score delta 2",
        )

    def test_delivery_reward_oracle_uses_explicit_checkpoint_deliveries(self):
        env = MiniMetroEnv()
        env.reset(seed=16)
        initial = canonical_checkpoint(env)
        changed = deepcopy(initial)
        changed["progression"]["deliveries"] += 1
        changed["progression"]["total_travels_handled"] += 1
        operation_row = operation("delivery")
        row = {
            "index": 0,
            "name": operation_row["name"],
            "action": deepcopy(operation_row["action"]),
            "requestedDtMs": None,
            "effectiveDtMs": 7,
            "actionOk": True,
            "reward": 0,
            "done": False,
            "checkpoint": changed,
        }

        findings = evaluate_oracles(
            [row],
            [operation_row],
            initial,
            environment_reward_contract=DELIVERIES_REWARD_CONTRACT,
        )

        self.assertIn(
            "reward-deliveries-mismatch",
            {finding["data"]["class"] for finding in findings},
        )

    def test_reward_oracle_defaults_to_checkpoint_contract_and_rejects_drift(self):
        env = MiniMetroEnv(reward_mode="line_credits_delta")
        env.reset(seed=16)
        initial = canonical_checkpoint(env)
        changed = deepcopy(initial)
        changed["structured"]["score"] += 1
        changed["progression"]["score"] += 1
        changed["progression"]["line_credits"] += 1
        operation_row = operation("credit")
        row = {
            "index": 0,
            "name": operation_row["name"],
            "action": deepcopy(operation_row["action"]),
            "requestedDtMs": None,
            "effectiveDtMs": 7,
            "actionOk": True,
            "reward": 1,
            "done": False,
            "checkpoint": changed,
        }

        findings = evaluate_oracles([row], [operation_row], initial)

        self.assertNotIn(
            "reward-deliveries-mismatch",
            {finding["data"]["class"] for finding in findings},
        )
        with self.assertRaisesRegex(ValueError, "disagrees"):
            evaluate_oracles(
                [row],
                [operation_row],
                initial,
                environment_reward_contract=DELIVERIES_REWARD_CONTRACT,
            )

        changed_mode = deepcopy(row)
        changed_mode["checkpoint"]["environment"]["reward_mode"] = "deliveries"
        drift_findings = evaluate_oracles([changed_mode], [operation_row], initial)
        self.assertIn(
            "environment-reward-contract-changed",
            {finding["data"]["class"] for finding in drift_findings},
        )

    def test_paused_time_and_terminal_mutation_oracles(self):
        env = MiniMetroEnv()
        env.reset(seed=11)
        paused = canonical_checkpoint(env)
        paused["structured"]["is_paused"] = True
        paused["progression"]["is_paused"] = True
        paused_after = deepcopy(paused)
        paused_after["structured"]["steps"] = 1
        terminal = deepcopy(paused_after)
        terminal["structured"]["is_game_over"] = True
        terminal_after = deepcopy(terminal)
        terminal_after["structured"]["score"] = 1
        operations = [operation("paused"), operation("terminal")]
        rows = []
        for index, checkpoint in enumerate((terminal, terminal_after)):
            rows.append(
                {
                    "index": index,
                    "name": operations[index]["name"],
                    "action": deepcopy(operations[index]["action"]),
                    "requestedDtMs": None,
                    "effectiveDtMs": 7,
                    "actionOk": True,
                    "reward": 0,
                    "done": bool(index),
                    "checkpoint": checkpoint,
                }
            )

        classes = {
            finding["data"]["class"]
            for finding in evaluate_oracles(rows, operations, paused)
        }
        self.assertIn("paused-time-progression", classes)
        self.assertIn("terminal-state-mutation", classes)

    def test_paused_noop_detects_non_clock_state_mutation(self):
        env = MiniMetroEnv()
        env.reset(seed=12)
        paused = canonical_checkpoint(env)
        paused["structured"]["is_paused"] = True
        paused["progression"]["is_paused"] = True
        operation_row = operation("paused-noop")
        mutations = {
            "spawning": lambda value: value["spawning"]["stations"][0].update(
                steps_since_last_spawn=999
            ),
            "topology": lambda value: value["topology"].update(is_creating_path=True),
            "rng": lambda value: value["rng"]["python"][1].__setitem__(0, 999),
        }

        for label, mutate in mutations.items():
            with self.subTest(family=label):
                changed = deepcopy(paused)
                mutate(changed)
                row = {
                    "index": 0,
                    "name": operation_row["name"],
                    "action": deepcopy(operation_row["action"]),
                    "requestedDtMs": None,
                    "effectiveDtMs": 7,
                    "actionOk": True,
                    "reward": 0,
                    "done": False,
                    "checkpoint": changed,
                }
                classes = {
                    finding["data"]["class"]
                    for finding in evaluate_oracles([row], [operation_row], paused)
                }
                self.assertIn("paused-state-mutation", classes)

    def test_rejected_pause_on_unchanged_terminal_state_is_not_a_pause_mutation(self):
        env = MiniMetroEnv()
        env.reset(seed=15)
        terminal = canonical_checkpoint(env)
        terminal["structured"]["is_game_over"] = True
        terminal["progression"]["is_game_over"] = True
        operation_row = operation(
            "rejected-terminal-pause", {"type": "pause"}, expected=False
        )
        row = {
            "index": 0,
            "name": operation_row["name"],
            "action": deepcopy(operation_row["action"]),
            "requestedDtMs": None,
            "effectiveDtMs": 7,
            "actionOk": False,
            "reward": 0,
            "done": True,
            "checkpoint": deepcopy(terminal),
        }

        classes = {
            finding["data"]["class"]
            for finding in evaluate_oracles([row], [operation_row], terminal)
        }

        self.assertNotIn("paused-state-mutation", classes)

    def test_done_must_match_both_terminal_checkpoint_flags(self):
        env = MiniMetroEnv()
        env.reset(seed=13)
        initial = canonical_checkpoint(env)
        operation_row = operation("noop")
        cases = (
            (True, False, False),
            (False, True, True),
            (True, True, False),
        )
        for done, structured_terminal, progression_terminal in cases:
            with self.subTest(
                done=done,
                structured=structured_terminal,
                progression=progression_terminal,
            ):
                checkpoint = deepcopy(initial)
                checkpoint["structured"]["is_game_over"] = structured_terminal
                checkpoint["progression"]["is_game_over"] = progression_terminal
                row = {
                    "index": 0,
                    "name": operation_row["name"],
                    "action": deepcopy(operation_row["action"]),
                    "requestedDtMs": None,
                    "effectiveDtMs": 7,
                    "actionOk": True,
                    "reward": 0,
                    "done": done,
                    "checkpoint": checkpoint,
                }
                classes = {
                    finding["data"]["class"]
                    for finding in evaluate_oracles([row], [operation_row], initial)
                }
                self.assertIn("terminal-result-mismatch", classes)

    def test_reference_errors_cover_every_latent_index_family(self):
        env = MiniMetroEnv()
        env.reset(seed=14)
        env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
            dt_ms=1,
        )
        _, _, _, assignment_info = env.step(
            {"type": "assign_locomotive", "path_index": 0},
            dt_ms=0,
        )
        self.assertTrue(assignment_info["action_ok"])
        checkpoint = canonical_checkpoint(env)
        self.assertEqual(reference_errors(checkpoint), [])
        mutations = {
            "station pool": lambda value: value["stationPool"][0][
                "passenger_indices"
            ].append(999),
            "topology": lambda value: value["topology"]["paths"][0][
                "station_indices"
            ].append(999),
            "topology path metro": lambda value: value["topology"]["paths"][0][
                "metro_indices"
            ].append(999),
            "passenger": lambda value: value["passengers"].append(
                {
                    "destination_shape_type": "1",
                    "position": [0, 0],
                    "is_at_destination": False,
                    "wait_ms": 0,
                    "location": {"kind": "station", "index": 999},
                }
            ),
            "travel plan": lambda value: value["travelPlans"].append(
                {
                    "passenger_index": 999,
                    "next_path_index": 999,
                    "next_station_index": 999,
                    "next_station_cursor": 0,
                    "node_path": [],
                }
            ),
            "metro motion": lambda value: value["metroMotion"][0].update(
                current_station_index=999
            ),
            "metro declared path": lambda value: value["metroMotion"][0].update(
                declared_path_index=999
            ),
            "metro segment start": lambda value: value["metroMotion"][0][
                "current_segment"
            ].update(start_station_index=999),
            "metro segment end": lambda value: value["metroMotion"][0][
                "current_segment"
            ].update(end_station_index=999),
            "metro segment index": lambda value: value["metroMotion"][0].update(
                current_segment_index=999
            ),
            "metro segment relation index": lambda value: value["metroMotion"][
                0
            ].update(current_segment_relation_index=999),
            "spawning": lambda value: value["spawning"]["stations"][0].update(
                station_index=999
            ),
            "path button": lambda value: value["progression"]["path_buttons"][0].update(
                path_index=999
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(family=label):
                broken = deepcopy(checkpoint)
                mutate(broken)
                self.assertTrue(reference_errors(broken))


if __name__ == "__main__":
    unittest.main()

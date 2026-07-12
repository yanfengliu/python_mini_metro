import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from agent_play import (
    LEGACY_PLAYTHROUGH_RECORD_SCHEMA,
    LINE_CREDITS_REWARD_CONTRACT,
    PLAYTHROUGH_RECORD_SCHEMA,
    PlaythroughRecord,
    iter_playthrough_observations,
    replay_playthrough,
    replay_playthrough_deliveries,
    run_agent_playthrough,
    run_agent_playthrough_deliveries,
)
from env import MiniMetroEnv


class NoopAgent:
    def reset(self, observation):
        return

    def act(self, observation):
        return {"type": "noop"}


class MetricEnv:
    created_reward_modes = []

    def __init__(self, dt_ms=None, reward_mode="deliveries"):
        self.dt_ms = dt_ms
        self.reward_mode = reward_mode
        self.mediator = SimpleNamespace(
            deliveries=2,
            line_credits=9,
            total_travels_handled=2,
            score=9,
        )
        type(self).created_reward_modes.append(reward_mode)

    def _observation(self, time_ms):
        return {
            "structured": {
                "stations": [],
                "deliveries": self.mediator.deliveries,
                "line_credits": self.mediator.line_credits,
                "score": self.mediator.line_credits,
                "time_ms": time_ms,
            }
        }

    def reset(self, seed=None):
        del seed
        self.mediator.deliveries = 2
        self.mediator.total_travels_handled = 2
        self.mediator.line_credits = 9
        self.mediator.score = 9
        return self._observation(0)

    def step(self, action, dt_ms=None):
        del action, dt_ms
        previous_credits = self.mediator.line_credits
        self.mediator.deliveries += 1
        self.mediator.total_travels_handled += 1
        self.mediator.line_credits = 4
        self.mediator.score = 4
        reward = (
            1
            if self.reward_mode == "deliveries"
            else self.mediator.line_credits - previous_credits
        )
        return self._observation(1), reward, False, {}


class TestAgentPlay(unittest.TestCase):
    def test_new_record_names_deliveries_and_line_credits_without_breaking_score(self):
        final_score, record = run_agent_playthrough(
            agent=NoopAgent(), env=MetricEnv(), max_steps=1
        )

        self.assertEqual(record.schema, PLAYTHROUGH_RECORD_SCHEMA)
        self.assertEqual(record.reward_contract, "deliveries")
        self.assertEqual(record.steps[0].reward, 1)
        self.assertEqual(record.steps[0].deliveries, 3)
        self.assertEqual(record.steps[0].line_credits, 4)
        self.assertEqual(record.steps[0].score, 4)
        self.assertEqual(record.final_deliveries, 3)
        self.assertEqual(record.final_line_credits, 4)
        self.assertEqual(record.final_score, 4)
        self.assertEqual(final_score, 4)

    def test_canonical_entry_points_return_deliveries(self):
        final_deliveries, record = run_agent_playthrough_deliveries(
            agent=NoopAgent(), env=MetricEnv(), max_steps=1
        )

        self.assertEqual(final_deliveries, 3)
        self.assertEqual(replay_playthrough_deliveries(record, env=MetricEnv()), 3)

    def test_replay_constructs_environment_for_record_reward_contract(self):
        MetricEnv.created_reward_modes = []
        delivery_record = PlaythroughRecord(
            seed=1,
            dt_ms=2,
            actions=[{"type": "noop"}],
            schema=PLAYTHROUGH_RECORD_SCHEMA,
            reward_contract="deliveries",
        )
        legacy_record = PlaythroughRecord(
            seed=1,
            dt_ms=2,
            actions=[{"type": "noop"}],
            schema=LEGACY_PLAYTHROUGH_RECORD_SCHEMA,
            reward_contract=LINE_CREDITS_REWARD_CONTRACT,
        )
        schema_less_record = SimpleNamespace(
            seed=1,
            dt_ms=2,
            actions=[{"type": "noop"}],
            final_score=4,
        )

        with patch("agent_play.MiniMetroEnv", MetricEnv):
            self.assertEqual(replay_playthrough(delivery_record), 4)
            self.assertEqual(replay_playthrough(legacy_record), 4)
            self.assertEqual(replay_playthrough(schema_less_record), 4)

        self.assertEqual(
            MetricEnv.created_reward_modes,
            ["deliveries", "line_credits_delta", "line_credits_delta"],
        )

    def test_record_preserves_supplied_environment_default_timestep(self):
        env = MiniMetroEnv(dt_ms=100)

        _, record = run_agent_playthrough(agent=NoopAgent(), env=env, max_steps=2)
        replay_times = [
            observation["structured"]["time_ms"]
            for observation in iter_playthrough_observations(record)
        ]

        self.assertEqual(record.dt_ms, 100)
        self.assertEqual([step.time_ms for step in record.steps], [100, 200])
        self.assertEqual(replay_times, [0, 100, 200])

    def test_supplied_environment_reward_contract_fails_closed(self):
        env = MetricEnv()
        env.reward_mode = "typo"

        with self.assertRaisesRegex(ValueError, "reward contract"):
            run_agent_playthrough(agent=NoopAgent(), env=env, max_steps=1)

    def test_old_style_record_constructor_defaults_to_legacy_contract(self):
        record = PlaythroughRecord(seed=4, dt_ms=5)

        self.assertEqual(record.schema, LEGACY_PLAYTHROUGH_RECORD_SCHEMA)
        self.assertEqual(record.reward_contract, LINE_CREDITS_REWARD_CONTRACT)
        self.assertEqual(record.final_deliveries, 0)
        self.assertEqual(record.final_line_credits, 0)

    def test_record_schema_and_reward_contract_cannot_disagree(self):
        legacy_with_delivery_reward = PlaythroughRecord(
            seed=4,
            dt_ms=5,
            schema=LEGACY_PLAYTHROUGH_RECORD_SCHEMA,
            reward_contract="deliveries",
        )
        v2_without_reward_contract = SimpleNamespace(
            seed=4,
            dt_ms=5,
            schema=PLAYTHROUGH_RECORD_SCHEMA,
            actions=[],
        )

        with self.assertRaisesRegex(ValueError, "legacy"):
            replay_playthrough(legacy_with_delivery_reward)
        with self.assertRaisesRegex(ValueError, "require reward_contract"):
            replay_playthrough(v2_without_reward_contract)

    def test_run_agent_playthrough_records_actions(self):
        final_score, record = run_agent_playthrough(seed=123, max_steps=5, dt_ms=1)

        self.assertIsInstance(final_score, int)
        self.assertEqual(record.final_score, final_score)
        self.assertEqual(record.max_steps, 5)
        self.assertLessEqual(len(record.actions), 5)
        self.assertLessEqual(len(record.steps), 5)

    def test_replay_playthrough_is_deterministic(self):
        final_score, record = run_agent_playthrough(seed=42, max_steps=10, dt_ms=1)
        replay_score = replay_playthrough(record)

        self.assertEqual(replay_score, final_score)

    def test_iter_playthrough_observations_yields_initial_and_steps(self):
        _, record = run_agent_playthrough(seed=7, max_steps=3, dt_ms=1)
        observations = list(iter_playthrough_observations(record))

        self.assertEqual(len(observations), 4)

    def test_run_agent_playthrough_snapshots_reused_mutable_actions(self):
        class ReusingActionAgent:
            def __init__(self):
                self.action = {"type": "noop", "payload": {"call": 0}}

            def reset(self, observation):
                self.action["payload"]["call"] = 0

            def act(self, observation):
                self.action["payload"]["call"] += 1
                return self.action

        agent = ReusingActionAgent()
        _, record = run_agent_playthrough(agent=agent, seed=11, max_steps=2, dt_ms=1)

        self.assertEqual(
            [action["payload"]["call"] for action in record.actions], [1, 2]
        )
        self.assertEqual(
            [step.action["payload"]["call"] for step in record.steps], [1, 2]
        )

        agent.action["payload"]["call"] = 3
        record.actions[0]["payload"]["call"] = 4
        self.assertEqual(record.steps[0].action["payload"]["call"], 1)
        self.assertEqual(record.actions[1]["payload"]["call"], 2)

        record.steps[1].action["payload"]["call"] = 5
        self.assertEqual(record.actions[1]["payload"]["call"], 2)


if __name__ == "__main__":
    unittest.main()

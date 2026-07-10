import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from agent_play import (
    iter_playthrough_observations,
    replay_playthrough,
    run_agent_playthrough,
)


class TestAgentPlay(unittest.TestCase):
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

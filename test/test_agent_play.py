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


if __name__ == "__main__":
    unittest.main()

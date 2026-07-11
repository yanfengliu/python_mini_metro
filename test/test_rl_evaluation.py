from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.evaluation import EpisodeMetrics, evaluate_vector_policy


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, list[bool], bool]] = []

    def predict(
        self,
        observation,
        *,
        state,
        episode_start,
        deterministic,
    ):
        self.calls.append(
            (
                observation,
                state,
                [bool(value) for value in episode_start],
                deterministic,
            )
        )
        return "action", None


class FakeRecurrentModel:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, list[bool], bool]] = []

    def predict(
        self,
        observation,
        *,
        state,
        episode_start,
        deterministic,
    ):
        self.calls.append(
            (
                observation,
                state,
                [bool(value) for value in episode_start],
                deterministic,
            )
        )
        return "action", f"state-{len(self.calls)}"


class FakeVectorEnv:
    num_envs = 1

    def __init__(self) -> None:
        self.step_count = 0

    def reset(self):
        return "reset-observation"

    def step(self, action):
        self.step_count += 1
        done = self.step_count % 2 == 0
        episode = self.step_count // 2
        info = {
            "game_episode": {
                "deliveries": episode * 3,
                "display_score": episode * 2,
                "seed": 40 + episode,
            },
            "termination_reason": "horizon" if done else None,
        }
        return f"observation-{self.step_count}", [0.5], [done], [info]


class TestEvaluateVectorPolicy(unittest.TestCase):
    def test_feedforward_policy_reports_terminal_game_metrics(self) -> None:
        model = FakeModel()
        env = FakeVectorEnv()

        metrics = evaluate_vector_policy(model, env, episodes=2)

        self.assertEqual(
            metrics,
            (
                EpisodeMetrics(1.0, 2, 3, 2, 41, "horizon"),
                EpisodeMetrics(1.0, 2, 6, 4, 42, "horizon"),
            ),
        )
        self.assertEqual(metrics[0].to_dict()["deliveries"], 3)
        self.assertEqual(len(model.calls), 4)
        self.assertTrue(all(state is None for _, state, _, _ in model.calls))
        self.assertEqual(
            [episode_start for _, _, episode_start, _ in model.calls],
            [[True], [False], [True], [False]],
        )
        self.assertTrue(all(deterministic for _, _, _, deterministic in model.calls))

    def test_recurrent_policy_threads_state_and_marks_episode_boundaries(self) -> None:
        model = FakeRecurrentModel()
        env = FakeVectorEnv()

        metrics = evaluate_vector_policy(model, env, episodes=2)

        self.assertEqual(len(metrics), 2)
        self.assertEqual(
            [state for _, state, _, _ in model.calls],
            [None, "state-1", "state-2", "state-3"],
        )
        self.assertEqual(
            [episode_start for _, _, episode_start, _ in model.calls],
            [[True], [False], [True], [False]],
        )
        self.assertTrue(all(deterministic for _, _, _, deterministic in model.calls))

    def test_validates_episode_count_and_single_environment(self) -> None:
        for episodes in (0, -1, True, 1.5):
            with self.subTest(episodes=episodes):
                with self.assertRaises((TypeError, ValueError)):
                    evaluate_vector_policy(
                        FakeModel(), FakeVectorEnv(), episodes=episodes
                    )

        env = FakeVectorEnv()
        env.num_envs = 2
        with self.assertRaisesRegex(ValueError, "exactly one"):
            evaluate_vector_policy(FakeModel(), env, episodes=1)


if __name__ == "__main__":
    unittest.main()

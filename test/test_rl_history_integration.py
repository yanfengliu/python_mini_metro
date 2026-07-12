from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import rl.training as rl_training
from rl.history import DECISION_HISTORY_LAYOUT, contiguous_history, history_for_layout
from rl.protocol import FAST_RENDER_PROFILE, RewardMode, TaskSpec

RL_DEPS_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("gymnasium", "sb3_contrib", "stable_baselines3", "torch")
)


@unittest.skipUnless(
    RL_DEPS_AVAILABLE,
    "Gymnasium, sb3-contrib, Stable-Baselines3, and Torch are optional",
)
class TestHistoryRuntimeIntegration(unittest.TestCase):
    def test_named_history_spawn_order_terminal_shape_and_cleanup(self) -> None:
        from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

        from rl.temporal_history import VecTemporalHistory

        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 1)
        history = history_for_layout(DECISION_HISTORY_LAYOUT)
        env = rl_training.build_vector_env(
            spec,
            n_envs=2,
            seed=31,
            history=history,
        )
        try:
            observation = env.reset()
            next_observation, _, dones, infos = env.step(
                np.zeros((2, 3), dtype=np.int64)
            )

            self.assertIsInstance(env, VecTemporalHistory)
            self.assertIsInstance(env.venv, VecMonitor)
            self.assertIsInstance(env.venv.venv, SubprocVecEnv)
            self.assertEqual(observation.shape, (2, 36, 108, 192))
            self.assertEqual(next_observation.shape, (2, 36, 108, 192))
            self.assertTrue(dones.all())
            for info in infos:
                self.assertIs(info["TimeLimit.truncated"], True)
                self.assertEqual(info["terminal_observation"].shape, (36, 108, 192))
        finally:
            env.close()

    def test_recurrent_episode_start_masks_reset_only_at_episode_boundaries(self):
        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 2)
        env = rl_training.build_vector_env(
            spec,
            n_envs=1,
            seed=41,
            history=history_for_layout(DECISION_HISTORY_LAYOUT),
        )
        try:
            model = rl_training.make_model(
                env,
                seed=41,
                device="cpu",
                n_envs=1,
                n_steps=3,
                n_epochs=1,
                features_dim=32,
            )
            original_forward = model.policy.forward
            episode_starts: list[list[bool]] = []

            def record_forward(
                observation,
                lstm_states,
                episode_start,
                deterministic=False,
            ):
                episode_starts.append(
                    [bool(value) for value in episode_start.detach().cpu().numpy()]
                )
                return original_forward(
                    observation,
                    lstm_states,
                    episode_start,
                    deterministic,
                )

            with patch.object(
                model.policy,
                "forward",
                side_effect=record_forward,
            ):
                model.learn(total_timesteps=3)
        finally:
            env.close()

        self.assertEqual(episode_starts, [[True], [False], [True]])

    def test_model_observation_mismatch_fails_before_rollout(self) -> None:
        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 2)
        source = rl_training.build_vector_env(
            spec,
            n_envs=1,
            seed=51,
            history=contiguous_history(4),
        )
        target = rl_training.build_vector_env(
            spec,
            n_envs=1,
            seed=52,
            history=history_for_layout(DECISION_HISTORY_LAYOUT),
        )
        try:
            model = rl_training.make_model(
                source,
                seed=51,
                device="cpu",
                n_envs=1,
                n_steps=2,
                n_epochs=1,
                features_dim=32,
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = Path(temp_dir) / "model.zip"
                model.save(model_path)
                with self.assertRaisesRegex(ValueError, "Observation spaces"):
                    rl_training.load_model(
                        model_path,
                        algorithm=rl_training.DEFAULT_ALGORITHM,
                        env=target,
                        device="cpu",
                        seed=52,
                    )
        finally:
            target.close()
            source.close()


if __name__ == "__main__":
    unittest.main()

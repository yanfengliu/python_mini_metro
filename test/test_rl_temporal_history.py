from __future__ import annotations

import os
import sys
import unittest
from collections import deque
from collections.abc import Sequence
from importlib.util import find_spec
from typing import Any
from unittest.mock import patch

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

if any(find_spec(name) is None for name in ("gymnasium", "stable_baselines3")):
    raise unittest.SkipTest("Gymnasium and Stable-Baselines3 are optional")

from gymnasium import spaces
from stable_baselines3.common.vec_env import VecEnv, VecFrameStack

from rl.history import DECISION_HISTORY_LAYOUT, contiguous_history, history_for_layout
from rl.temporal_history import VecTemporalHistory


def frame(value: int, *, dtype: Any = np.uint8) -> np.ndarray:
    return np.full((3, 2, 2), value, dtype=dtype)


def batch(*values: int, dtype: Any = np.uint8) -> np.ndarray:
    return np.stack([frame(value, dtype=dtype) for value in values])


def sample_blocks(observation: np.ndarray, env_index: int = 0) -> np.ndarray:
    return observation[env_index].reshape((-1, 3, 2, 2))


class ScriptedVecEnv(VecEnv):
    def __init__(
        self,
        reset_observations: np.ndarray,
        *,
        observation_space: spaces.Space | None = None,
    ) -> None:
        self.reset_observations = reset_observations
        self.steps: deque[
            tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]
        ] = deque()
        self.closed = False
        self.actions = None
        self.render_mode = None
        space = observation_space or spaces.Box(
            low=0,
            high=255,
            shape=tuple(reset_observations.shape[1:]),
            dtype=np.uint8,
        )
        super().__init__(
            num_envs=len(reset_observations),
            observation_space=space,
            action_space=spaces.Discrete(1),
        )

    def queue_step(
        self,
        observations: np.ndarray,
        *,
        rewards: np.ndarray | None = None,
        dones: np.ndarray | None = None,
        infos: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
        count = self.num_envs
        queued_rewards = (
            rewards if rewards is not None else np.zeros(count, dtype=np.float32)
        )
        queued_dones = dones if dones is not None else np.zeros(count, dtype=bool)
        queued_infos = infos if infos is not None else [{} for _ in range(count)]
        self.steps.append((observations, queued_rewards, queued_dones, queued_infos))
        return queued_rewards, queued_dones, queued_infos

    def reset(self) -> np.ndarray:
        return self.reset_observations.copy()

    def step_async(self, actions: np.ndarray) -> None:
        self.actions = actions

    def step_wait(
        self,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
        return self.steps.popleft()

    def close(self) -> None:
        self.closed = True

    def get_attr(
        self, attr_name: str, indices: Any = None
    ) -> list[Any]:  # pragma: no cover - VecEnv plumbing
        return [getattr(self, attr_name)]

    def set_attr(
        self, attr_name: str, value: Any, indices: Any = None
    ) -> None:  # pragma: no cover - VecEnv plumbing
        setattr(self, attr_name, value)

    def env_method(
        self,
        method_name: str,
        *method_args: Any,
        indices: Any = None,
        **method_kwargs: Any,
    ) -> list[Any]:  # pragma: no cover - VecEnv plumbing
        return [getattr(self, method_name)(*method_args, **method_kwargs)]

    def env_is_wrapped(
        self, wrapper_class: type, indices: Any = None
    ) -> list[bool]:  # pragma: no cover - VecEnv plumbing
        return [False] * self.num_envs


class TestVecTemporalHistory(unittest.TestCase):
    def assert_poisoned_until_reset(
        self,
        base: ScriptedVecEnv,
        env: VecTemporalHistory,
        *,
        reset_value: int = 30,
    ) -> None:
        base.actions = None
        with self.assertRaisesRegex(RuntimeError, "reset"):
            env.step_async(np.asarray([0] * base.num_envs))
        self.assertIsNone(base.actions)

        base.reset_observations = batch(
            *(reset_value + index * 100 for index in range(base.num_envs))
        )
        observation = env.reset()
        for env_index in range(base.num_envs):
            expected = [frame(0)] * (env.history.frame_stack - 1)
            expected.append(frame(reset_value + env_index * 100))
            np.testing.assert_array_equal(
                sample_blocks(observation, env_index),
                np.stack(expected),
            )

    def test_multiscale_chronology_zero_fill_wraparound_and_ownership(self) -> None:
        history = history_for_layout(DECISION_HISTORY_LAYOUT)
        base = ScriptedVecEnv(batch(1))
        env = VecTemporalHistory(base, history)

        observation = env.reset()
        retained_reset = observation
        expected_reset = observation.copy()
        self.assertEqual(observation.shape, (1, 36, 2, 2))
        self.assertEqual(observation.dtype, np.uint8)
        self.assertEqual(env.history_buffer_nbytes, 129 * 3 * 2 * 2)

        checkpoints = {1, 7, 16, 64, 128, 129, 130}
        for decision in range(1, 131):
            rewards, dones, infos = base.queue_step(batch(decision + 1))
            observation, actual_rewards, actual_dones, actual_infos = env.step(
                np.asarray([0])
            )
            self.assertIs(actual_rewards, rewards)
            self.assertIs(actual_dones, dones)
            self.assertIs(actual_infos, infos)
            if decision in checkpoints:
                blocks = sample_blocks(observation)
                for index, offset in enumerate(history.offsets):
                    expected = (
                        frame(decision - offset + 1)
                        if offset <= decision
                        else np.zeros((3, 2, 2), dtype=np.uint8)
                    )
                    np.testing.assert_array_equal(blocks[index], expected)

        np.testing.assert_array_equal(retained_reset, expected_reset)

    def test_staggered_terminal_and_truncation_stacks_are_isolated(self) -> None:
        history = contiguous_history(3)
        base = ScriptedVecEnv(batch(10, 110))
        env = VecTemporalHistory(base, history)
        env.reset()
        base.queue_step(batch(11, 111))
        retained_previous, _, _, _ = env.step(np.asarray([0, 0]))
        expected_previous = retained_previous.copy()

        rewards = np.asarray([2.0, 3.0], dtype=np.float32)
        dones = np.asarray([True, False])
        infos = [
            {
                "TimeLimit.truncated": True,
                "marker": "truncated",
                "terminal_observation": frame(12),
            },
            {"marker": "running"},
        ]
        base.queue_step(batch(20, 112), rewards=rewards, dones=dones, infos=infos)
        observation, actual_rewards, actual_dones, actual_infos = env.step(
            np.asarray([0, 0])
        )

        self.assertIs(actual_rewards, rewards)
        self.assertIs(actual_dones, dones)
        self.assertIs(actual_infos, infos)
        self.assertIs(actual_infos[0]["TimeLimit.truncated"], True)
        self.assertEqual(actual_infos[0]["marker"], "truncated")
        np.testing.assert_array_equal(
            sample_blocks(observation, 0),
            np.stack([frame(0), frame(0), frame(20)]),
        )
        np.testing.assert_array_equal(
            sample_blocks(observation, 1),
            np.stack([frame(110), frame(111), frame(112)]),
        )
        np.testing.assert_array_equal(
            actual_infos[0]["terminal_observation"],
            np.concatenate([frame(10), frame(11), frame(12)], axis=0),
        )
        np.testing.assert_array_equal(retained_previous, expected_previous)
        retained_done_observation = observation
        expected_done_observation = observation.copy()
        retained_terminal = actual_infos[0]["terminal_observation"]
        expected_terminal = retained_terminal.copy()

        second_infos = [
            {"marker": "running"},
            {"TimeLimit.truncated": False, "terminal_observation": frame(113)},
        ]
        base.queue_step(
            batch(21, 120),
            dones=np.asarray([False, True]),
            infos=second_infos,
        )
        second, _, _, returned_infos = env.step(np.asarray([0, 0]))
        np.testing.assert_array_equal(
            sample_blocks(second, 0),
            np.stack([frame(0), frame(20), frame(21)]),
        )
        np.testing.assert_array_equal(
            sample_blocks(second, 1),
            np.stack([frame(0), frame(0), frame(120)]),
        )
        np.testing.assert_array_equal(
            returned_infos[1]["terminal_observation"],
            np.concatenate([frame(111), frame(112), frame(113)], axis=0),
        )
        np.testing.assert_array_equal(
            retained_done_observation, expected_done_observation
        )
        np.testing.assert_array_equal(retained_terminal, expected_terminal)

    def test_malformed_steps_fail_before_history_mutation(self) -> None:
        malformed_terminals: Sequence[dict[str, Any]] = (
            {},
            {"terminal_observation": np.zeros((3, 1, 1), dtype=np.uint8)},
            {"terminal_observation": frame(3, dtype=np.float32)},
        )
        for malformed_info in malformed_terminals:
            with self.subTest(malformed_info=malformed_info):
                base = ScriptedVecEnv(batch(1))
                env = VecTemporalHistory(base, contiguous_history(3))
                env.reset()
                base.queue_step(batch(2))
                env.step(np.asarray([0]))
                base.queue_step(
                    batch(9),
                    dones=np.asarray([True]),
                    infos=[malformed_info],
                )
                with self.assertRaises((TypeError, ValueError)):
                    env.step(np.asarray([0]))

                self.assert_poisoned_until_reset(base, env)

        malformed_observations = (
            batch(2, dtype=np.float32),
            np.zeros((1, 3, 1, 1), dtype=np.uint8),
        )
        for malformed_observation in malformed_observations:
            with self.subTest(malformed_observation=malformed_observation):
                base = ScriptedVecEnv(batch(1))
                env = VecTemporalHistory(base, contiguous_history(2))
                env.reset()
                base.queue_step(malformed_observation)
                with self.assertRaises((TypeError, ValueError)):
                    env.step(np.asarray([0]))
                self.assert_poisoned_until_reset(base, env)

        malformed_metadata: Sequence[tuple[Any, Any]] = (
            (np.asarray([0], dtype=np.int8), [{}]),
            (np.asarray([[False]]), [{}]),
            (np.asarray([False]), []),
            (np.asarray([False]), [None]),
        )
        for malformed_dones, malformed_infos in malformed_metadata:
            with self.subTest(
                malformed_dones=malformed_dones,
                malformed_infos=malformed_infos,
            ):
                base = ScriptedVecEnv(batch(1))
                env = VecTemporalHistory(base, contiguous_history(2))
                env.reset()
                base.queue_step(
                    batch(2),
                    dones=malformed_dones,
                    infos=malformed_infos,
                )
                with self.assertRaises((TypeError, ValueError)):
                    env.step(np.asarray([0]))
                self.assert_poisoned_until_reset(base, env)

    def test_malformed_reset_poisoning_and_candidate_resource_shape(self) -> None:
        base = ScriptedVecEnv(batch(1))
        env = VecTemporalHistory(base, contiguous_history(3))
        env.reset()
        base.queue_step(batch(2))
        env.step(np.asarray([0]))
        base.reset_observations = batch(9, dtype=np.float32)
        with self.assertRaises(TypeError):
            env.reset()
        self.assert_poisoned_until_reset(base, env)

        with patch("rl.temporal_history.np.zeros", side_effect=MemoryError):
            with self.assertRaises(MemoryError):
                env.reset()
        self.assert_poisoned_until_reset(base, env, reset_value=40)

        candidate_shape = (8, 3, 108, 192)
        candidate_base = ScriptedVecEnv(np.zeros(candidate_shape, dtype=np.uint8))
        candidate = VecTemporalHistory(
            candidate_base,
            history_for_layout(DECISION_HISTORY_LAYOUT),
        )
        self.assertEqual(candidate.history_buffer_nbytes, 64_198_656)
        self.assertEqual(candidate.observation_space.shape, (36, 108, 192))
        candidate_observation = candidate.reset()
        self.assertEqual(candidate_observation.nbytes, 5_971_968)
        self.assertEqual(candidate_observation.dtype, np.uint8)

    def test_contiguous_layout_matches_sb3_frame_stack(self) -> None:
        for frame_stack in (1, 4, 8, 13):
            with self.subTest(frame_stack=frame_stack):
                ours_base = ScriptedVecEnv(batch(1))
                sb3_base = ScriptedVecEnv(batch(1))
                ours = VecTemporalHistory(ours_base, contiguous_history(frame_stack))
                sb3 = VecFrameStack(
                    sb3_base, n_stack=frame_stack, channels_order="first"
                )
                np.testing.assert_array_equal(ours.reset(), sb3.reset())

                for value in range(2, frame_stack + 3):
                    ours_base.queue_step(batch(value))
                    sb3_base.queue_step(batch(value))
                    ours_step, _, _, _ = ours.step(np.asarray([0]))
                    sb3_step, _, _, _ = sb3.step(np.asarray([0]))
                    np.testing.assert_array_equal(ours_step, sb3_step)

                ours_infos = [
                    {
                        "TimeLimit.truncated": True,
                        "terminal_observation": frame(200),
                    }
                ]
                sb3_infos = [
                    {
                        "TimeLimit.truncated": True,
                        "terminal_observation": frame(200),
                    }
                ]
                ours_base.queue_step(
                    batch(201), dones=np.asarray([True]), infos=ours_infos
                )
                sb3_base.queue_step(
                    batch(201), dones=np.asarray([True]), infos=sb3_infos
                )
                ours_step, _, _, ours_returned_infos = ours.step(np.asarray([0]))
                sb3_step, _, _, sb3_returned_infos = sb3.step(np.asarray([0]))
                np.testing.assert_array_equal(ours_step, sb3_step)
                np.testing.assert_array_equal(
                    ours_returned_infos[0]["terminal_observation"],
                    sb3_returned_infos[0]["terminal_observation"],
                )

    def test_reset_space_validation_and_close(self) -> None:
        unreset_base = ScriptedVecEnv(batch(1))
        unreset = VecTemporalHistory(unreset_base, contiguous_history(2))
        with self.assertRaisesRegex(RuntimeError, "reset"):
            unreset.step_async(np.asarray([0]))
        self.assertIsNone(unreset_base.actions)

        base = ScriptedVecEnv(batch(1, 101))
        env = VecTemporalHistory(base, contiguous_history(4))
        env.reset()
        base.queue_step(batch(2, 102))
        env.step(np.asarray([0, 0]))
        base.reset_observations = batch(30, 130)
        reset = env.reset()

        self.assertEqual(env.observation_space.shape, (12, 2, 2))
        self.assertEqual(env.observation_space.dtype, np.uint8)
        np.testing.assert_array_equal(
            sample_blocks(reset, 0),
            np.stack([frame(0), frame(0), frame(0), frame(30)]),
        )
        np.testing.assert_array_equal(
            sample_blocks(reset, 1),
            np.stack([frame(0), frame(0), frame(0), frame(130)]),
        )
        env.close()
        self.assertTrue(base.closed)

        invalid_spaces = (
            spaces.Box(low=0, high=1, shape=(3, 2, 2), dtype=np.float32),
            spaces.Box(low=0, high=255, shape=(4, 2, 2), dtype=np.uint8),
            spaces.Box(low=1, high=255, shape=(3, 2, 2), dtype=np.uint8),
        )
        for invalid_space in invalid_spaces:
            with self.subTest(invalid_space=invalid_space):
                invalid_base = ScriptedVecEnv(batch(1), observation_space=invalid_space)
                with self.assertRaises((TypeError, ValueError)):
                    VecTemporalHistory(invalid_base, contiguous_history(4))
                self.assertTrue(invalid_base.closed)


if __name__ == "__main__":
    unittest.main()

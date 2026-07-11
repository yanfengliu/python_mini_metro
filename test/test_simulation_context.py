from __future__ import annotations

import os
import random
import sys
import unittest

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from simulation_context import SimulationContext


def assert_numpy_random_state_equal(
    case: unittest.TestCase, left: tuple, right: tuple
) -> None:
    case.assertEqual(left[0], right[0])
    np.testing.assert_array_equal(left[1], right[1])
    case.assertEqual(left[2:], right[2:])


class TestSimulationContext(unittest.TestCase):
    def test_mediator_accepts_context_or_seed_but_not_both(self) -> None:
        context = SimulationContext(seed=7)

        mediator = Mediator(context=context)

        self.assertIs(mediator.context, context)
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            Mediator(seed=7, context=context)

    def test_seed_creates_repeatable_independent_python_and_numpy_streams(self) -> None:
        first = SimulationContext(seed=123)
        second = SimulationContext(seed=123)

        self.assertEqual(
            [first.python_random.random() for _ in range(4)],
            [second.python_random.random() for _ in range(4)],
        )
        np.testing.assert_array_equal(
            first.numpy_random.random(4), second.numpy_random.random(4)
        )

    def test_seeded_envs_remain_equal_when_stepped_interleaved(self) -> None:
        first = MiniMetroEnv(dt_ms=17)
        second = MiniMetroEnv(dt_ms=17)
        first.reset(seed=456)
        second.reset(seed=456)

        for _ in range(12):
            first.step({"type": "noop"})
            second.step({"type": "noop"})
            self.assertEqual(canonical_checkpoint(first), canonical_checkpoint(second))

    def test_env_reset_and_step_do_not_change_host_global_rngs(self) -> None:
        random.seed(8128)
        np.random.seed(4096)
        python_before = random.getstate()
        numpy_before = np.random.get_state()

        env = MiniMetroEnv(dt_ms=17)
        env.reset(seed=99)
        for _ in range(5):
            env.step({"type": "noop"})

        self.assertEqual(random.getstate(), python_before)
        assert_numpy_random_state_equal(self, np.random.get_state(), numpy_before)

    def test_checkpoint_tracks_both_context_rng_streams(self) -> None:
        env = MiniMetroEnv()
        env.reset(seed=789)
        initial = canonical_checkpoint(env)

        env.mediator.context.python_random.random()
        after_python = canonical_checkpoint(env)
        self.assertNotEqual(initial["rng"]["python"], after_python["rng"]["python"])
        self.assertEqual(initial["rng"]["numpy"], after_python["rng"]["numpy"])

        env.mediator.context.numpy_random.random()
        after_numpy = canonical_checkpoint(env)
        self.assertEqual(after_python["rng"]["python"], after_numpy["rng"]["python"])
        self.assertNotEqual(after_python["rng"]["numpy"], after_numpy["rng"]["numpy"])


if __name__ == "__main__":
    unittest.main()

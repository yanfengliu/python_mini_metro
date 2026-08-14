"""Behaviour-cloning data collection must report what the expert actually did.

The first version read lifetime deliveries from a privileged snapshot taken
after the episode finished. A vector environment auto-resets on termination, so
that snapshot describes the *next* game and every expert episode was recorded as
0 deliveries -- while the same expert scored 20 standalone. A collector that
silently reports zero looks like a weak expert rather than a broken meter.
"""

import os
import sys
import unittest

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pretrain_bc  # noqa: E402

from rl.history import default_history  # noqa: E402
from rl.protocol import TaskSpec  # noqa: E402
from rl.training import build_vector_env  # noqa: E402


class ExpertCollectionTest(unittest.TestCase):
    def setUp(self):
        self.vec = build_vector_env(
            TaskSpec(), n_envs=1, seed=0, history=default_history()
        )
        self.addCleanup(self.vec.close)

    def test_reports_the_deliveries_the_expert_actually_earned(self):
        kept, deliveries, taken = pretrain_bc.expert_episode(
            self.vec,
            noop_keep=1.0,
            rng=np.random.default_rng(0),
            max_decisions=500,
        )

        self.assertGreater(
            deliveries,
            0,
            "the scripted expert delivers on this seed, so a zero here means the "
            "count was read after the vector env auto-reset rather than accrued "
            "during the episode",
        )
        self.assertGreater(taken, 0)
        self.assertGreater(len(kept), 0)

    def test_kept_samples_carry_the_stacked_observation_and_a_valid_action(self):
        kept, _, _ = pretrain_bc.expert_episode(
            self.vec,
            noop_keep=1.0,
            rng=np.random.default_rng(0),
            max_decisions=120,
        )

        observation, action = kept[0]
        self.assertEqual(observation.shape, self.vec.observation_space.shape)
        self.assertTrue(self.vec.action_space.contains(action))

    def test_the_expert_draws_a_route_rather_than_only_waiting(self):
        """Cloning only noops would teach the policy that doing nothing is correct."""
        kept, _, _ = pretrain_bc.expert_episode(
            self.vec,
            noop_keep=0.0,
            rng=np.random.default_rng(0),
            max_decisions=500,
        )

        kinds = {int(action[0]) for _, action in kept}
        self.assertTrue(
            {1, 2, 3} <= kinds,
            f"expected motion, pointer-down and pointer-up in the demonstrations, "
            f"saw kinds {sorted(kinds)}",
        )


if __name__ == "__main__":
    unittest.main()

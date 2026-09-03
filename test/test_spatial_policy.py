"""The live policy's coordinates must come from the heatmap, not the flat head.

The spatial pointer measured 11.8x the probability on the expert's exact pixel,
but that gain only exists if the heatmap actually reaches the action
distribution. The failure mode is silent: if the stashed pointer logits are
missing, the policy falls back to the flat categorical, training runs, losses
descend, and nothing announces that the change was a no-op.

These tests compare probabilities rather than logits, because
``torch.distributions.Categorical`` normalises logits internally -- a raw-value
comparison reports a mismatch even when the wiring is correct.
"""

import os
import sys
import unittest
from importlib.util import find_spec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

if any(
    find_spec(name) is None for name in ("sb3_contrib", "stable_baselines3", "torch")
):
    raise unittest.SkipTest("PyTorch, Stable-Baselines3 and sb3-contrib are optional")

import torch  # noqa: E402

from rl.history import default_history  # noqa: E402
from rl.protocol import TaskSpec  # noqa: E402
from rl.spatial_policy import (  # noqa: E402
    SpatialPointerExtractor,
    build_spatial_policy_class,
)
from rl.training import build_vector_env  # noqa: E402


class SpatialPolicyWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sb3_contrib import RecurrentPPO

        cls.vec = build_vector_env(
            TaskSpec(), n_envs=1, seed=0, history=default_history()
        )
        cls.model = RecurrentPPO(
            build_spatial_policy_class(),
            cls.vec,
            device="cpu",
            n_steps=16,
            batch_size=8,
            policy_kwargs=dict(features_extractor_class=SpatialPointerExtractor),
        )

    @classmethod
    def tearDownClass(cls):
        cls.vec.close()

    def _distribution(self):

        policy = self.model.policy
        observation = torch.as_tensor(self.vec.reset()).float() / 255.0
        shape = (policy.lstm_actor.num_layers, 1, policy.lstm_actor.hidden_size)
        zeros = (torch.zeros(shape), torch.zeros(shape))
        starts = torch.ones(1)
        with torch.no_grad():
            features = policy.extract_features(observation)
            stashed = policy.features_extractor.pointer_logits
            latent, _ = policy._process_sequence(
                features, zeros, starts, policy.lstm_actor
            )
            latent_pi = policy.mlp_extractor.forward_actor(latent)
            distribution = policy._get_action_dist_from_latent(latent_pi)
            flat = policy.action_net(latent_pi)[0]
        return distribution, stashed, flat

    def test_coordinates_come_from_the_heatmap(self):
        distribution, stashed, _ = self._distribution()
        x_logits, y_logits = stashed

        self.assertTrue(
            torch.allclose(
                distribution.distribution[1].probs[0],
                torch.softmax(x_logits[0], -1),
                atol=1e-5,
            ),
            "the x distribution does not match the heatmap, so the policy has "
            "silently fallen back to the flat categorical head",
        )
        self.assertTrue(
            torch.allclose(
                distribution.distribution[2].probs[0],
                torch.softmax(y_logits[0], -1),
                atol=1e-5,
            )
        )

    def test_coordinates_are_not_the_flat_head_output(self):
        """Guards against a comparison that would pass even if nothing changed."""
        distribution, _, flat = self._distribution()

        self.assertFalse(
            torch.allclose(
                distribution.distribution[1].probs[0],
                torch.softmax(flat[8 : 8 + 192], -1),
                atol=1e-4,
            ),
            "the x distribution equals the flat head's slice, so replacing it "
            "changed nothing",
        )

    def test_action_kind_still_sees_history(self):
        """Only the pointer bypasses the LSTM; kind selection must not."""
        distribution, _, flat = self._distribution()

        self.assertTrue(
            torch.allclose(
                distribution.distribution[0].probs[0],
                torch.softmax(flat[:8], -1),
                atol=1e-5,
            )
        )

    def test_a_short_learn_runs_end_to_end(self):
        self.model.learn(total_timesteps=32)


if __name__ == "__main__":
    unittest.main()

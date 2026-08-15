"""The pointer head must score each action from the entities it names.

The flat MLP predicts all 364 logits from one 64-unit vector, so nothing links
observation slot i to action index i -- that correspondence is memorised. This
head gathers station and line embeddings per action instead, and the property
worth pinning is causal rather than architectural: changing one station's
features must move the actions naming that station and leave the others alone.

Without this test the head could silently degrade into a flat one -- if the
gather indices were wrong, or the embeddings unused, training would still run and
losses would still fall.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402
import torch  # noqa: E402

from rl.semantic_env import (  # noqa: E402
    ACTION_TABLE,
    STATION_FEATURES,
    ActionKind,
    SemanticMetroEnv,
)
from rl.semantic_nets import PointerExtractor, build_pointer_policy_class  # noqa: E402

NAMING_KINDS = (ActionKind.CONNECT, ActionKind.EXTEND_LINE, ActionKind.PREPEND_LINE)


class PointerHeadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sb3_contrib import MaskablePPO
        from sb3_contrib.common.wrappers import ActionMasker
        from stable_baselines3.common.vec_env import DummyVecEnv

        venv = DummyVecEnv(
            [lambda: ActionMasker(SemanticMetroEnv(), lambda e: e.action_masks())]
        )
        cls.model = MaskablePPO(
            build_pointer_policy_class(),
            venv,
            device="cpu",
            n_steps=32,
            batch_size=16,
            policy_kwargs=dict(features_extractor_class=PointerExtractor),
        )
        cls.venv = venv

    @classmethod
    def tearDownClass(cls):
        cls.venv.close()

    def _logits(self, observation):
        policy = self.model.policy
        with torch.no_grad():
            tensor = torch.as_tensor(observation[None]).float()
            features = policy.extract_features(tensor)
            latent, _ = policy.mlp_extractor(features)
            return policy._action_logits(latent)[0]

    def _mid_game_observation(self):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=0)
        rng = np.random.default_rng(0)
        for _ in range(200):
            observation, _, terminated, truncated, _ = env.step(
                int(rng.choice(np.flatnonzero(env.action_masks())))
            )
            if terminated or truncated:
                break
        env.close()
        return observation

    def test_changing_a_station_moves_only_the_actions_that_name_it(self):
        observation = self._mid_game_observation()
        target = 2
        base = self._logits(observation)

        perturbed = observation.copy()
        block = slice(target * STATION_FEATURES, (target + 1) * STATION_FEATURES)
        perturbed[block] += 0.5
        moved = (self._logits(perturbed) - base).abs()

        naming = [
            index
            for index, (kind, first, second) in enumerate(ACTION_TABLE)
            if kind in NAMING_KINDS and target in (first, second)
        ]
        unrelated = [
            index
            for index, (kind, first, second) in enumerate(ACTION_TABLE)
            if kind in NAMING_KINDS and target not in (first, second)
        ]

        naming_shift = float(moved[naming].mean())
        other_shift = float(moved[unrelated].mean())
        self.assertGreater(
            naming_shift,
            other_shift * 10,
            f"actions naming station {target} moved {naming_shift:.5f} against "
            f"{other_shift:.5f} for the rest; the head is not reading the entity "
            "each action refers to and has degraded to a flat categorical",
        )

    def test_it_emits_one_logit_per_table_entry(self):
        observation = self._mid_game_observation()

        self.assertEqual(self._logits(observation).shape[0], len(ACTION_TABLE))

    def test_a_short_learn_runs_end_to_end(self):
        self.model.learn(total_timesteps=64)


if __name__ == "__main__":
    unittest.main()

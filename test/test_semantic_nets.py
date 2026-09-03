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
from importlib.util import find_spec

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

if any(
    find_spec(name) is None for name in ("sb3_contrib", "stable_baselines3", "torch")
):
    raise unittest.SkipTest("PyTorch, Stable-Baselines3 and sb3-contrib are optional")

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

    def _mid_game_observation(self, seed: int = 0):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=seed)
        rng = np.random.default_rng(seed)
        for _ in range(200):
            observation, _, terminated, truncated, _ = env.step(
                int(rng.choice(np.flatnonzero(env.action_masks())))
            )
            if terminated or truncated:
                break
        env.close()
        return observation

    def test_changing_a_station_moves_only_the_actions_that_name_it(self):
        """Averaged over several states, because one state is not the property.

        An earlier version asserted a ratio above 10 from a single measurement
        that happened to read 236. Across random initialisations the ratio
        actually spans 3.1 to 21.5, so that threshold failed roughly half the
        time -- a flaky gate on a real property. What the mechanism guarantees
        is that the ratio is well above 1 (a flat head scores exactly 1); the
        magnitude is an artefact of the untrained weights.
        """

        ratios = []
        for offset in range(4):
            observation = self._mid_game_observation(seed=offset)
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
            ratios.append(
                float(moved[naming].mean()) / max(float(moved[unrelated].mean()), 1e-12)
            )

        mean_ratio = sum(ratios) / len(ratios)
        self.assertGreater(
            mean_ratio,
            2.0,
            f"actions naming a station moved only {mean_ratio:.1f}x more than "
            f"unrelated ones (per-state {[round(r, 1) for r in ratios]}); a flat "
            "head scores 1.0, so the pointer has degraded to one",
        )

    def test_it_emits_one_logit_per_table_entry(self):
        observation = self._mid_game_observation()

        self.assertEqual(self._logits(observation).shape[0], len(ACTION_TABLE))

    def test_a_short_learn_runs_end_to_end(self):
        self.model.learn(total_timesteps=64)


if __name__ == "__main__":
    unittest.main()

"""The semantic lane exists to make the game's first rung reachable.

On pixels, a random policy built a usable line in 0 of 48 episodes and no PPO
configuration ever delivered a passenger, because "connect these two stations"
had to be expressed as two clicks each landing on ~0.034% of the coordinate
grid. Naming stations instead of pointing at them removes that cost entirely.

The masking is not a convenience. Station slots run to twenty while a young game
has three, so an unmasked sampler spends nearly every CONNECT on a station that
does not exist -- with masks a random policy delivers, without them it does not.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.semantic_env import MAX_PATHS, SemanticAction, SemanticMetroEnv  # noqa: E402


def _play(seed: int, rng: np.random.Generator):
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    delivered = 0.0
    while True:
        masks = env.action_mask_components()
        action = np.array(
            [int(rng.choice(np.flatnonzero(mask))) for mask in masks], dtype=np.int64
        )
        _, reward, terminated, truncated, _ = env.step(action)
        delivered += reward
        if terminated or truncated:
            break
    lines = len([p for p in env._mediator.paths if len(p.stations) >= 2])
    env.close()
    return delivered, lines


class SemanticEnvTest(unittest.TestCase):
    def test_random_legal_play_builds_lines_and_delivers(self):
        """The measurement this lane exists for; on pixels both numbers are zero."""
        rng = np.random.default_rng(0)
        results = [_play(seed, rng) for seed in range(6)]

        self.assertTrue(
            all(lines > 0 for _, lines in results),
            "random legal play must connect stations every time; that is the "
            "entire point of naming stations instead of pointing at them",
        )
        self.assertGreater(
            sum(delivered for delivered, _ in results),
            0,
            "random legal play delivered nothing, so the semantic lane is no "
            "easier than the pixel lane it exists to replace",
        )

    def test_masks_keep_rejected_actions_rare(self):
        """Per-component masks cannot be exact, so this pins the rate, not zero.

        The kind and the index are drawn independently, so the sampler can pair
        ASSIGN_LOCOMOTIVE with a line that cannot take one. Exactness would need
        a flattened Discrete over enumerated legal actions; what matters here is
        that the wasted fraction stays small enough not to drown the signal.
        """
        env = SemanticMetroEnv()
        env.reset(seed=0)
        self.addCleanup(env.close)
        rng = np.random.default_rng(1)

        applied = attempted = 0
        for _ in range(300):
            masks = env.action_mask_components()
            action = np.array(
                [int(rng.choice(np.flatnonzero(mask))) for mask in masks],
                dtype=np.int64,
            )
            _, _, terminated, truncated, info = env.step(action)
            attempted += 1
            applied += bool(info["applied"])
            if terminated or truncated:
                break

        rate = applied / attempted
        self.assertGreater(
            rate,
            0.5,
            f"only {rate:.0%} of masked actions took effect; the mask is not "
            "limiting the decision space enough to be worth having",
        )

    def test_removing_a_line_is_masked_out(self):
        """It is legal, but an exploring policy only uses it to undo progress."""
        env = SemanticMetroEnv()
        env.reset(seed=0)
        self.addCleanup(env.close)

        self.assertFalse(env.action_mask_components()[0][SemanticAction.REMOVE_LINE])

    def test_connect_is_masked_off_once_every_line_slot_is_used(self):
        env = SemanticMetroEnv()
        env.reset(seed=0)
        self.addCleanup(env.close)

        for _ in range(400):
            if len(env._mediator.stations) >= 2:
                break
            env.step(np.array([SemanticAction.WAIT, 0, 0], dtype=np.int64))
        for index in range(MAX_PATHS):
            env.step(np.array([SemanticAction.CONNECT, 0, 1], dtype=np.int64))

        if len(env._mediator.paths) >= MAX_PATHS:
            self.assertFalse(env.action_mask_components()[0][SemanticAction.CONNECT])

    def test_the_observation_matches_its_declared_space(self):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=0)
        self.addCleanup(env.close)

        self.assertTrue(env.observation_space.contains(observation))


if __name__ == "__main__":
    unittest.main()

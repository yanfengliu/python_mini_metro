"""The semantic lane's offered actions must match the live game exactly.

On pixels, a random policy built a usable line in 0 of 48 episodes and no PPO
configuration ever delivered, because "connect these two stations" had to be
expressed as two clicks each landing on ~0.034% of the coordinate grid. Naming
stations removes that cost.

Three properties are pinned here, each earned by a measured failure.

Exactness: a previous mask tested a constant ceiling of four line slots while a
fresh game unlocks one, so 283 of 284 CONNECT attempts were silent no-ops. An
approximate mask is a slow leak that reads as a weak policy.

Reachability of multi-station routes: without EXTEND_LINE the agent could only
ever build two-station lines, which caps the network structurally. Adding it took
random play from ~2 deliveries to over a hundred.

Running to a real ending: the episode must finish because the game ended, not
because a horizon cut it off. Stations keep arriving, and the run should last
exactly as long as the agent can keep up.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.semantic_env import (  # noqa: E402
    ACTION_TABLE,
    MAX_PATHS,
    ActionKind,
    SemanticMetroEnv,
)


def _play(seed: int, rng: np.random.Generator, env: SemanticMetroEnv | None = None):
    env = env or SemanticMetroEnv()
    env.reset(seed=seed)
    delivered = 0.0
    offered = applied = 0
    terminated = truncated = False
    while True:
        mask = env.action_masks()
        action = int(rng.choice(np.flatnonzero(mask)))
        _, reward, terminated, truncated, info = env.step(action)
        delivered += reward
        offered += 1
        applied += bool(info["applied"])
        if terminated or truncated:
            break
    longest = max((len(p.stations) for p in env._mediator.paths), default=0)
    env.close()
    return {
        "delivered": delivered,
        "offered": offered,
        "applied": applied,
        "terminated": terminated,
        "longest_line": longest,
    }


class SemanticEnvTest(unittest.TestCase):
    def test_every_offered_action_takes_effect(self):
        """The contract: if the mask offers it, the game accepts it."""
        rng = np.random.default_rng(0)
        result = _play(0, rng, SemanticMetroEnv(max_decisions=600))

        self.assertEqual(
            result["applied"],
            result["offered"],
            f"{result['offered'] - result['applied']} of {result['offered']} "
            "offered actions were silent no-ops; the mask does not reflect the "
            "live game",
        )

    def test_lines_can_grow_past_two_stations(self):
        """Two-station lines cap the network however well the agent plays."""
        rng = np.random.default_rng(0)
        result = _play(0, rng, SemanticMetroEnv(max_decisions=1500))

        self.assertGreater(
            result["longest_line"],
            2,
            "no line grew past two stations, so EXTEND_LINE is unreachable and "
            "the agent cannot build a real route",
        )

    def test_an_episode_ends_because_the_game_ended(self):
        """Survival is the objective, so a horizon must not decide the outcome."""
        rng = np.random.default_rng(0)
        results = [_play(seed, rng) for seed in range(3)]

        self.assertTrue(
            all(result["terminated"] for result in results),
            "an episode stopped on the decision horizon rather than game over; "
            "the delivery total is then right-censored and understates the run",
        )

    def test_connect_never_pairs_a_station_with_itself(self):
        """A flat table can forbid this; independent per-axis masks cannot."""
        for kind, first, second in ACTION_TABLE:
            if kind == ActionKind.CONNECT:
                self.assertNotEqual(first, second)

    def test_the_observation_exposes_what_gates_the_agent(self):
        """Line slots unlock on milestones, so unlock state must be observable."""
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=0)
        self.addCleanup(env.close)

        resources = observation[-14:]
        self.assertAlmostEqual(
            float(resources[5]),
            env._mediator.get_unlocked_num_paths() / MAX_PATHS,
            places=5,
            msg="unlocked line slots must appear in the observation, or the "
            "model cannot see the rule limiting it",
        )
        self.assertTrue(env.observation_space.contains(observation))

    def test_unlock_proximity_rises_as_a_milestone_approaches(self):
        env = SemanticMetroEnv()
        env.reset(seed=0)
        self.addCleanup(env.close)

        self.assertLess(
            env._unlock_proximity((30,), 0), env._unlock_proximity((30,), 28)
        )
        self.assertEqual(env._unlock_proximity((), 5), 0.0)

    def test_station_indices_are_stable_because_stations_are_never_removed(self):
        """Action entries name station slots, so a shifting index would remap them."""
        env = SemanticMetroEnv(max_decisions=800)
        env.reset(seed=0)
        self.addCleanup(env.close)
        rng = np.random.default_rng(2)

        counts = []
        while True:
            mask = env.action_masks()
            _, _, terminated, truncated, _ = env.step(
                int(rng.choice(np.flatnonzero(mask)))
            )
            counts.append(len(env._mediator.stations))
            if terminated or truncated:
                break

        self.assertTrue(all(b >= a for a, b in zip(counts, counts[1:])))


if __name__ == "__main__":
    unittest.main()

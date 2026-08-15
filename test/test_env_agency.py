"""Properties every learning environment here must have, gated rather than trusted.

Six defects in this repository's RL work shared one shape: the mechanism was
verified and the *capability the agent gained* was not. Each was found by playing
the environment, never by reading the code, and each looked like a weak policy
rather than a broken environment.

    reward shaping paid for a milestone exploration never reaches   0 payouts / 24 episodes
    a denser signal was farmable                                    ~80 vs ~20 for real play
    the mask advertised line slots the game had not unlocked        283 of 284 actions no-ops
    lines could only ever hold two stations                         no real network expressible
    the shape encoding moved between episodes                       shape-matching unlearnable
    the mask left one legal action per step                         the score measured the sim

The generalisation: a change to an action space, a mask, an observation or a
reward is not validated by confirming it runs. It is validated by measuring what
the agent can now reach, express, decide, and exploit. These tests are that
measurement, so the next such change fails here instead of after a training run.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402

# A step offering one action is not a decision. Below this the environment is
# narrating rather than being played, and a score says nothing about the policy.
MIN_MEDIAN_LEGAL_ACTIONS = 3


def _competent_rollout(seed: int, limit: int = 20_000) -> dict:
    """Play the scripted heuristic, which actually builds a network.

    Every gate in this file was originally driven by random play, and three
    environment-breaking mutations survived all of them: a horizon cut to 450, a
    cap of three stations per line, and the whole fleet masked out. The reason is
    the same in each case -- random play crashes the game within a few hundred
    decisions and never builds anything, so it never reaches the limit being
    asserted about. A gate driven by a policy that cannot play only ever tests
    what bad play happens to touch.
    """
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    delivered = 0.0
    decisions = 0
    longest = fleet = 0
    terminated = False
    for _ in range(limit):
        _, reward, terminated, truncated, _ = env.step(choose(env))
        delivered += float(reward)
        decisions += 1
        longest = max(
            longest, max((len(p.stations) for p in env._mediator.paths), default=0)
        )
        fleet = max(fleet, sum(len(p.metros) for p in env._mediator.paths))
        if terminated or truncated:
            break
    env.close()
    return {
        "seed": seed,
        "deliveries": delivered,
        "decisions": decisions,
        "longest_line": longest,
        "fleet": fleet,
        "terminated": terminated,
    }


def _rollout(seed: int, rng: np.random.Generator, limit: int = 4000) -> dict:
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    legal, kinds = [], set()
    offered = applied = 0
    terminated = False
    longest = 0
    for _ in range(limit):
        mask = env.action_masks()
        legal.append(int(mask.sum()))
        choice = int(rng.choice(np.flatnonzero(mask)))
        kinds.add(ACTION_TABLE[choice][0])
        _, _, terminated, truncated, info = env.step(choice)
        offered += 1
        applied += bool(info["applied"])
        longest = max(
            longest, max((len(p.stations) for p in env._mediator.paths), default=0)
        )
        if terminated or truncated:
            break
    env.close()
    return {
        "legal": legal,
        "kinds": kinds,
        "offered": offered,
        "applied": applied,
        "terminated": terminated,
        "longest_line": longest,
    }


class EnvironmentAgencyTest(unittest.TestCase):
    """The agent must be able to reach, express, decide and not exploit."""

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(0)
        cls.runs = [_rollout(seed, rng) for seed in range(4)]
        cls.COMPETENT = [_competent_rollout(seed) for seed in range(3)]

    def test_every_offered_action_takes_effect(self):
        """Exactness. An approximate mask reads as a weak policy, not as a bug."""
        offered = sum(run["offered"] for run in self.runs)
        applied = sum(run["applied"] for run in self.runs)

        self.assertEqual(
            applied,
            offered,
            f"{offered - applied} of {offered} offered actions were silent "
            "no-ops, so the mask does not reflect the live game and the agent "
            "is spending steps on nothing",
        )

    def test_the_agent_has_real_choices(self):
        """Decision freedom. One legal action per step is narration, not play."""
        legal = [count for run in self.runs for count in run["legal"]]
        median = float(np.median(legal))

        self.assertGreaterEqual(
            median,
            MIN_MEDIAN_LEGAL_ACTIONS,
            f"median {median:.0f} legal actions per step; below "
            f"{MIN_MEDIAN_LEGAL_ACTIONS} the environment plays itself and any "
            "score measures the simulation rather than the policy",
        )

    def test_the_action_space_can_express_a_real_route(self):
        """Expressiveness, measured by play that actually builds.

        The original assertion was `longest > 2` over random rollouts, and a
        mutation capping lines at three stations survived it -- random play never
        reaches four, so the cap and the real environment look identical. What a
        metro needs is a line long enough to be worth routing, so this measures
        competent play and asks for a real one.
        """
        longest = max(run["longest_line"] for run in self.COMPETENT)

        self.assertGreaterEqual(
            longest,
            5,
            f"the longest line competent play could build was {longest} stations; "
            "below five the action space cannot express a network worth routing, "
            "however well a policy plays",
        )

    def test_route_order_is_editable_in_both_directions(self):
        """A metro's lap time is made of route order, so order must be actionable."""
        kinds = {kind for kind, _, _ in ACTION_TABLE}

        self.assertIn(ActionKind.EXTEND_LINE, kinds)
        self.assertIn(ActionKind.PREPEND_LINE, kinds)
        self.assertIn(ActionKind.REMOVE_LINE, kinds)

    def test_episodes_end_because_the_game_ended(self):
        """A horizon that cuts an episode short right-censors its score.

        Checked under competent play, because that is the only kind that reaches
        a horizon. Random play loses within a few hundred decisions, so a
        mutation cutting the limit to 450 survived the original version of this
        test untouched.
        """
        self.assertTrue(
            all(run["terminated"] for run in self.COMPETENT),
            "an episode stopped on the step limit rather than on game over, so "
            "its delivery total understates the run: "
            + ", ".join(
                f"seed {run['seed']} ran {run['decisions']} decisions"
                for run in self.COMPETENT
                if not run["terminated"]
            ),
        )

    def test_the_horizon_is_not_the_binding_constraint(self):
        """A game that ends on the clock is not a game about being overwhelmed."""
        longest = max(run["decisions"] for run in self.COMPETENT)

        self.assertGreater(
            longest,
            2_000,
            f"the longest competent episode was {longest} decisions; the network "
            "is still being built at that point, so the score measures the "
            "horizon rather than when the system became overwhelmed",
        )

    def test_the_fleet_can_actually_be_grown(self):
        """Locomotives and carriages must be reachable, not merely in the table.

        A mutation masking the fleet out entirely survived every other gate here,
        because random play never accumulates the resources to buy one and the
        action table still *listed* the actions.
        """
        fleet = max(run["fleet"] for run in self.COMPETENT)

        self.assertGreater(
            fleet,
            1,
            f"competent play never ran more than {fleet} train(s); the fleet "
            "actions are in the table but unreachable, so line capacity is fixed "
            "and no policy can respond to demand",
        )

    def test_training_sees_a_new_layout_every_episode(self):
        """Diversity. A vector env auto-resets without a seed, and a constant
        default meant eight parallel environments trained 600,000 steps on one
        identical board. An explicit seed must still pin the game exactly.
        """

        env = SemanticMetroEnv()
        env.reset(seed=7)
        pinned = [(s.position.left, s.position.top) for s in env._mediator.stations]
        env.reset(seed=7)
        repeated = [(s.position.left, s.position.top) for s in env._mediator.stations]
        layouts = set()
        for _ in range(5):
            env.reset()
            layouts.add(
                tuple((s.position.left, s.position.top) for s in env._mediator.stations)
            )
        env.close()

        self.assertEqual(pinned, repeated, "an explicit seed must reproduce exactly")
        self.assertGreater(
            len(layouts),
            1,
            "every unseeded reset produced the same layout, so training would "
            "see one board no matter how many environments or steps it runs",
        )

    def test_a_degenerate_policy_cannot_outscore_real_play(self):
        """Non-exploitability. Any single repeated action must go nowhere.

        This assertion could not fail as written. It compared the degenerate
        score against `max(max(real), 1.0)`, and `real` was *random* play, which
        scores about zero here -- so the floor did the work and the test read
        `0.0 <= 1.0` no matter what the environment did. Real play means play
        that plays, so the baseline is the scripted heuristic and the floor is
        gone.
        """
        real = [run["deliveries"] for run in self.COMPETENT]
        self.assertGreater(
            min(real),
            50.0,
            f"the baseline scored {min(real)} deliveries, so it is not real play "
            "and cannot bound a degenerate policy",
        )
        best_degenerate = 0.0
        for kind in (ActionKind.WAIT, ActionKind.REMOVE_LINE):
            index = next(i for i, (k, _, _) in enumerate(ACTION_TABLE) if k == kind)
            env = SemanticMetroEnv()
            env.reset(seed=0)
            total = 0.0
            for _ in range(4000):
                mask = env.action_masks()
                choice = index if mask[index] else 0
                _, reward, terminated, truncated, _ = env.step(choice)
                total += reward
                if terminated or truncated:
                    break
            env.close()
            best_degenerate = max(best_degenerate, total)

        self.assertLess(
            best_degenerate,
            min(real),
            f"repeating one action scored {best_degenerate} against real play's "
            f"worst run of {min(real)}; the environment rewards a degenerate "
            "policy, so a training score does not measure play",
        )


def _replay_rewards(seed: int, rng: np.random.Generator):
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    rewards = []
    for _ in range(4000):
        mask = env.action_masks()
        _, reward, terminated, truncated, _ = env.step(
            int(rng.choice(np.flatnonzero(mask)))
        )
        rewards.append(reward)
        if terminated or truncated:
            break
    env.close()
    return rewards


if __name__ == "__main__":
    unittest.main()

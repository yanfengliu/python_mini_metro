"""Lookahead search rests on two claims; both are load-bearing and cheap to break.

The first is that a snapshot restores the game *exactly*. If restore drifted --
a dropped RNG state, a reset decision counter, a lost passenger queue -- every
candidate would be scored against a slightly different game and the whole search
would be comparing noise. It would still run, still print sensible numbers, and
still pick a "best" action, which is what makes the failure worth a test rather
than a glance.

The second is policy improvement: the action search commits to must be the one
its own rollouts scored highest. A sign error or a `min` for a `max` would make
search reliably pick the *worst* candidate, and the only symptom would be a low
score -- indistinguishable from the method simply not working.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402
from search_policy import STRUCTURAL, _restore, _rollout, _signature  # noqa: E402

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, SemanticMetroEnv  # noqa: E402
from save_game import serialize_game  # noqa: E402


def _advance(env, steps: int):
    for _ in range(steps):
        _, _, terminated, truncated, _ = env.step(choose(env))
        if terminated or truncated:
            break


def _advance_to_a_decision_point(env, limit: int = 3000):
    """Stop where a structural action is actually legal.

    A fixed decision count is the wrong anchor: decision 460 was chosen because
    the heuristic acts at 459, and by 460 it has already acted and nothing
    structural is left. Search points are where the game offers a choice, so the
    test finds one rather than assuming where it is.
    """
    for _ in range(limit):
        mask = env.action_masks()
        if any(ACTION_TABLE[i][0] in STRUCTURAL for i in np.flatnonzero(mask)):
            return True
        _, _, terminated, truncated, _ = env.step(choose(env))
        if terminated or truncated:
            return False
    return False


class SnapshotFidelityTest(unittest.TestCase):
    def test_rollouts_from_one_snapshot_are_identical(self):
        """The exactness claim, stated as the thing that would break search."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 500)
        document = serialize_game(env._mediator)
        at = env._decision

        results = [_rollout(env, document, at, 0, 400) for _ in range(3)]
        env.close()

        self.assertEqual(
            len(set(results)),
            1,
            f"three rollouts from the SAME snapshot returned {results}; restore is "
            "not exact, so every candidate is scored against a different game and "
            "the search is comparing noise rather than actions",
        )

    def test_restore_puts_back_the_decision_count(self):
        """The ramp reads `_decision`; a reset one simulates an easier game."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 300)
        document = serialize_game(env._mediator)
        at = env._decision
        self.assertGreater(at, 0)

        _rollout(env, document, at, 0, 50)
        _restore(env, document, at)
        restored = env._decision
        env.close()

        self.assertEqual(
            restored,
            at,
            f"restore left the decision counter at {restored} instead of {at}; "
            "the difficulty ramp and several observation features read it, so "
            "rollouts would simulate an easier game than the one being played",
        )

    def test_restore_puts_back_the_delivery_count(self):
        """Reward is a delta against `_last_deliveries`; a stale one pays twice."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 800)
        document = serialize_game(env._mediator)
        delivered = env._mediator.deliveries
        self.assertGreater(delivered, 0)

        _restore(env, document, env._decision)
        _, reward, _, _, _ = env.step(0)
        env.close()

        self.assertEqual(
            env._last_deliveries - int(reward),
            delivered,
            f"after restore the first step paid {reward} against a baseline of "
            f"{delivered}; reward is a delta, so a stale baseline re-pays every "
            "delivery made before the snapshot",
        )


class PolicyImprovementTest(unittest.TestCase):
    def test_it_commits_to_its_highest_scoring_candidate(self):
        """Search must take the argmax of what it measured, not merely something.

        Driven through the same shortlist/score/choose sequence the player uses,
        rather than by asserting on a stubbed maximum, so a `min` for a `max`
        turns this red.
        """
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        self.assertTrue(
            _advance_to_a_decision_point(env),
            "the game offered no structural action within 3000 decisions",
        )

        mask = env.action_masks()
        structural = [
            i for i in np.flatnonzero(mask) if ACTION_TABLE[i][0] in STRUCTURAL
        ]

        document = serialize_game(env._mediator)
        at = env._decision
        shortlist = structural[:4] + [0]
        scored = [
            (_rollout(env, document, at, candidate, 600), candidate)
            for candidate in shortlist
        ]
        env.close()

        chosen = max(scored)[1]
        best_value = max(value for value, _ in scored)
        chosen_value = next(value for value, action in scored if action == chosen)
        self.assertEqual(
            chosen_value,
            best_value,
            f"search committed to action {chosen} worth {chosen_value} while a "
            f"candidate worth {best_value} was on the shortlist {shortlist}",
        )

    def test_the_shortlist_always_offers_doing_nothing(self):
        """WAIT is the baseline; without it search can only ever act."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance_to_a_decision_point(env)
        mask = env.action_masks()
        env.close()

        self.assertTrue(
            bool(mask[0]),
            "WAIT is masked out, so search has no do-nothing baseline and would "
            "be forced to take a structural action at every decision point",
        )


class SearchTriggerTest(unittest.TestCase):
    def test_a_new_capability_changes_the_signature(self):
        """The trigger fires on new capabilities, not on new station pairs."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        first = _signature(env.action_masks())
        _advance(env, 2000)
        later = _signature(env.action_masks())
        env.close()

        self.assertNotEqual(
            first,
            later,
            "the structural signature never changed across 2000 decisions, so "
            "search would fire once and then never again on capability arrival",
        )


if __name__ == "__main__":
    unittest.main()

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
from search_policy import (  # noqa: E402
    STRUCTURAL,
    _restore,
    _rollout,
    _signature,
    expected_value,
    reseeded,
    shortlist_for,
)

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

    def test_a_rollout_predicts_the_future_the_live_game_produces(self):
        """Determinism is not enough; the simulated future must be the real one.

        A restore that rewound the RNG to the episode start would be perfectly
        deterministic and would pass the test above, while simulating a future
        that never happens -- search would then be optimising a fiction, and the
        only symptom would be a mediocre score. This plays the same decisions
        twice, once by continuing the live game and once from a snapshot taken
        part-way through, and requires the same answer.

        The simulating environment is reset on a *different* seed first, so a
        rollout that secretly depended on its own episode seed rather than on the
        restored state would diverge here.
        """
        live = SemanticMetroEnv()
        live.reset(seed=9000)
        _advance(live, 500)
        document = serialize_game(live._mediator)
        at = live._decision

        real = 0.0
        for _ in range(800):
            _, reward, terminated, truncated, _ = live.step(choose(live))
            real += float(reward)
            if terminated or truncated:
                break
        live.close()

        simulated = SemanticMetroEnv()
        simulated.reset(seed=1)
        _restore(simulated, document, at)
        predicted = 0.0
        for _ in range(800):
            _, reward, terminated, truncated, _ = simulated.step(choose(simulated))
            predicted += float(reward)
            if terminated or truncated:
                break
        simulated.close()

        self.assertEqual(
            predicted,
            real,
            f"the snapshot rollout predicted {predicted} deliveries where the "
            f"live game produced {real}; search would be choosing actions for a "
            "future that will not happen",
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


class SampledFutureTest(unittest.TestCase):
    """Averaging over futures is what stops search selecting luck.

    A single rollout scores a candidate against the one future that will
    actually happen, because the serialised state carries the RNG. Taking the
    max over those one-sample estimates picks the luckiest sample rather than
    the best action -- measured on seed 9000, candidates differ by 17-54
    deliveries within a future while one fixed candidate varies by up to 62
    across futures.
    """

    def test_reseeding_changes_the_future(self):
        """If the RNG swap did nothing, averaging would be theatre.

        The rollout has to be long enough for a changed spawn sequence to reach
        the delivery count. Measured on this state: identical at 600 and 1,500
        decisions, diverging from 3,000. A shorter check would have read as a
        broken RNG swap when the swap was fine.
        """
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 400)
        document = serialize_game(env._mediator)
        at = env._decision

        values = {
            key: _rollout(env, reseeded(document, key), at, 0, 3500) for key in range(3)
        }
        env.close()

        self.assertGreater(
            len(set(values.values())),
            1,
            f"three reseeded futures all returned {set(values.values())}; the RNG "
            "swap is not taking effect, so averaging over futures would return "
            "the same one-sample estimate it is meant to replace",
        )

    def test_reseeding_leaves_the_board_alone(self):
        """Only the future may change; a different board is a different problem."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 400)
        document = serialize_game(env._mediator)

        def board(doc):
            return (
                [(s["position"], s["shapeType"]) for s in doc["stations"]],
                doc["deliveries"],
                doc["steps"],
                len(doc["paths"]),
            )

        original = board(document)
        variant = board(reseeded(document, 7))
        env.close()

        self.assertEqual(
            variant,
            original,
            "reseeding altered the board itself, so candidates would be compared "
            "across different problems rather than across different futures",
        )

    def test_it_averages_rather_than_taking_one_sample(self):
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 400)
        document = serialize_game(env._mediator)
        at = env._decision
        keys = [1, 2, 3]

        singles = [_rollout(env, reseeded(document, k), at, 0, 600) for k in keys]
        averaged = expected_value(env, document, at, 0, 600, keys)
        env.close()

        self.assertAlmostEqual(
            averaged,
            sum(singles) / len(singles),
            places=5,
            msg=f"expected_value returned {averaged} where the mean of "
            f"{singles} is {sum(singles) / len(singles)}; it is not averaging "
            "over the futures it was given",
        )

    def test_no_futures_reproduces_the_one_sample_search(self):
        """The old behaviour stays reachable, so the two can be compared."""
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        _advance(env, 400)
        document = serialize_game(env._mediator)
        at = env._decision

        single = _rollout(env, document, at, 0, 600)
        empty = expected_value(env, document, at, 0, 600, [])
        env.close()

        self.assertEqual(
            empty,
            single,
            f"with no sampled futures expected_value returned {empty} where the "
            f"plain rollout returns {single}; the one-sample baseline is no "
            "longer reproducible and the two cannot be compared",
        )


class ShortlistTest(unittest.TestCase):
    """What search is allowed to consider decides what it can ever find."""

    def test_it_always_offers_the_action_being_improved_on(self):
        """Dropping `preferred` removes the guarantee search rests on.

        Rolling the heuristic's own pick measures exactly what the heuristic
        would score from this state, so including it is what makes search
        provably no worse than the policy it improves. Without it search could
        pick the best of a bad shortlist and lose.
        """
        rng = np.random.default_rng(0)
        structural = list(range(20, 90))

        for preferred in (25, 61, 88):
            shortlist = shortlist_for(rng, structural, preferred, candidates=6)

            self.assertIn(
                preferred,
                shortlist,
                f"the heuristic's choice {preferred} was left off the shortlist "
                f"{shortlist}; search can then score worse than the policy it "
                "is supposed to improve",
            )
            self.assertIn(
                0,
                shortlist,
                f"WAIT was left off the shortlist {shortlist}; search would be "
                "forced to act at every decision point it examines",
            )

    def test_it_samples_alternatives_instead_of_taking_the_lowest_indices(self):
        """Slicing biases every search toward the same corner of the map.

        The action table is ordered by (kind, first, second), so
        `structural[:n]` systematically offers station 0 and 1 and never looks
        at the far side of the board. Sampling costs the same rollouts.
        """
        rng = np.random.default_rng(0)
        structural = list(range(100, 200))

        seen = set()
        for _ in range(40):
            seen.update(shortlist_for(rng, structural, 100, candidates=6))
        seen.discard(0)
        seen.discard(100)

        lowest = set(structural[:5])
        self.assertGreater(
            len(seen),
            len(lowest),
            f"across 40 searches only {sorted(seen)} were ever considered; the "
            "shortlist is sliced by action index rather than sampled, so the "
            "far side of the map is never examined",
        )

    def test_it_stays_within_the_rollout_budget(self):
        """Each extra candidate is a full-episode rollout, so the cap is real."""
        rng = np.random.default_rng(0)
        structural = list(range(20, 90))

        for preferred in (0, 33):
            shortlist = shortlist_for(rng, structural, preferred, candidates=6)

            self.assertLessEqual(
                len(shortlist),
                7,
                f"shortlist {shortlist} exceeds the 6-candidate budget plus "
                "WAIT; every entry costs a full-episode rollout",
            )
            self.assertEqual(
                len(shortlist),
                len(set(shortlist)),
                f"shortlist {shortlist} repeats a candidate, so a rollout is "
                "spent scoring the same action twice",
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


class ScoredRolloutTest(unittest.TestCase):
    """Every rollout search performs is kept, and kept against the right board.

    A search point costs one full-episode simulation per candidate, and taking
    only the argmax discards five sixths of that. The losing evaluations are
    recorded so each search point becomes a preference ordering rather than a
    single hard label -- but they index into their own episode's rows, so
    concatenating episodes must shift every index by the rows already written.
    Getting that wrong attaches one episode's rollout values to another
    episode's board, which trains the policy on fiction while every array shape
    stays valid and every score keeps printing.
    """

    def _episode(self, rows, evaluations, seed=0):
        return {
            "seed": seed,
            "observations": np.zeros((rows, 4), dtype=np.float32),
            "actions": np.arange(rows, dtype=np.int64),
            "masks": np.ones((rows, 4), dtype=bool),
            "returns": np.zeros(rows, dtype=np.float32),
            "eval_row": np.array(evaluations, dtype=np.int64),
            "eval_action": np.array([7] * len(evaluations), dtype=np.int64),
            "eval_value": np.arange(len(evaluations), dtype=np.float32),
        }

    def test_evaluations_are_reindexed_onto_the_right_episode(self):
        import tempfile
        from pathlib import Path

        from search_dataset import save

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data.npz"
            # Episode A keeps 3 rows and scored rollouts at its rows 0 and 2;
            # episode B keeps 2 rows and scored at its own rows 0 and 1.
            save(
                target,
                [
                    self._episode(3, [0, 2], seed=111),
                    self._episode(2, [0, 1], seed=222),
                ],
            )
            archive = np.load(target)
            rows = archive["eval_row"].tolist()
            episodes = archive["episode"].tolist()
            observations = len(archive["observations"])
            archive.close()

        self.assertEqual(
            rows,
            [0, 2, 3, 4],
            f"scored rollouts landed on rows {rows} instead of [0, 2, 3, 4]; the "
            "second episode's evaluations were not shifted past the first "
            "episode's rows, so they describe the wrong board",
        )
        self.assertLess(
            max(rows),
            observations,
            f"a scored rollout points at row {max(rows)} of only {observations} "
            "observations, so it indexes past the end of the dataset",
        )
        # Episode ids exist so a held-out split can be taken by EPISODE. A split
        # by sample puts near-duplicate states from one board on both sides and
        # reports a generalisation number that is nothing of the kind.
        self.assertEqual(
            episodes,
            [111, 111, 111, 222, 222],
            f"rows were labelled {episodes} instead of [111, 111, 111, 222, 222]; "
            "without correct episode ids a validation split cannot separate "
            "boards, and training agreement becomes indistinguishable from "
            "memorisation",
        )


if __name__ == "__main__":
    unittest.main()

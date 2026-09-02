"""What the search PLAYER must do, as opposed to what its helpers can do.

Two claims live here, and both were proved by helper tests that stayed green
while the defect was reintroduced at the call site.

**Resample the simulator's randomness when planning inside it.** A reproducible
simulator is not a deterministic game. The serialised state carries the RNG, so
scoring a candidate once measures it against the one future that will actually
happen -- and taking the max over such one-sample estimates selects the luckiest
future rather than the best action. Measured on seed 9000: candidates differ by
17-54 deliveries within one future while one FIXED candidate varies by up to 62
across futures, so roughly 95% of a published +128.5 margin was luck. Averaging
lives in `expected_value`, and `test_search_policy.py` proves it averages -- but
`play` chooses how many futures to ask for, and `play` was never tested. Its own
`futures` parameter defaulted to 0 while the CLI defaulted to 4, so every
programmatic caller silently got the clairvoyant oracle, which is how a whole
dataset of unlearnable labels was generated.

**Set a lookahead from the measured interval between consequences.** The first
implementation used a fixed 150-decision horizon and scored 144 against the
heuristic's 262 -- worse than the thing it was improving, and worse for a
structural reason rather than a tuning one. Every structural action here costs
resources immediately and repays slowly, and the heuristic's real decisions on
seed 9000 fall at 0-7, 459, 1702, 3411, 3412, 5444 and 7681 out of 8244, so gaps
run 450 to 2200 decisions. A horizon inside the gap cannot reach the next
decision point, never mind a payoff: it sees each action's cost and none of its
benefit, so WAIT wins by construction and search systematically under-acts.
Rolling to episode end turned 144 into 407.88.

So the horizon is not a knob to be tuned by taste. It is measured against the
interval between an action and its consequence, and this file measures that
interval rather than quoting it.
"""

import inspect
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import search_policy  # noqa: E402

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import SemanticMetroEnv  # noqa: E402

WAIT = 0
PINNED_SEED = 9000


class _Enough(Exception):
    """Stop `play` once the call site has been observed often enough."""


class TheSearchPlayerPlansAgainstSampledFutures(unittest.TestCase):
    """Averaging in `expected_value` buys nothing if `play` asks for one future.

    WHAT BOUNDS THIS GATE: the first six decision points of one seed. The spy
    stops `play` there because a full searched episode is thousands of decisions
    and hundreds of rollouts. That is enough to bind the CALL SITE -- the keys
    are built once per search point by one line of code, so six samples of it
    are six samples of the same branch -- and it is not enough to catch a call
    site that behaved differently late in an episode. Nothing here does, and if
    something ever does, this gate will not see it.
    """

    @classmethod
    def setUpClass(cls):
        cls.calls = []
        original = search_policy.expected_value

        def spy(env, document, decision, action, cap, futures):
            cls.calls.append((decision, action, tuple(futures)))
            if len({row[0] for row in cls.calls}) > 6:
                raise _Enough
            return 0.0

        search_policy.expected_value = spy
        try:
            search_policy.play(PINNED_SEED, candidates=6, cap=20_000, futures=4)
        except _Enough:
            pass
        finally:
            search_policy.expected_value = original

    def test_the_player_actually_reached_its_search_path(self):
        """The control. Everything below is vacuous if search never fired.

        Two things have to be true, not one. Search must fire at more than one
        decision point, AND at least one of those points must offer more than
        one candidate -- with a single-candidate shortlist the common-random-
        numbers assertion below compares a set of size one against itself and
        can never fail.
        """
        by_decision = {}
        for decision, action, _ in self.calls:
            by_decision.setdefault(decision, set()).add(action)

        self.assertGreater(
            len(by_decision),
            1,
            f"`play` produced {len(self.calls)} candidate evaluations at "
            f"{len(by_decision)} decision points, so the assertions below never "
            "ran against a real search and would pass with any call site at all",
        )
        self.assertTrue(
            any(len(actions) > 1 for actions in by_decision.values()),
            f"every decision point evaluated exactly one candidate "
            f"({ {d: sorted(a) for d, a in list(by_decision.items())[:3]} }); "
            "with nothing to compare against, common random numbers cannot be "
            "tested and search is not choosing between anything",
        )

    def test_it_never_scores_a_candidate_against_a_single_future(self):
        """One rollout per candidate selects the luckiest future, not the best action.

        The bar is TWO futures, not one. Reseeding to a single future removes
        the clairvoyance -- the planner no longer sees the future that will
        actually happen -- but it leaves the winner's curse untouched: the max
        over one-sample estimates still selects the luckiest sample rather than
        the best action, and here the noise is the size of the signal
        (candidates differ by 17-54 within a future, one fixed candidate varies
        by up to 62 across futures). An average needs something to average.
        """
        thin = [
            (decision, action, len(keys))
            for decision, action, keys in self.calls
            if len(keys) < 2
        ]

        self.assertEqual(
            thin,
            [],
            f"{len(thin)} of {len(self.calls)} candidates were scored against "
            f"fewer than two sampled futures (first few {thin[:4]}); a "
            "one-sample estimate per candidate is exactly the search that "
            "selects lucky futures rather than good actions, whether or not the "
            "one sample happens to be the real one",
        )

    def test_every_candidate_at_a_decision_shares_the_same_futures(self):
        """Common random numbers: the comparison must isolate the ACTION.

        Drawing fresh futures per candidate costs the same rollouts and leaves
        the between-future variation in the comparison, which here is larger
        than the difference between candidates.
        """
        by_decision = {}
        for decision, _, keys in self.calls:
            by_decision.setdefault(decision, set()).add(keys)
        mixed = {
            decision: sorted(seen)
            for decision, seen in by_decision.items()
            if len(seen) > 1
        }

        self.assertEqual(
            mixed,
            {},
            f"candidates at {len(mixed)} decision point(s) were scored against "
            f"different futures ({list(mixed)[:3]}); without common random "
            "numbers the comparison carries the variation between futures, "
            "which on this game is larger than the gap between candidates",
        )

    def test_the_player_forces_its_caller_to_choose_its_measurement_knobs(self):
        """A default here is a silent default, and the silent default was 0.

        `futures` and `cap` are both of them: each decides what the search is
        measuring, and each has a CLI default that a programmatic caller does
        not see. The defect was a function default of 0 sitting under a CLI
        default of 4, so a caller got the clairvoyant oracle while the flag
        advertised otherwise. Nothing about that shape is specific to `futures`.
        """
        signature = inspect.signature(search_policy.play)

        for name in ("futures", "cap"):
            with self.subTest(parameter=name):
                default = signature.parameters[name].default

                self.assertIs(
                    default,
                    inspect.Parameter.empty,
                    f"`play` defaults {name} to {default!r}; a programmatic "
                    "caller then silently inherits a measurement choice it "
                    "never made, which is exactly how the clairvoyant dataset "
                    "was generated while the CLI advertised a different number",
                )

    def test_the_command_line_does_not_default_to_the_oracle(self):
        parser = self._parser()
        default = parser.get_default("futures")

        self.assertGreaterEqual(
            default,
            2,
            f"--futures defaults to {default}; below two there is nothing to "
            "average, so every candidate is a one-sample estimate and the max "
            "over them selects the luckiest sample rather than the best action "
            "(at zero it is also the clairvoyant oracle, since the serialised "
            "state carries the future that will actually happen)",
        )

    @staticmethod
    def _parser():
        import argparse

        holder = {}
        original = argparse.ArgumentParser.parse_args

        def capture(self, *args, **kwargs):
            holder["parser"] = self
            raise _Enough

        argparse.ArgumentParser.parse_args = capture
        try:
            search_policy.main([])
        except _Enough:
            pass
        finally:
            argparse.ArgumentParser.parse_args = original
        return holder["parser"]


class TheRolloutHorizonOutlastsTheDelayBeforeAPayoff(unittest.TestCase):
    """A lookahead shorter than the gap between consequences prefers inaction."""

    @classmethod
    def setUpClass(cls):
        env = SemanticMetroEnv()
        env.reset(seed=PINNED_SEED)
        acted = []
        decisions = 0
        while True:
            action = choose(env)
            if action != WAIT:
                acted.append(decisions)
            _, _, terminated, truncated, _ = env.step(action)
            decisions += 1
            if terminated or truncated:
                break
        env.close()
        cls.acted = acted
        cls.decisions = decisions
        cls.largest_gap = max(
            (later - earlier for earlier, later in zip(acted, acted[1:])),
            default=0,
        )

    def test_the_measurement_itself_is_sound(self):
        """The control: a horizon claim needs decisions spread across an episode."""
        self.assertGreater(
            len(self.acted),
            2,
            f"the scripted policy acted {len(self.acted)} times on seed "
            f"{PINNED_SEED}, so there is no interval between consequences to "
            "measure and the bound below means nothing",
        )
        self.assertGreater(
            self.largest_gap,
            100,
            f"the largest gap between actions was {self.largest_gap} decisions; "
            "this seed no longer exhibits the delayed-payoff structure the "
            "horizon is sized against, so pin one that does",
        )

    def test_the_default_rollout_reaches_the_end_of_the_episode(self):
        """Rolling to episode end is what removes the bias toward WAIT.

        Anything shorter has to be justified against a measurement, because a
        horizon inside the gap sees an action's immediate cost and none of its
        delayed benefit. A fixed 150 scored 144 against the heuristic's 262 and
        spent its searches overriding good actions with WAIT.
        """
        default = TheSearchPlayerPlansAgainstSampledFutures._parser().get_default("cap")

        self.assertGreaterEqual(
            default,
            self.decisions,
            f"the default rollout cap is {default} decisions while an episode "
            f"on seed {PINNED_SEED} runs {self.decisions}; a rollout that stops "
            "early is right-censored, and since every structural action costs "
            "immediately and repays slowly the truncation is a systematic bias "
            "toward doing nothing rather than a loss of accuracy",
        )

    def test_the_default_rollout_outlasts_the_gap_between_consequences(self):
        default = TheSearchPlayerPlansAgainstSampledFutures._parser().get_default("cap")

        self.assertGreater(
            default,
            self.largest_gap,
            f"the default rollout cap is {default} decisions against a measured "
            f"{self.largest_gap}-decision gap between the scripted policy's own "
            f"actions on seed {PINNED_SEED}; a rollout that cannot reach the "
            "next decision point cannot see a payoff, so WAIT wins by "
            "construction and search reliably recommends inaction",
        )


if __name__ == "__main__":
    unittest.main()

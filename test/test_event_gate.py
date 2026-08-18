"""The event gate must cost the scripted heuristic exactly nothing.

The semantic environment queries a policy every 6 ticks, so an episode is about
7,600 decisions -- and the scripted heuristic acts on about 15 of them. Over
99.8% of a training rollout is therefore spent learning to emit WAIT, and any
credit for a delivery has to travel back across thousands of no-ops.

The gate removes that. After WAIT it fast-forwards the simulation until the
action mask changes, because the heuristic's choice is a pure function of
(station positions, served set, mask) and none of those can move while the mask
stands still: a new station index makes fresh CONNECT/EXTEND/PREPEND entries
legal, and only an agent action changes line membership. After a non-WAIT action
it must re-query immediately -- acting changes what to do next while leaving the
option set alone, which is the first version's bug. Gating on mask changes alone
scored 0 deliveries against 525, because the heuristic's own follow-up actions
were already legal and so never moved the mask.

These tests pin the property the whole design rests on: identical deliveries,
identical decision counts, identical action sequences. If a future change to the
mask, the action table or the heuristic breaks the equivalence, the gate stops
being free and every measurement taken through it is suspect.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.event_gate import EventGatedSemanticEnv  # noqa: E402
from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402

# Long enough to reach real mid-game structure, short enough for the suite.
GATE_SEEDS = (0, 3, 7)
BUDGET = 2200


def _play_plain(seed: int, budget: int) -> dict:
    """The heuristic queried on every decision, as the environment ships.

    The budget is applied by the environment's own `max_decisions`, not by an
    external counter: a gated WAIT consumes up to `wait_backstop` decisions at
    once, so an outside cap stops the two arms at different points and the
    comparison measures the cap rather than the gate.
    """
    env = SemanticMetroEnv(max_decisions=budget)
    env.reset(seed=seed)
    total, decisions, actions = 0.0, 0, []
    try:
        while True:
            action = choose(env)
            if action != 0:
                # WHEN as well as WHAT. The defect the n=200 run found delayed
                # the correct action by exactly one backstop, so a comparison
                # of actions alone passes with the bug live.
                actions.append((decisions, int(action)))
            _, reward, terminated, truncated, _ = env.step(action)
            total += float(reward)
            decisions += 1
            if terminated or truncated:
                break
    finally:
        env.close()
    return {"deliveries": total, "decisions": decisions, "actions": actions}


def _play_gated(seed: int, budget: int, **kwargs) -> dict:
    """The heuristic queried only at the gate's decision points."""
    kwargs.setdefault("max_decisions", budget)
    env = EventGatedSemanticEnv(**kwargs)
    env.reset(seed=seed)
    total, queries, actions = 0.0, 0, []
    try:
        while True:
            action = choose(env.inner)
            if action != 0:
                actions.append((env.decisions, int(action)))
            _, reward, terminated, truncated, _ = env.step(action)
            total += float(reward)
            queries += 1
            if terminated or truncated:
                break
    finally:
        env.close()
    return {
        "deliveries": total,
        "decisions": env.decisions,
        "actions": actions,
        "queries": queries,
    }


class EventGateIsFreeForTheHeuristic(unittest.TestCase):
    def test_deliveries_and_decisions_are_identical(self):
        for seed in GATE_SEEDS:
            with self.subTest(seed=seed):
                plain = _play_plain(seed, BUDGET)
                gated = _play_gated(seed, BUDGET)
                self.assertEqual(gated["deliveries"], plain["deliveries"])
                self.assertEqual(gated["decisions"], plain["decisions"])

    def test_the_action_sequence_is_identical(self):
        """Not merely the same score -- the same moves, in the same order.

        Equal totals could coincide; equal action sequences cannot. This is the
        assertion that fails if the gate ever lets the heuristic act late.
        """
        for seed in GATE_SEEDS:
            with self.subTest(seed=seed):
                plain = _play_plain(seed, BUDGET)
                gated = _play_gated(seed, BUDGET)
                self.assertEqual(gated["actions"], plain["actions"])
                self.assertGreater(len(plain["actions"]), 3)

    def test_the_gate_actually_removes_decisions(self):
        """A gate that never fast-forwards would pass every test above."""
        for seed in GATE_SEEDS:
            with self.subTest(seed=seed):
                gated = _play_gated(seed, BUDGET)
                self.assertLess(gated["queries"] * 10, gated["decisions"])


class ASpawnInsideTheWaitStepMustNotBeSleptThrough(unittest.TestCase):
    """The regression the n=200 comparison found and the n=8 one did not.

    `fast_forward` used to read its baseline mask *after* the WAIT step had
    already advanced six ticks. A station spawning inside those ticks therefore
    became the baseline, and the gate then slept a whole backstop through the
    change it existed to wake for. On 200 seeds it cost 5 of them a delayed
    action -- always the correct action exactly `wait_backstop` decisions late,
    seed 90048 at decision 411 arriving at 611 -- while the mean moved 249.29 to
    249.50. That is a defect no aggregate would ever have shown.

    Seed 90048 and its 700-decision window are pinned because a nearby seed
    passes with the bug live: the spawn has to land in the one step that opens a
    fast-forward, which is why it is rare.
    """

    SEED = 90048
    WINDOW = 700

    def test_the_delayed_action_arrives_on_time(self):
        plain = _play_plain(self.SEED, self.WINDOW)
        gated = _play_gated(self.SEED, self.WINDOW)
        self.assertEqual(gated["actions"], plain["actions"])

    def test_reading_the_baseline_after_the_step_reproduces_the_delay(self):
        """Mutation-prove the fix: the old baseline still fails this seed."""
        env = EventGatedSemanticEnv(wait_backstop=200, max_decisions=self.WINDOW)
        env.reset(seed=self.SEED)
        actions = []
        try:
            while True:
                action = choose(env.inner)
                if action != 0:
                    actions.append((env.inner._decision, int(action)))
                _, _, terminated, truncated, _ = env.inner.step(action)
                if terminated or truncated:
                    break
                if action == 0:
                    # The defect: baseline read after the step, not before it.
                    _, _, terminated, truncated, _ = env.fast_forward()
                    if terminated or truncated:
                        break
        finally:
            env.close()
        self.assertNotEqual(actions, _play_plain(self.SEED, self.WINDOW)["actions"])


class GatingOnMaskChangeAloneIsWrong(unittest.TestCase):
    """Pin the bug the corrected design exists to avoid.

    The first gate fast-forwarded after *every* action rather than only after
    WAIT. Because the heuristic's follow-up moves are already legal, the mask
    did not move, so it sat idle for the whole backstop and the run died at the
    40-second overcrowding deadline with zero deliveries. Without this test a
    future simplification back to "fast-forward whenever the mask is stable"
    looks harmless and silently destroys the equivalence.
    """

    def test_fast_forwarding_after_a_real_action_loses_deliveries(self):
        # `pressure_step=0` puts the gate back in the mask-only regime this
        # defect belongs to. With the shipped pressure wake the same defect
        # scores 68 against 67 -- queue depth moves within a few decisions, so
        # the gate can no longer idle through the overcrowding deadline and the
        # bug is largely masked. That is a real robustness gain and exactly why
        # this test names the regime instead of relying on the default: a future
        # change that drops the pressure wake would re-expose the defect, and
        # this must still be the test that catches it.
        env = EventGatedSemanticEnv(
            wait_backstop=200, pressure_step=0, max_decisions=BUDGET
        )
        env.reset(seed=0)
        total = 0.0
        try:
            while True:
                action = choose(env.inner)
                _, reward, terminated, truncated, _ = env.step(action)
                total += float(reward)
                # The defect: fast-forward regardless of what was just done.
                _, extra, terminated, truncated, _ = env.fast_forward()
                total += float(extra)
                if terminated or truncated:
                    break
        finally:
            env.close()
        plain = _play_plain(0, BUDGET)
        self.assertLess(total, plain["deliveries"])


class GateMechanics(unittest.TestCase):
    def test_wait_stops_at_the_backstop_when_the_mask_never_moves(self):
        env = EventGatedSemanticEnv(wait_backstop=7)
        env.reset(seed=0)
        try:
            # Reach a state where the heuristic is idle, so WAIT is genuine.
            for _ in range(40):
                action = choose(env.inner)
                if action == 0:
                    break
                env.step(action)
            before = env.decisions
            env.step(0)
            self.assertLessEqual(env.decisions - before, 8)
            self.assertGreaterEqual(env.decisions - before, 1)
        finally:
            env.close()

    def test_a_non_wait_action_advances_exactly_one_decision(self):
        env = EventGatedSemanticEnv()
        env.reset(seed=0)
        try:
            action = choose(env.inner)
            self.assertNotEqual(action, 0)
            before = env.decisions
            env.step(action)
            self.assertEqual(env.decisions - before, 1)
        finally:
            env.close()

    def test_reward_accumulates_over_the_skipped_decisions(self):
        """A fast-forward that dropped its rewards would silently teach WAIT
        is worthless, which is the opposite of what the game says."""
        env = EventGatedSemanticEnv()
        env.reset(seed=0)
        try:
            banked = 0.0
            for _ in range(60):
                action = choose(env.inner)
                _, reward, terminated, truncated, _ = env.step(action)
                banked += float(reward)
                if terminated or truncated:
                    break
            self.assertEqual(banked, float(env.inner._mediator.deliveries))
            self.assertGreater(banked, 0.0)
        finally:
            env.close()

    def test_spaces_and_masks_pass_through(self):
        env = EventGatedSemanticEnv()
        try:
            self.assertEqual(env.action_space.n, len(ACTION_TABLE))
            obs, _ = env.reset(seed=0)
            self.assertEqual(obs.shape, env.observation_space.shape)
            mask = env.action_masks()
            self.assertEqual(mask.shape, (len(ACTION_TABLE),))
            self.assertTrue(mask[0])
        finally:
            env.close()

    def test_terminating_inside_a_fast_forward_is_reported(self):
        """The run must end when the game does, not when the backstop expires."""
        env = EventGatedSemanticEnv()
        env.reset(seed=0)
        try:
            terminated = False
            for _ in range(4000):
                _, _, terminated, truncated, _ = env.step(choose(env.inner))
                if terminated or truncated:
                    break
            self.assertTrue(terminated)
            self.assertTrue(env.inner._mediator.is_game_over)
        finally:
            env.close()

    def test_the_wait_that_ends_the_game_still_pays_its_deliveries(self):
        env = EventGatedSemanticEnv()
        env.reset(seed=1)
        try:
            total = 0.0
            for _ in range(4000):
                _, reward, terminated, truncated, _ = env.step(choose(env.inner))
                total += float(reward)
                if terminated or truncated:
                    break
            self.assertEqual(total, float(env.inner._mediator.deliveries))
        finally:
            env.close()


class DeferAction(unittest.TestCase):
    """`DEFER` must be the heuristic exactly, or the anchor is a fiction.

    The point of the residual design is that a policy which always defers scores
    what the heuristic scores, so training starts at the bar rather than 80
    deliveries below it. If DEFER drifts from `choose` by even one action the
    starting point is unknown and every "beats the heuristic" claim built on it
    is unfounded.
    """

    def test_defer_reproduces_the_heuristic_action_by_action(self):
        env = EventGatedSemanticEnv(defer=True, max_decisions=BUDGET)
        env.reset(seed=2)
        plain = _play_plain(2, BUDGET)
        chosen = []
        total = 0.0
        try:
            while True:
                _, reward, terminated, truncated, info = env.step(env.DEFER)
                total += float(reward)
                if info["proposal"] != 0:
                    chosen.append((env.decisions - 1, int(info["proposal"])))
                if terminated or truncated:
                    break
        finally:
            env.close()
        self.assertEqual(chosen, plain["actions"])
        self.assertEqual(total, plain["deliveries"])
        self.assertEqual(env.decisions, plain["decisions"])

    def test_defer_is_the_last_index_and_is_always_legal(self):
        env = EventGatedSemanticEnv(defer=True)
        env.reset(seed=0)
        try:
            self.assertEqual(env.action_space.n, len(ACTION_TABLE) + 1)
            self.assertEqual(env.DEFER, len(ACTION_TABLE))
            for _ in range(30):
                mask = env.action_masks()
                self.assertEqual(mask.shape, (len(ACTION_TABLE) + 1,))
                self.assertTrue(mask[env.DEFER])
                env.step(env.DEFER)
        finally:
            env.close()

    def test_defer_is_absent_unless_asked_for(self):
        env = EventGatedSemanticEnv()
        try:
            self.assertIsNone(env.DEFER)
            self.assertEqual(env.action_space.n, len(ACTION_TABLE))
        finally:
            env.close()

    def test_an_explicit_action_still_works_alongside_defer(self):
        """Deviating is the whole point; the table must stay usable."""
        env = EventGatedSemanticEnv(defer=True)
        env.reset(seed=0)
        try:
            mask = env.action_masks()
            legal = [
                index
                for index in np.flatnonzero(mask[: len(ACTION_TABLE)])
                if ACTION_TABLE[index][0] is ActionKind.CONNECT
            ]
            self.assertTrue(legal)
            _, _, _, _, info = env.step(int(legal[0]))
            self.assertTrue(info["applied"])
            self.assertEqual(len(env.inner._mediator.paths), 1)
        finally:
            env.close()

    def test_the_proposal_block_names_the_action_defer_would_take(self):
        env = EventGatedSemanticEnv(defer=True, proposal_features=True)
        obs, _ = env.reset(seed=0)
        try:
            self.assertEqual(
                obs.shape[0],
                SemanticMetroEnv._observation_size() + env.PROPOSAL_FEATURES,
            )
            for _ in range(25):
                proposal = choose(env.inner)
                block = env.observe()[-env.PROPOSAL_FEATURES :]
                kind, first, second = ACTION_TABLE[proposal]
                self.assertEqual(int(np.argmax(block[: len(ActionKind)])), int(kind))
                self.assertAlmostEqual(
                    float(block[len(ActionKind)]), first / 20.0, places=5
                )
                self.assertAlmostEqual(
                    float(block[len(ActionKind) + 1]), second / 20.0, places=5
                )
                env.step(env.DEFER)
        finally:
            env.close()

    def test_the_proposal_block_is_absent_unless_asked_for(self):
        env = EventGatedSemanticEnv(defer=True)
        obs, _ = env.reset(seed=0)
        try:
            self.assertEqual(obs.shape[0], SemanticMetroEnv._observation_size())
        finally:
            env.close()


class DeviationScope(unittest.TestCase):
    """`kind` narrows a deviation to the arguments the heuristic picked blind.

    The heuristic crews `legal[kind][0][0]` -- whichever line happens to sit
    lowest in the action table -- and grafts onto the nearest line end without
    regard to what that line already carries. Those are the arbitrary choices
    worth attacking, and offering only them leaves a handful of options per
    decision instead of about thirty, so a fixed number of episodes buys far
    more evidence per option.
    """

    def test_kind_offers_only_the_proposal_s_kind_plus_wait_and_defer(self):
        env = EventGatedSemanticEnv(defer=True, deviation_scope="kind")
        env.reset(seed=0)
        try:
            seen_narrow = False
            for _ in range(40):
                proposal = choose(env.inner)
                wanted = ACTION_TABLE[proposal][0]
                mask = env.action_masks()
                self.assertTrue(mask[env.DEFER])
                self.assertTrue(mask[0])
                offered = {
                    ACTION_TABLE[index][0]
                    for index in np.flatnonzero(mask[: len(ACTION_TABLE)])
                }
                self.assertLessEqual(offered, {ActionKind.WAIT, wanted})
                full = env.inner.action_masks()
                if int(full.sum()) > int(mask[: len(ACTION_TABLE)].sum()):
                    seen_narrow = True
                env.step(env.DEFER)
            self.assertTrue(seen_narrow, "kind never actually narrowed anything")
        finally:
            env.close()

    def test_the_proposal_itself_is_still_offered_under_kind(self):
        """Narrowing must never mask out the action DEFER would take."""
        env = EventGatedSemanticEnv(defer=True, deviation_scope="kind")
        env.reset(seed=4)
        try:
            for _ in range(40):
                proposal = choose(env.inner)
                self.assertTrue(env.action_masks()[proposal])
                env.step(env.DEFER)
        finally:
            env.close()

    def test_defer_still_equals_the_heuristic_under_kind(self):
        env = EventGatedSemanticEnv(
            defer=True, deviation_scope="kind", max_decisions=BUDGET
        )
        env.reset(seed=3)
        total = 0.0
        try:
            while True:
                _, reward, terminated, truncated, _ = env.step(env.DEFER)
                total += float(reward)
                if terminated or truncated:
                    break
        finally:
            env.close()
        self.assertEqual(total, _play_plain(3, BUDGET)["deliveries"])

    def test_all_is_the_default_and_offers_everything_legal(self):
        env = EventGatedSemanticEnv(defer=True)
        env.reset(seed=0)
        try:
            mask = env.action_masks()
            self.assertTrue(
                np.array_equal(mask[: len(ACTION_TABLE)], env.inner.action_masks())
            )
        finally:
            env.close()

    def test_an_unknown_scope_names_what_would_satisfy_it(self):
        with self.assertRaises(ValueError) as caught:
            EventGatedSemanticEnv(defer=True, deviation_scope="argmin")
        self.assertIn("'all'", str(caught.exception))
        self.assertIn("argmin", str(caught.exception))

    def test_a_scope_without_defer_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            EventGatedSemanticEnv(deviation_scope="kind")
        self.assertIn("defer=True", str(caught.exception))


class NoSkippedDecisionWasOneTheHeuristicWantedToAct(unittest.TestCase):
    """The direct proof, rather than the end-state coincidence.

    Comparing action sequences shows the gate did not change the outcome. It
    does not show WHY, and it only covers the prefix the test budget reaches --
    the committed sequence tests span 20-37% of their episodes, all early game
    where the mask carries the most redundant channels.

    This asks the load-bearing question at every decision the gate skips: would
    the ungated heuristic have acted here? A single yes is a divergence the gate
    swallowed, whether or not the score happens to survive it. An independent
    review lane ran this shape over ~310,000 skipped decisions on 60 seeds and
    with `wait_backstop` swept from 1 to 100,000, and found none; this pins a
    full episode of it in CI.
    """

    def test_the_heuristic_would_have_waited_at_every_skipped_decision(self):
        for seed in (5, 11):
            with self.subTest(seed=seed):
                env = EventGatedSemanticEnv()
                env.reset(seed=seed)
                skipped = 0
                try:
                    while True:
                        action = choose(env.inner)
                        _, _, terminated, truncated, _ = env.inner.step(action)
                        env.decisions += 1
                        if terminated or truncated:
                            break
                        if action != 0:
                            continue
                        held = env.inner.action_masks()
                        for _ in range(env.wait_backstop):
                            if not np.array_equal(env.inner.action_masks(), held):
                                break
                            self.assertEqual(
                                choose(env.inner),
                                0,
                                f"seed {seed}: the gate skipped decision "
                                f"{env.inner._decision}, where the heuristic wanted "
                                f"to act",
                            )
                            _, _, terminated, truncated, _ = env.inner.step(0)
                            env.decisions += 1
                            skipped += 1
                            if terminated or truncated:
                                break
                        if terminated or truncated:
                            break
                finally:
                    env.close()
                self.assertGreater(skipped, 2000)


if __name__ == "__main__":
    unittest.main()

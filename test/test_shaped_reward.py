"""Shaped reward exists so the game can be learned without a teacher.

Under the deliveries reward the first passenger is unreachable by exploration:
drawing a line needs pointer-down on a ~10 px station, motion, then pointer-up on
another, and across 12 random episodes and 4170 decisions none occurred. Every
reward in a batch is then zero, so the advantage is zero and the policy gradient
is the zero vector -- there is nothing to descend.

Shaping pays partial credit for the sub-events of that conjunction, so the pieces
become individually learnable. It changes no action, no observation and no game
rule; evaluation still scores true deliveries.

The credit tracks a high-water mark rather than the live count, because a reward
paid for the *state* of having a line can be farmed by erasing and redrawing it.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.demonstrator import drag_route_actions  # noqa: E402
from rl.player_env import PlayerPixelEnv  # noqa: E402
from rl.privileged_oracle import capture_privileged_snapshot  # noqa: E402
from rl.shaping import ConnectionShapedReward  # noqa: E402


def _env(shaped):
    env = PlayerPixelEnv()
    if shaped:
        env = ConnectionShapedReward(env)
    env.reset(seed=0)
    return env


def _draw_opening_route(env):
    """Run the expert's opening drag, returning the reward it accrued."""
    # The privileged helpers read the game directly, so they need the raw env.
    inner = env.unwrapped
    stations = len(capture_privileged_snapshot(inner).station_positions)
    total = 0.0
    for action in drag_route_actions(inner, tuple(range(stations))):
        _, reward, terminated, truncated, _ = env.step(
            np.asarray(action, dtype=np.int64)
        )
        total += float(reward)
        if terminated or truncated:
            break
    return total


class TheSignalMustBeReachableByThePolicyThatNeedsIt(unittest.TestCase):
    """Reachable by EXPLORATION, which is not the same as reachable at all.

    Every other test in this file drives the expert's opening drag, so it asks
    whether shaping pays a policy that can already do the thing. The policy that
    needs shaping cannot. The first version of this wrapper paid credit only for
    stations joined onto a usable route, and across 24 random episodes and 8,721
    decisions it paid out ZERO times -- it rewarded precisely the event an
    exploring policy never reaches, and so reproduced the exact zero gradient it
    was built to remove. Reintroduced, that defect passes every expert-driven
    test in this file, because the expert reaches the milestone on its first
    drag.

    So the population matters: the credit has to arrive under the play that is
    actually generating the batch. The two assertions below say that in the two
    ways that can each be true without the other -- credit arrives in every
    episode, and credit arrives BEFORE any line exists.
    """

    EPISODES = 12
    STEPS = 600

    @classmethod
    def setUpClass(cls):
        cls.runs = {seed: cls._explore(seed) for seed in range(cls.EPISODES)}

    @classmethod
    def _explore(cls, seed: int) -> dict:
        from rl.shaping import count_connected_stations

        env = _env(shaped=True)
        try:
            env.reset(seed=seed)
            env.action_space.seed(seed)
            mediator = env.unwrapped._require_mediator()
            payouts = 0
            payouts_before_any_line = 0
            for _ in range(cls.STEPS):
                _, _, terminated, truncated, info = env.step(env.action_space.sample())
                if info.get("shaping_credit"):
                    payouts += 1
                    if count_connected_stations(mediator) == 0:
                        payouts_before_any_line += 1
                if terminated or truncated:
                    break
        finally:
            env.close()
        return {"payouts": payouts, "before_any_line": payouts_before_any_line}

    def test_random_play_earns_shaping_credit_in_every_episode(self):
        runs = self.runs
        silent = sorted(seed for seed, run in runs.items() if not run["payouts"])

        self.assertEqual(
            silent,
            [],
            f"shaping paid out nothing across {self.STEPS} random decisions on "
            f"seed(s) {silent} of {self.EPISODES}; a signal an exploring policy "
            "never reaches leaves every reward in the batch at zero, so the "
            "advantage is zero and the policy gradient is the zero vector -- "
            "which is the failure shaping exists to remove",
        )

    def test_credit_arrives_before_the_milestone_it_is_scaffolding_for(self):
        """Paying only at the finish line is the defect, restated as a test."""
        blind = sorted(
            seed for seed, run in self.runs.items() if not run["before_any_line"]
        )

        self.assertEqual(
            blind,
            [],
            f"on seed(s) {blind} every payout arrived only after a line already "
            "existed, so the ladder has no rung below the milestone; an "
            "exploring policy has to cross the whole conjunction -- pointer-down "
            "on a ~10 px station, motion, pointer-up on a different one -- "
            "before it is paid anything at all",
        )


class ShapedRewardTest(unittest.TestCase):
    def test_deliveries_mode_pays_nothing_for_drawing_a_line(self):
        """The baseline this exists to fix: the gesture itself earns zero."""
        env = _env(shaped=False)
        self.addCleanup(env.close)

        self.assertEqual(_draw_opening_route(env), 0.0)

    def test_shaped_mode_pays_for_drawing_a_line(self):
        env = _env(shaped=True)
        self.addCleanup(env.close)

        self.assertGreater(
            _draw_opening_route(env),
            0.0,
            "connecting stations must earn credit under shaping, or exploration "
            "is left with the same zero gradient it had before",
        )

    def test_total_shaping_is_bounded_so_it_cannot_be_farmed(self):
        """A spam-clicking policy must not outscore one that actually plays.

        Proximity credit is dense by design -- that is what makes it reachable --
        so without a ceiling 0.02 per pointer-down over a long episode would beat
        the ~19-20 a real game earns, and standing next to a station clicking
        forever would be the optimal policy.
        """
        import numpy as np

        from rl.privileged_oracle import capture_privileged_snapshot
        from rl.protocol import ActionKind, canonical_to_action_coordinate

        env = _env(shaped=True)
        self.addCleanup(env.close)
        inner = env.unwrapped
        station = capture_privileged_snapshot(inner).station_positions[0]
        x, y = canonical_to_action_coordinate(*station, inner.task_spec.render_profile)
        spam = np.array([int(ActionKind.DOWN.value), x, y], dtype=np.int64)

        total = 0.0
        for _ in range(4000):
            _, reward, terminated, truncated, _ = env.step(spam)
            total += float(reward)
            if terminated or truncated:
                break

        self.assertLess(
            total,
            5.0,
            f"clicking one station repeatedly earned {total}; the shaping budget "
            "must keep a degenerate policy far below the ~19-20 real play earns",
        )

    def test_a_delivery_still_dominates_the_shaping_credit(self):
        """Shaping must nudge toward the objective, not replace it."""
        env = _env(shaped=True)
        self.addCleanup(env.close)

        drawing = _draw_opening_route(env)

        self.assertLess(
            drawing,
            1.0,
            f"drawing one route paid {drawing}, which is at least a full "
            "delivery; shaping would then outweigh the real objective",
        )

    def test_shaping_leaves_the_task_identity_untouched(self):
        """Shaping is scaffolding, not a different task: fingerprints must not move."""
        from rl.protocol import protocol_fingerprint, task_fingerprint

        before = (protocol_fingerprint(), task_fingerprint())
        env = _env(shaped=True)
        self.addCleanup(env.close)

        self.assertEqual((protocol_fingerprint(), task_fingerprint()), before)


if __name__ == "__main__":
    unittest.main()


class ShapingStaysOutOfEvaluationTest(unittest.TestCase):
    """Shaping is scaffolding; a shaped evaluation would silently inflate scores."""

    def test_thunks_apply_shaping_only_when_asked(self):
        from rl.protocol import TaskSpec
        from rl.training import make_env_thunks

        plain = make_env_thunks(TaskSpec(), n_envs=1, seed=0)[0]
        shaped = make_env_thunks(TaskSpec(), n_envs=1, seed=0, shaped_reward=True)[0]

        self.assertFalse(plain.shaped_reward)
        self.assertTrue(shaped.shaped_reward)

        built_plain = plain()
        self.addCleanup(built_plain.close)
        built_shaped = shaped()
        self.addCleanup(built_shaped.close)

        self.assertNotIsInstance(built_plain, ConnectionShapedReward)
        self.assertIsInstance(built_shaped, ConnectionShapedReward)

    def test_the_training_script_never_shapes_the_evaluation_environment(self):
        """Read the call sites directly: a shaped eval env would inflate every score."""
        import re
        from pathlib import Path

        source = Path(__file__).resolve().parents[1] / "scripts" / "train_rl.py"
        text = source.read_text(encoding="utf-8")
        calls = re.findall(
            r"(\w+_env) = build_vector_env\((.*?)\n        \)", text, re.S
        )
        shaped = {name for name, body in calls if "shaped_reward" in body}

        self.assertIn("train_env", shaped)
        self.assertNotIn(
            "eval_env",
            shaped,
            "the evaluation environment must never receive shaping, or reported "
            "deliveries include exploration credit",
        )

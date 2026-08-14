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

    def test_shaping_cannot_be_farmed_by_redrawing_the_same_line(self):
        """A second identical route must not pay again."""
        env = _env(shaped=True)
        self.addCleanup(env.close)

        first = _draw_opening_route(env)
        second = _draw_opening_route(env)

        self.assertGreater(first, 0.0)
        self.assertLessEqual(
            second,
            0.0,
            f"redrawing paid {second} a second time; shaping must track a "
            "high-water mark so it cannot be farmed by erase-and-redraw",
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

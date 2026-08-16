"""The evaluation callback must fire, whatever n_envs happens to be.

`num_timesteps` advances by `n_envs` on every callback, so it only ever takes
multiples of `n_envs`. A trigger written as `num_timesteps % every == 0` therefore
fires at multiples of `lcm(n_envs, every)` rather than at `every` -- with 6
environments and an interval of 1,000 it fires every 3,000 steps, a third as
often as asked. The worst cases are much worse: 7 environments and an interval of
1,000,000 fire once per 7,000,000 steps, so a 10M-step run evaluates once
instead of ten times.

The consequence is silent. Evaluation is also what saves the best model, so a
long run can finish having checkpointed almost nothing, and the only symptom is a
sparse log -- which reads like slow training rather than a broken trigger.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from train_semantic import KeepBest  # noqa: E402


class _Recorder:
    """Stands in for the SB3 callback host, counting like SB3 counts."""

    def __init__(self, keeper, n_envs):
        self.callback = keeper.build()
        self.n_envs = n_envs
        self.num_timesteps = 0
        self.fired = []
        # The callback reaches for the model only when it actually fires.
        self.callback.model = self
        self.callback.num_timesteps = 0

    def save(self, path):
        pass

    def run(self, total):
        while self.num_timesteps < total:
            self.num_timesteps += self.n_envs
            self.callback.num_timesteps = self.num_timesteps
            self.callback._on_step()


class EvalTriggerTest(unittest.TestCase):
    def _keeper(self, every):
        keeper = KeepBest("output/_unused", every, episodes=1, seed=0)
        return keeper

    def _run(self, n_envs, every, total, monkeypatched):
        keeper = self._keeper(every)
        fired = []

        import train_semantic

        original = train_semantic.evaluate
        train_semantic.evaluate = lambda *a, **k: fired.append(1) or [0.0]
        try:
            _Recorder(keeper, n_envs).run(total)
        finally:
            train_semantic.evaluate = original
        return fired

    def test_it_fires_when_n_envs_does_not_divide_the_interval(self):
        """6 environments and 1,000 align only every 3,000 -- a third as often."""
        fired = self._run(n_envs=6, every=1_000, total=10_000, monkeypatched=True)

        self.assertGreaterEqual(
            len(fired),
            9,
            f"the evaluation fired {len(fired)} times across 10,000 steps at an "
            "interval of 1,000; with 6 environments a modulo trigger only fires "
            "at multiples of lcm(6, 1000) = 3,000, so evaluations and the "
            "best-model checkpoints that depend on them come far more rarely "
            "than requested",
        )

    def test_it_fires_when_n_envs_does_divide_the_interval(self):
        """The case that happened to work must keep working."""
        fired = self._run(n_envs=16, every=1_600, total=16_000, monkeypatched=True)

        self.assertGreaterEqual(len(fired), 9, "regular intervals stopped firing")

    def test_it_does_not_fire_more_often_than_asked(self):
        """A trigger that fires every step would evaluate the run to a halt."""
        fired = self._run(n_envs=6, every=1_000, total=10_000, monkeypatched=True)

        self.assertLessEqual(
            len(fired),
            11,
            f"the evaluation fired {len(fired)} times for 10 expected intervals; "
            "over-firing spends the run evaluating rather than training",
        )


if __name__ == "__main__":
    unittest.main()

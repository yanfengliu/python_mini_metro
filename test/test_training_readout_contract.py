"""What a training run must write down, and when.

Two claims, both learned from runs whose result no longer exists.

**Save the best result while it exists; a training run is not monotonic and the
final weights are not the peak.** A 1.2M-step run here peaked at 97.5 deliveries
near 500k and fell to 35.5 by 856k. The trainer saved only at the end, so the
best policy it ever produced was never written to disk and survives only as a
number in a log file. The collapse was recoverable; the loss was not. "The run
finished" and "the run's best result is available" are different claims, and
only the second one is worth anything afterwards. The collapse also had a
recognisable signature -- `entropy_loss`, `approx_kl` and `clip_fraction` all
rising together while the score halved -- which is visible only if the
evaluation history is kept as the run goes rather than reconstructed later.

**An initialisation is a claim: save the starting policy and evaluate it as
readout zero.** "A policy that always defers IS the heuristic, so training
starts at the bar rather than 80 deliveries below it" appeared in two docstrings
and a commit message, and nothing measured it. It was false:
`action_net.weight.mul_(0.01)` sat on top of the library's own orthogonal init
with gain 0.01, leaving the weights at std 5.2e-6, so the opening policy was
"defer with probability p, otherwise UNIFORM over the legal actions" -- 211.85
against the anchor's 248.78. Both arms then spent their budget un-learning the
noise their own initialisation had injected while printing a steadily closing
gap (-36.9 -> -15.9 -> -3.5) whose end state is simply the anchor. Read as
"training is working" that is exactly backwards, and the run's `-best` selector
became a monotone selector for doing nothing. Where a run is supposed to start
is a measurement, not a property of the code that was written.
"""

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# The measured collapse, replayed as a score sequence: a run climbs, peaks, and
# then loses two thirds of what it had while still training.
COLLAPSE = (10.0, 40.0, 97.5, 60.0, 35.5)
PEAK = max(COLLAPSE)


class _Trainer:
    """Stands in for the SB3 model and callback host, counting as SB3 counts."""

    def __init__(self, keeper, n_envs):
        self.callback = keeper.build()
        self.n_envs = n_envs
        self.num_timesteps = 0
        self.saved = []
        self.callback.model = self
        self.callback.num_timesteps = 0

    def save(self, path):
        self.saved.append((self.num_timesteps, str(path)))

    def run(self, total):
        while self.num_timesteps < total:
            self.num_timesteps += self.n_envs
            self.callback.num_timesteps = self.num_timesteps
            self.callback._on_step()

    def written(self, suffix):
        return [step for step, path in self.saved if path.endswith(suffix)]


class TheBestPolicyMustSurviveTheRunThatProducedIt(unittest.TestCase):
    EVERY = 1_000
    N_ENVS = 10

    def setUp(self):
        import train_semantic

        self.train_semantic = train_semantic
        self.keeper = train_semantic.KeepBest(
            "output/_test_keep_best", self.EVERY, episodes=1, seed=0
        )
        remaining = list(COLLAPSE)
        original = train_semantic.evaluate
        train_semantic.evaluate = lambda *a, **k: [remaining.pop(0)]
        self.addCleanup(setattr, train_semantic, "evaluate", original)
        self.trainer = _Trainer(self.keeper, self.N_ENVS)
        self.trainer.run(self.EVERY * len(COLLAPSE))
        self.peak_step = self.EVERY * (COLLAPSE.index(PEAK) + 1)

    def test_the_run_actually_evaluated_the_whole_collapse(self):
        """The control: nothing below means anything if the trigger under-fired."""
        self.assertEqual(
            [mean for _, mean in self.keeper.history],
            list(COLLAPSE),
            f"the callback recorded {self.keeper.history} rather than the "
            f"{len(COLLAPSE)} readouts it was driven with, so the collapse this "
            "test replays never happened and the assertions below are vacuous",
        )

    def test_a_best_checkpoint_exists_at_all(self):
        self.assertTrue(
            self.trainer.written("-best"),
            "no `-best` artifact was ever written across a run that reached "
            f"{PEAK} deliveries; saving only at the end assumes the last update "
            "was the best one, which the measured curve says is false",
        )

    def test_the_best_checkpoint_is_the_peak_and_not_the_last_weights(self):
        """The sharp one: an artifact named `-best` can still hold the collapse."""
        best_saves = self.trainer.written("-best")
        latest_saves = self.trainer.written("-latest")
        self.assertTrue(best_saves, "no `-best` artifact was written at all")
        self.assertTrue(latest_saves, "no `-latest` artifact was written at all")

        self.assertEqual(
            best_saves[-1],
            self.peak_step,
            f"the last `-best` save happened at step {best_saves[-1]} but the "
            f"run peaked at {PEAK} deliveries at step {self.peak_step}; the "
            "artifact keeps its name while holding weights worth "
            f"{COLLAPSE[-1]}, so the run's best result is gone even though a "
            "file called `-best` is sitting on disk",
        )
        self.assertGreater(
            latest_saves[-1],
            best_saves[-1],
            "the run's final weights were saved no later than its best ones, so "
            "this replay never exercised a non-monotonic run and the "
            "distinction it exists to protect was not tested",
        )

    def test_the_kept_score_is_the_peak(self):
        self.assertEqual(
            self.keeper.best,
            PEAK,
            f"the keeper reports its best as {self.keeper.best} against a "
            f"measured peak of {PEAK}",
        )

    def test_the_evaluation_history_is_kept_as_the_run_goes(self):
        """A collapse has to be visible while it happens, not reconstructed after."""
        self.assertEqual(
            [step for step, _ in self.keeper.history],
            [self.EVERY * (index + 1) for index in range(len(COLLAPSE))],
            f"the history is {self.keeper.history}; without a readout at every "
            "interval a collapse is only ever noticed afterwards by someone who "
            "already suspects it",
        )


class _Recorder:
    """A stand-in trainer that records what the script asks it to do, in order."""

    def __init__(self, events, bias_width=31):
        import torch

        self.events = events
        self.policy = types.SimpleNamespace(
            action_net=types.SimpleNamespace(bias=torch.zeros(bias_width))
        )

    def save(self, path):
        self.events.append(("save", str(path)))

    def learn(self, *args, **kwargs):
        self.events.append(("learn", kwargs.get("callback")))
        return self

    def close(self):
        pass


class AnInitialisationIsAClaimSoItIsMeasured(unittest.TestCase):
    """`scripts/train_residual.py` must read out its starting policy first.

    This RUNS `main` with the trainer, the vector env and the readout replaced
    by recorders, rather than reading the source for the right shape. The
    difference is load-bearing: an earlier version of this gate parsed the AST,
    and a readout wrapped in a condition that is never true satisfied every
    assertion while the run took its first gradient step having measured
    nothing. Ordering is a property of execution, so it is asserted by executing.
    """

    @classmethod
    def setUpClass(cls):
        import sb3_contrib
        import stable_baselines3.common.vec_env as vec_env
        import train_residual

        cls.events = []
        readouts = []

        def fake_readout(path, seeds, spec, workers, reference):
            cls.events.append(("readout", str(path)))
            readouts.append(str(path))
            return {
                "mean": 0.0,
                "heuristic": 0.0,
                "gap": 0.0,
                "ci95": 0.0,
                "won": 0,
                "lost": 0,
                "tied": 0,
                "deviation_rate": 0.0,
            }

        originals = {
            (sb3_contrib, "MaskablePPO"): sb3_contrib.MaskablePPO,
            (vec_env, "SubprocVecEnv"): vec_env.SubprocVecEnv,
            (train_residual, "heuristic_reference"): train_residual.heuristic_reference,
            (train_residual, "paired_readout"): train_residual.paired_readout,
        }
        sb3_contrib.MaskablePPO = lambda *a, **k: _Recorder(cls.events)
        vec_env.SubprocVecEnv = lambda thunks: _Recorder(cls.events)
        train_residual.heuristic_reference = lambda seeds, *a: {
            seed: 0.0 for seed in seeds
        }
        train_residual.paired_readout = fake_readout
        try:
            with tempfile.TemporaryDirectory() as folder:
                train_residual.main(
                    [
                        "--output",
                        str(Path(folder) / "model"),
                        "--total-timesteps",
                        "1",
                        "--envs",
                        "1",
                        "--eval-episodes",
                        "1",
                        "--eval-workers",
                        "1",
                    ]
                )
        finally:
            for (module, name), value in originals.items():
                setattr(module, name, value)

        cls.kinds = [kind for kind, _ in cls.events]

    def test_the_script_still_trains(self):
        """The control: no gradient step means every ordering below is trivial."""
        self.assertIn(
            "learn",
            self.kinds,
            f"train_residual.main() recorded {self.kinds} and never trained, so "
            "'before the first gradient step' has no meaning and the assertions "
            "below are asserting nothing",
        )

    def _before_learn(self, kind):
        first_learn = self.kinds.index("learn")
        return [
            payload
            for index, (event, payload) in enumerate(self.events)
            if index < first_learn and event == kind
        ]

    def test_the_starting_policy_is_written_to_disk(self):
        self.assertTrue(
            self._before_learn("save"),
            f"train_residual.main() took its first gradient step without saving "
            f"the policy it started from (recorded {self.kinds}); the opening "
            "policy then exists only as an argument in a docstring, and it has "
            "already been wrong once",
        )

    def test_the_starting_policy_is_evaluated_before_a_single_gradient_step(self):
        self.assertTrue(
            self._before_learn("readout"),
            f"train_residual.main() never measured its own initialisation "
            f"(recorded {self.kinds}); a run that is supposed to start at the "
            "bar and instead starts 37 deliveries below it prints a steadily "
            "closing gap whose end state is just the bar, which reads as "
            "training working and is exactly backwards",
        )

    def test_readout_zero_measures_the_policy_that_was_just_saved(self):
        """Reading out the wrong artifact is the same defect with a number on it."""
        saved = set(self._before_learn("save"))
        read = set(self._before_learn("readout"))

        self.assertTrue(
            saved & read,
            f"train_residual.main() evaluated {sorted(read)} before training "
            f"while saving {sorted(saved)}; readout zero has to be the untrained "
            "policy itself, or the number reported as the starting point belongs "
            "to something else",
        )


class TheBestKeeperMustActuallyBeWiredIntoTheRun(unittest.TestCase):
    """A keeper nothing hands to `learn` saves nothing, and its own tests pass.

    `KeepBest` is driven directly by two test classes, so its arithmetic is
    covered twice over and its CALL SITE was covered nowhere: deleting
    `callback=keeper.build()` from `train_semantic.main` left every one of them
    green while no run would ever have written a best checkpoint again. That is
    the same shape as a helper proved correct in isolation while the defect
    lives where it is called.
    """

    @classmethod
    def setUpClass(cls):
        import sb3_contrib
        import stable_baselines3.common.vec_env as vec_env
        import train_semantic

        cls.events = []
        built = []
        real_keep_best = train_semantic.KeepBest

        class _Watched(real_keep_best):
            def build(self):
                callback = super().build()
                built.append(callback)
                return callback

        originals = {
            (sb3_contrib, "MaskablePPO"): sb3_contrib.MaskablePPO,
            (vec_env, "DummyVecEnv"): vec_env.DummyVecEnv,
            (vec_env, "VecMonitor"): vec_env.VecMonitor,
            (train_semantic, "KeepBest"): real_keep_best,
            (train_semantic, "evaluate"): train_semantic.evaluate,
        }
        sb3_contrib.MaskablePPO = lambda *a, **k: _Recorder(cls.events)
        vec_env.DummyVecEnv = lambda thunks: _Recorder(cls.events)
        vec_env.VecMonitor = lambda inner: inner
        train_semantic.KeepBest = _Watched
        train_semantic.evaluate = lambda *a, **k: [0.0]
        try:
            with tempfile.TemporaryDirectory() as folder:
                train_semantic.main(
                    [
                        "--output",
                        str(Path(folder) / "model"),
                        "--total-timesteps",
                        "1",
                        "--n-envs",
                        "1",
                        "--eval-episodes",
                        "1",
                        "--device",
                        "cpu",
                    ]
                )
        finally:
            for (module, name), value in originals.items():
                setattr(module, name, value)

        cls.built = built

    def test_the_run_reached_its_gradient_step(self):
        """The control."""
        self.assertIn(
            "learn",
            [kind for kind, _ in self.events],
            f"train_semantic.main() recorded {self.events} and never trained",
        )

    def test_the_keeper_is_built_at_all(self):
        self.assertTrue(
            self.built,
            "train_semantic.main() never built a KeepBest callback, so no run "
            "evaluates periodically and nothing is ever checkpointed",
        )

    def test_the_keepers_callback_is_the_one_handed_to_learn(self):
        passed = [payload for kind, payload in self.events if kind == "learn"]

        self.assertTrue(
            any(callback in self.built for callback in passed),
            f"train_semantic.main() called learn with {passed} while the keeper "
            f"built {self.built}; a keeper the trainer never receives evaluates "
            "nothing and saves nothing, and every test that drives KeepBest "
            "directly stays green while it happens",
        )


if __name__ == "__main__":
    unittest.main()

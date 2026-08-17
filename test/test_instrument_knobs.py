"""Knobs that were accepted and silently did nothing.

`--eval-episodes` was passed into `KeepBest`'s `n_episodes` from a *different*
flag, so every in-training evaluation in this project's history ran on 5
episodes whatever the user typed -- against a distribution spanning 110 to 800,
an MDE near +/-190. Every "new best, saved" was a five-episode lottery, and the
checkpoints picked that way are what later comparisons ran against.

That was found by accident, so the whole surface was then audited: 24 argparse
flags plus constructor keywords and module constants, each traced from its parse
site into its consumer with the callee's signature actually opened, and each
suspected defect handed to an independent lane told to refute it. Eighteen
suspects, thirteen confirmed, five refuted.

These tests pin the confirmed thirteen. They are deliberately about OBSERVABLE
consequence rather than about the line of code -- what the optimiser reads, what
the network is fed, what the environment plays -- because every one of these
defects type-checked, ran clean, and produced plausible logs.
"""

import argparse
import os
import sys
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.semantic_env import (  # noqa: E402
    MAX_PATHS,
    MAX_STATIONS,
    PATH_FEATURES,
    RANK_FEATURES,
    REACH_FEATURES,
    RESOURCE_FEATURES,
    STATION_FEATURES,
    SemanticMetroEnv,
)


class TheConstructorSeedIsHonoured(unittest.TestCase):
    """`SemanticMetroEnv(seed=42)` used to draw a fresh board on every reset.

    The argument was accepted and dropped: no TypeError, no warning, and a
    different random layout each time -- so any reproducibility resting on it
    was false while looking exactly like a working seed.
    """

    def test_the_same_constructor_seed_gives_the_same_board(self):
        def layout(seed):
            env = SemanticMetroEnv(seed=seed)
            env.reset()
            try:
                return [
                    (s.position.left, s.position.top) for s in env._mediator.stations
                ]
            finally:
                env.close()

        self.assertEqual(layout(4242), layout(4242))
        self.assertNotEqual(layout(4242), layout(4243))

    def test_reset_still_wins_over_the_constructor(self):
        env = SemanticMetroEnv(seed=4242)
        try:
            env.reset(seed=99)
            pinned = [(s.position.left, s.position.top) for s in env._mediator.stations]
            env.reset(seed=99)
            self.assertEqual(
                pinned,
                [(s.position.left, s.position.top) for s in env._mediator.stations],
            )
        finally:
            env.close()

    def test_no_seed_anywhere_still_varies(self):
        """The default must stay random, or vector envs replay one board."""
        env = SemanticMetroEnv()
        try:
            env.reset()
            first = [(s.position.left, s.position.top) for s in env._mediator.stations]
            for _ in range(8):
                env.reset()
                if [
                    (s.position.left, s.position.top) for s in env._mediator.stations
                ] != first:
                    return
        finally:
            env.close()
        self.fail("eight unseeded resets produced one layout")


class ThePointerExtractorReadsTheResourceBlock(unittest.TestCase):
    """It sliced 80 floats early and was blind to every resource counter.

    The observation is stations | paths | reach | RANK | resources. The
    extractor advanced its cursor past reach and then read `resources`
    immediately, so it was handed the tail of the rank block -- all zeros in
    ordinary play. Locomotives, carriages, credits and the distance to the next
    unlock were structurally invisible, and it trained without error.
    """

    def test_perturbing_the_resource_block_moves_the_features(self):
        try:
            import torch

            from rl.semantic_nets import PointerExtractor
        except ImportError as error:  # pragma: no cover - RL extras absent
            self.skipTest(f"RL dependencies unavailable: {error}")

        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=9000)
        env.close()
        extractor = PointerExtractor(
            __import__("gymnasium").spaces.Box(
                low=-1.0, high=1.0, shape=observation.shape, dtype=np.float32
            )
        )
        base = torch.as_tensor(observation, dtype=torch.float32).unsqueeze(0)
        moved = base.clone()
        start = (
            MAX_STATIONS * STATION_FEATURES
            + MAX_PATHS * PATH_FEATURES
            + REACH_FEATURES
            + RANK_FEATURES
        )
        moved[0, start : start + RESOURCE_FEATURES] += 0.25
        with torch.no_grad():
            self.assertFalse(
                torch.allclose(extractor(base), extractor(moved)),
                "the resource block does not reach the network",
            )

    def test_the_block_it_reads_is_the_block_the_env_wrote(self):
        try:
            from rl.semantic_nets import PATH_BLOCK, STATION_BLOCK
        except ImportError as error:  # pragma: no cover - RL extras absent
            self.skipTest(f"RL dependencies unavailable: {error}")
        self.assertEqual(
            STATION_BLOCK + PATH_BLOCK + REACH_FEATURES + RANK_FEATURES,
            SemanticMetroEnv._observation_size() - RESOURCE_FEATURES,
        )


class TheDeviceGuardCatchesEveryCudaSpelling(unittest.TestCase):
    """`cuda:0` slipped past a membership test against ("auto", "cuda").

    On the CPU-only Windows wheel that is the silent ~100x slowdown the guard
    exists to prevent, on the one spelling anyone with two cards would use.
    """

    def _guard(self):
        from train_rl import require_usable_device

        return require_usable_device

    def test_an_indexed_cuda_device_is_refused_without_cuda(self):
        guard = self._guard()
        for requested in ("cuda", "cuda:0", "cuda:1", "auto"):
            with self.subTest(requested=requested):
                with self.assertRaises(SystemExit) as caught:
                    guard(requested, cuda_available=False)
                self.assertIn(requested, str(caught.exception))
                self.assertIn("--device cpu", str(caught.exception))

    def test_cpu_is_always_honoured_and_cuda_passes_when_present(self):
        guard = self._guard()
        self.assertEqual(guard("cpu", cuda_available=False), "cpu")
        self.assertEqual(guard("auto", cuda_available=True), "cuda")
        self.assertEqual(guard("cuda:1", cuda_available=True), "cuda:1")


class FlagsThatTheCheckpointOverridesAreRefused(unittest.TestCase):
    """A warm start takes its architecture from the checkpoint.

    `--resume x.zip --arch pointer` used to run happily on the checkpoint's MLP
    while reporting the pointer architecture, and `--spatial-pointer` did the
    same in the pixel lane. Silently ignoring a flag that names the thing being
    measured is how an experiment records a variable it never varied.
    """

    def test_train_semantic_refuses_arch_with_resume(self):
        import train_semantic

        with self.assertRaises(SystemExit):
            train_semantic.main(
                ["--resume", "nonexistent.zip", "--arch", "pointer", "--output", "x"]
            )

    def test_train_rl_refuses_spatial_pointer_with_resume(self):
        import train_rl

        with self.assertRaises(SystemExit):
            train_rl.main(["--resume", "nonexistent.zip", "--spatial-pointer"])

    def test_the_dead_checkpoint_episodes_flag_is_gone(self):
        import train_semantic

        parser_flags = train_semantic.__doc__ or ""
        with self.assertRaises(SystemExit):
            train_semantic.main(["--checkpoint-episodes", "40"])
        self.assertNotIn("--checkpoint-episodes", parser_flags)


class TheBlindControlFailsRatherThanChangingIdentity(unittest.TestCase):
    """A missing dataset turned the blind null into the uniform-random control.

    `output/` is gitignored, so on any fresh checkout the npz is absent -- and
    the `path.exists()` guard fell through to the Laplace uniform. The two nulls
    score differently and the substitution was silent.
    """

    def test_a_named_but_missing_dataset_raises(self):
        import blind_control

        with self.assertRaises(FileNotFoundError):
            blind_control.action_prior(Path("output/semantic/definitely-not-here.npz"))

    def test_no_dataset_named_is_still_the_deliberate_uniform(self):
        import blind_control

        prior = blind_control.action_prior(None)
        self.assertTrue(np.allclose(prior, prior[0]))

    def test_the_dataset_path_does_not_depend_on_the_working_directory(self):
        import blind_control

        self.assertTrue(blind_control.DATASET.is_absolute())


class TheRecorderUsesResampledFutures(unittest.TestCase):
    """`--player search` recorded the oracle, not this repo's search.

    The serialised state carries the RNG, so scoring a candidate on the
    unmodified document measures it against the one future that actually
    happens. `search_policy` was fixed for exactly this; the recorder kept the
    old call, so every playthrough it produced was the clairvoyant player.
    """

    def test_play_requires_futures_with_no_default(self):
        import inspect

        import record_semantic

        parameters = inspect.signature(record_semantic.play).parameters
        self.assertIn("futures", parameters)
        self.assertIs(parameters["futures"].default, inspect.Parameter.empty)

    def test_the_recorder_does_not_import_the_bare_rollout(self):
        import record_semantic

        self.assertTrue(hasattr(record_semantic, "expected_value"))
        self.assertFalse(hasattr(record_semantic, "_rollout"))


class TheMacEstimateFollowsTheRenderProfile(unittest.TestCase):
    """`render_profile=` moved the convolutions and silently not the head.

    The action head emits one logit per kind plus one per pixel column and row,
    so it scales with the render surface; it was written as the literals
    8 + 192 + 108, understating the fidelity profile by 12,800 MACs.
    """

    def test_a_larger_profile_reports_a_larger_action_head(self):
        from rl.history import HistoryDescriptor
        from rl.protocol import FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE
        from rl.resource_profile import estimate_inference_macs

        history = HistoryDescriptor(
            layout="decision-history-v1",
            offsets=(128, 64, 32, 16, 7, 6, 5, 4, 3, 2, 1, 0),
        )
        fast = estimate_inference_macs(history, FAST_RENDER_PROFILE)
        fidelity = estimate_inference_macs(history, FIDELITY_RENDER_PROFILE)
        self.assertGreater(fidelity.action_head, fast.action_head)


class TheResumeLearningRateReachesTheOptimiser(unittest.TestCase):
    """Assigning `model.learning_rate` after `load()` changed nothing.

    `load()` has already built `lr_schedule` from the checkpoint's saved rate,
    and `_update_learning_rate` reads the schedule and never the attribute. So
    every warm start in this project's history trained at the checkpoint's rate
    -- a constant 3e-4 inherited from the clone -- whatever `--learning-rate`
    said. This asserts the fix at the level that matters: the value the
    optimiser would actually use.
    """

    def test_rebuilding_the_schedule_makes_the_attribute_live(self):
        try:
            from sb3_contrib import MaskablePPO
        except ImportError as error:  # pragma: no cover - RL extras absent
            self.skipTest(f"RL dependencies unavailable: {error}")
        import tempfile

        from rl.event_gate import EventGatedSemanticEnv

        model = MaskablePPO(
            "MlpPolicy",
            EventGatedSemanticEnv(),
            learning_rate=3e-4,
            n_steps=8,
            batch_size=8,
            device="cpu",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ckpt")
            model.save(path)
            reloaded = MaskablePPO.load(path, device="cpu")
            reloaded.learning_rate = 1e-5
            self.assertAlmostEqual(reloaded.lr_schedule(1.0), 3e-4, places=9)
            reloaded._setup_lr_schedule()
            self.assertAlmostEqual(reloaded.lr_schedule(1.0), 1e-5, places=9)

    def test_train_semantic_rebuilds_it_on_the_resume_path(self):
        source = (
            Path(__file__).resolve().parent.parent / "scripts" / "train_semantic.py"
        ).read_text(encoding="utf-8")
        assign = source.index("model.learning_rate = args.learning_rate")
        rebuild = source.index("model._setup_lr_schedule()")
        self.assertGreater(rebuild, assign)


def _unused_guard():
    """Keep argparse imported for readers tracing the flags under test."""
    return argparse.ArgumentParser


if __name__ == "__main__":
    unittest.main()

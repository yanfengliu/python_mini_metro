"""Asking for the best device must not silently hand back a slow one.

An RL install on Windows resolves a CPU-only torch unless the CUDA overlay is
applied, and nothing about that failure is visible: training runs, logs look
healthy, and it is roughly 100x slower. `--device auto` means "give me the
accelerator", so it fails when there is none. Choosing `--device cpu` stays
allowed, because that is a stated intent rather than an accident.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import train_rl  # noqa: E402


class DeviceGuardTest(unittest.TestCase):
    def test_auto_without_an_accelerator_fails_with_an_actionable_message(self):
        with self.assertRaises(SystemExit) as raised:
            train_rl.require_usable_device("auto", cuda_available=False)

        message = str(raised.exception)
        self.assertIn("--device cpu", message)
        self.assertIn("requirements-rl-cuda", message)

    def test_auto_with_an_accelerator_resolves_to_cuda(self):
        self.assertEqual(
            train_rl.require_usable_device("auto", cuda_available=True), "cuda"
        )

    def test_explicit_cpu_is_a_stated_intent_and_is_honoured(self):
        """CI trains on GPU-less runners and passes --device cpu deliberately."""
        self.assertEqual(
            train_rl.require_usable_device("cpu", cuda_available=False), "cpu"
        )

    def test_explicit_cuda_without_an_accelerator_still_fails(self):
        with self.assertRaises(SystemExit):
            train_rl.require_usable_device("cuda", cuda_available=False)

    def test_an_unrelated_device_string_is_passed_through_untouched(self):
        self.assertEqual(
            train_rl.require_usable_device("mps", cuda_available=False), "mps"
        )


if __name__ == "__main__":
    unittest.main()

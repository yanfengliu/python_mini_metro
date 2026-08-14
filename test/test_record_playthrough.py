"""The recorder must produce a watchable file and a summary that tells the truth.

Its first version read the demonstrator's results off the wrong object with
``getattr(..., default)``, so it silently reported zero deliveries for a run that
had actually delivered. A recording whose summary understates the run is worse
than no recording, because it looks like evidence.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import record_playthrough  # noqa: E402
from PIL import Image  # noqa: E402


class RecordPlaythroughTest(unittest.TestCase):
    def _run(self, *argv: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.gif"
            summary = record_playthrough.record(
                record_playthrough.parse_args([*argv, "--output", str(output)])
            )
            with Image.open(output) as animation:
                summary["_frames_on_disk"] = getattr(animation, "n_frames", 1)
            return summary

    def test_writes_a_multi_frame_animation(self):
        summary = self._run(
            "--policy", "noop", "--max-decisions", "60", "--stride", "5"
        )

        self.assertGreater(summary["_frames_on_disk"], 1)
        self.assertEqual(summary["frames_written"], summary["_frames_on_disk"])
        self.assertGreaterEqual(summary["frames_captured"], summary["frames_written"])
        self.assertGreater(summary["bytes"], 0)

    def test_demonstrator_summary_reports_the_deliveries_it_actually_made(self):
        """The demonstrator delivers by contract, so a zero here is a reporting bug."""
        summary = self._run(
            "--policy", "demonstrator", "--max-decisions", "200", "--stride", "10"
        )

        self.assertGreater(
            summary["deliveries"],
            0,
            "the demonstrator is verified to deliver, so a zero means the summary "
            "read the wrong field rather than that the run failed",
        )

    def test_random_play_is_recorded_up_to_its_own_game_over(self):
        summary = self._run(
            "--policy", "random", "--seed", "0", "--max-decisions", "3000"
        )

        self.assertEqual(summary["ended"], "game-over")
        self.assertLess(summary["decisions"], 3000)
        self.assertGreater(
            summary["frames_written"],
            10,
            "a real game reaching game over must leave many distinct frames; "
            "a near-empty animation means capture, not compression, failed",
        )


if __name__ == "__main__":
    unittest.main()

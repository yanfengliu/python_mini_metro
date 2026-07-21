import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test.test_gm06c_replay_contract import assert_bijection

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = REPO_ROOT / "scripts" / "fixtures" / "recursive-playtest.json"


def jsonl_rows(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class TestGM06cFreshProcessReplay(unittest.TestCase):
    def test_python_fresh_process_replay_matches_nonempty_carriage_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            replay = root / "replay"
            environment = {**os.environ, "PYTHONHASHSEED": "0"}
            runner = REPO_ROOT / "src" / "recursive_playtest.py"
            initial = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--scenario",
                    str(DEFAULT_SCENARIO),
                    "--out",
                    str(first),
                    "--run-id",
                    "gm06c-python-v5",
                ],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr or initial.stdout)
            redrive = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--inputs",
                    str(first / "inputs.json"),
                    "--out",
                    str(replay),
                    "--run-id",
                    "gm06c-python-v5-redrive",
                ],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(redrive.returncode, 0, redrive.stderr or redrive.stdout)

            original_rows = jsonl_rows(first / "transcript.jsonl")
            replay_rows = jsonl_rows(replay / "transcript.jsonl")
            self.assertEqual(original_rows, replay_rows)
            carriage_rows = [
                row
                for row in original_rows
                if row["action"].get("type") == "attach_carriage"
            ]
            self.assertEqual(len(carriage_rows), 1)
            self.assertGreater(len(carriage_rows[0]["checkpoint"]["carriages"]), 0)
            assert_bijection(self, carriage_rows[0]["checkpoint"])


if __name__ == "__main__":
    unittest.main()

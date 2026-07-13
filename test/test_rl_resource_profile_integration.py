from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

if any(
    find_spec(name) is None
    for name in ("gymnasium", "stable_baselines3", "sb3_contrib", "torch")
):
    raise unittest.SkipTest("the exact reinforcement-learning stack is optional")

from rl.history import (
    DECISION_HISTORY_LAYOUT,
    EIGHT_MULTISCALE_HISTORY_LAYOUT,
    TEN_MULTISCALE_HISTORY_LAYOUT,
    contiguous_history,
)
from scripts import profile_rl_history_worker as worker


class TestResourceProfileWorker(unittest.TestCase):
    def test_worker_top_level_imports_remain_stdlib_only(self) -> None:
        source = Path(worker.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertEqual(
            imported_roots,
            {
                "__future__",
                "argparse",
                "dataclasses",
                "json",
                "os",
                "pathlib",
                "sys",
                "time",
                "typing",
            },
        )

    def test_candidate_resolution_uses_exact_reviewed_descriptors(self) -> None:
        expected = {
            "8-contiguous": ("contiguous-history-v1", tuple(range(7, -1, -1))),
            "8-multiscale": (
                EIGHT_MULTISCALE_HISTORY_LAYOUT,
                (128, 64, 32, 16, 3, 2, 1, 0),
            ),
            "12-multiscale": (
                DECISION_HISTORY_LAYOUT,
                (128, 64, 32, 16, 7, 6, 5, 4, 3, 2, 1, 0),
            ),
            "10-multiscale": (
                TEN_MULTISCALE_HISTORY_LAYOUT,
                (128, 64, 7, 6, 5, 4, 3, 2, 1, 0),
            ),
        }
        for candidate, (layout, offsets) in expected.items():
            with self.subTest(candidate=candidate):
                history = worker.resolve_candidate(candidate)
                self.assertEqual(history.layout, layout)
                self.assertEqual(history.offsets, offsets)

        with self.assertRaisesRegex(ValueError, "candidate"):
            worker.resolve_candidate("unreviewed")

    def test_preimport_handshake_is_exact_and_atomic_writer_replaces(self) -> None:
        stdout = io.StringIO()
        worker.release_preimport_handshake(
            input_stream=io.StringIO("START\n"),
            output_stream=stdout,
            pid=123,
        )
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"event": "ready", "pid": 123},
        )
        with self.assertRaisesRegex(RuntimeError, "START"):
            worker.release_preimport_handshake(
                input_stream=io.StringIO("start\n"),
                output_stream=io.StringIO(),
                pid=123,
            )

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary, "result.json")
            worker.write_result_atomic(path, {"second": 2, "first": 1})
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                '{"first":1,"second":2}\n',
            )
            self.assertEqual(list(path.parent.glob("*.tmp-*")), [])

    def test_two_real_recurrent_updates_capture_measured_storage_and_rates(
        self,
    ) -> None:
        workload = worker.ProfileWorkload(
            n_envs=1,
            n_steps=2,
            n_epochs=1,
            schedule_horizon=100,
            seed=17,
            device="cpu",
        )
        result = worker.run_profile(
            history=contiguous_history(2),
            candidate="integration-contiguous-2",
            workload=workload,
        )

        self.assertEqual(result["schema"], "mini-metro-history-profile-worker-v1")
        self.assertEqual(result["workload"]["transitionsPerIteration"], 2)
        self.assertEqual(result["workload"]["batchSize"], 2)
        self.assertEqual(result["workload"]["nEpochs"], 1)
        self.assertEqual(result["workload"]["scheduleHorizon"], 100)
        self.assertEqual(
            [(row["phase"], row["transitions"]) for row in result["iterations"]],
            [("warmup", 2), ("measured", 2)],
        )
        self.assertEqual(
            [row["epochUpdates"] for row in result["iterations"]],
            [1, 1],
        )
        self.assertGreater(result["iterations"][1]["learningRate"], 0.0)
        self.assertEqual(result["warmupMaximumValidAges"], [1])
        self.assertEqual(result["expectedMaximumValidAge"], 1)

        storage = result["storage"]
        self.assertEqual(storage["rolloutBuffer"]["shape"], [2, 1, 6, 108, 192])
        self.assertEqual(storage["rolloutBuffer"]["dtype"], "uint8")
        self.assertEqual(storage["oneStepOutput"]["shape"], [1, 6, 108, 192])
        self.assertEqual(storage["oneStepOutput"]["dtype"], "uint8")
        self.assertGreater(storage["historyRingBytes"], 0)

        minibatches = result["measuredOptimizerMinibatches"]
        normalized = result["measuredNormalizedInputs"]
        self.assertEqual(len(minibatches), 1)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(minibatches[0]["observation"]["dtype"], "uint8")
        self.assertEqual(normalized[0]["dtype"], "float32")
        self.assertEqual(minibatches[0]["validRows"], 2)
        self.assertEqual(minibatches[0]["paddedRows"], 2)
        self.assertEqual(result["rates"]["validOptimizerRows"], 2)
        self.assertEqual(result["rates"]["paddedOptimizerRows"], 2)
        self.assertGreater(result["rates"]["collectionFps"], 0.0)
        self.assertGreater(result["rates"]["validOptimizerRowsPerSecond"], 0.0)
        self.assertGreater(result["rates"]["endToEndFps"], 0.0)

        model = result["model"]
        self.assertGreater(model["trainableParameters"], 0)
        self.assertGreater(model["inferenceForwardMacs"]["total"], 0)
        self.assertEqual(
            set(model["inferenceForwardMacs"]["components"]),
            {
                "actionHead",
                "actorLstm",
                "actorMlp",
                "cnn",
                "criticLstm",
                "criticMlp",
                "valueHead",
            },
        )
        self.assertLess(
            result["measurementWindow"]["startPerfCounterNs"],
            result["measurementWindow"]["endPerfCounterNs"],
        )


if __name__ == "__main__":
    unittest.main()

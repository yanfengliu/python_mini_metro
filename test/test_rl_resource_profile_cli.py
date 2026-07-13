from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.protocol import TaskSpec, protocol_fingerprint
from rl.training import compute_training_fingerprint


def load_profile_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "profile_rl_history.py"
    spec = importlib.util.spec_from_file_location("mini_metro_profile_rl_history", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestProfileSourceState(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile_script()

    def test_cleanliness_allows_only_the_declared_agents_tree(self) -> None:
        state = self.profile.analyze_status_records(
            ("?? .agents/skill/notes.md", "?? .agents/cache/item.json")
        )

        self.assertTrue(state["clean"])
        self.assertEqual(
            state["allowedUntracked"],
            [".agents/cache/item.json", ".agents/skill/notes.md"],
        )
        self.assertEqual(state["unexpected"], [])
        self.assertEqual(state["ignoredOutputPrefixes"], ["output/"])

    def test_supervisor_boundary_keeps_both_files_focused_and_reexported(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "profile_rl_history.py"
        supervisor = root / "src" / "rl" / "profile_supervisor.py"

        self.assertLess(len(script.read_text(encoding="utf-8").splitlines()), 500)
        self.assertLess(len(supervisor.read_text(encoding="utf-8").splitlines()), 500)
        self.assertEqual(
            self.profile.analyze_status_records.__module__,
            "rl.profile_supervisor",
        )
        self.assertEqual(
            self.profile.supervise_worker.__module__,
            "rl.profile_supervisor",
        )
        for name in ("runtime_metadata", "sha256_file", "write_json"):
            with self.subTest(name=name):
                self.assertEqual(
                    getattr(self.profile, name).__module__,
                    "rl.profile_supervisor",
                )

    def test_cleanliness_rejects_tracked_staged_and_unexpected_untracked(self) -> None:
        for record in (" M src/rl/policy.py", "M  README.md", "?? surprise.py"):
            with self.subTest(record=record):
                state = self.profile.analyze_status_records((record,))
                self.assertFalse(state["clean"])
                self.assertEqual(state["unexpected"], [record])

    def test_production_worker_contract_detects_storage_drift(self) -> None:
        history = self.profile.PRIMARY_CANDIDATES["8-contiguous"]
        storage = self.profile.estimate_storage(history)
        macs = self.profile.estimate_inference_macs(history)
        channels = 24
        padded_rows = 64
        raw_batch_bytes = padded_rows * channels * 108 * 192
        mac_components = {
            "actionHead": macs.action_head,
            "actorLstm": macs.actor_lstm,
            "actorMlp": macs.actor_mlp,
            "cnn": macs.cnn_convolutions + macs.cnn_projection,
            "criticLstm": macs.critic_lstm,
            "criticMlp": macs.critic_mlp,
            "valueHead": macs.value_head,
        }
        result = {
            "candidate": "8-contiguous",
            "history": history.to_dict(),
            "historyFingerprint": history.fingerprint(),
            "iterations": [
                {
                    "epochUpdates": 4,
                    "learningRate": 0.1,
                    "collectionSeconds": 1.0,
                    "phase": phase,
                    "trainingSeconds": 1.0,
                    "transitions": 1024,
                }
                for phase in ("warmup", "measured")
            ],
            "measurementWindow": {
                "endPerfCounterNs": 2,
                "startPerfCounterNs": 1,
            },
            "measuredNormalizedInputs": [
                {
                    "bytes": raw_batch_bytes * 4,
                    "dtype": "float32",
                    "shape": [padded_rows, channels, 108, 192],
                }
                for _ in range(64)
            ],
            "measuredOptimizerMinibatches": [
                {
                    "mask": {
                        "bytes": padded_rows * 4,
                        "dtype": "float32",
                        "shape": [padded_rows],
                    },
                    "observation": {
                        "bytes": raw_batch_bytes,
                        "dtype": "uint8",
                        "shape": [padded_rows, channels, 108, 192],
                    },
                    "paddedRows": padded_rows,
                    "validRows": padded_rows,
                }
                for _ in range(64)
            ],
            "model": {
                "inferenceForwardMacs": {
                    "components": mac_components,
                    "total": macs.total,
                },
                "trainableParameters": 1,
            },
            "protocolFingerprint": protocol_fingerprint(),
            "rates": {
                "collectionFps": 1024.0,
                "endToEndFps": 512.0,
                "paddedOptimizerRows": 4096,
                "paddedOptimizerRowsPerSecond": 4096.0,
                "validOptimizerRows": 4096,
                "validOptimizerRowsPerSecond": 4096.0,
            },
            "schema": "mini-metro-history-profile-worker-v1",
            "storage": {
                "historyRingBytes": storage.history_ring_bytes,
                "oneStepOutput": {
                    "bytes": storage.one_step_output_bytes,
                    "dtype": "uint8",
                    "shape": [8, channels, 108, 192],
                },
                "rolloutBuffer": {
                    "bytes": storage.rollout_observations_bytes,
                    "dtype": "uint8",
                    "shape": [128, 8, channels, 108, 192],
                },
            },
            "taskFingerprint": TaskSpec().fingerprint(),
            "trainingFingerprint": compute_training_fingerprint(
                Path(__file__).resolve().parents[1]
            ),
            "warmupMaximumValidAges": [7] * 8,
            "workload": {
                "batchSize": 64,
                "device": "cpu",
                "nEnvs": 8,
                "nEpochs": 4,
                "nSteps": 128,
                "scheduleHorizon": 1_000_000,
                "seed": 42,
                "torchInteropThreads": 24,
                "torchThreads": 24,
                "transitionsPerIteration": 1024,
            },
        }

        self.assertEqual(
            self.profile.validate_worker_result(
                "8-contiguous",
                result,
                repo_root=Path(__file__).resolve().parents[1],
                seed=42,
                torch_threads=24,
                torch_interop_threads=24,
            ),
            (),
        )
        result["storage"]["historyRingBytes"] += 1
        self.assertEqual(
            self.profile.validate_worker_result(
                "8-contiguous",
                result,
                repo_root=Path(__file__).resolve().parents[1],
                seed=42,
                torch_threads=24,
                torch_interop_threads=24,
            ),
            ("historyRingBytes",),
        )
        result["storage"]["historyRingBytes"] -= 1
        result["rates"]["endToEndFps"] = None
        self.assertIn(
            "endToEndFps",
            self.profile.validate_worker_result(
                "8-contiguous",
                result,
                repo_root=Path(__file__).resolve().parents[1],
                seed=42,
                torch_threads=24,
                torch_interop_threads=24,
            ),
        )

    def test_mocked_primary_campaign_reaches_bounded_summary_emission(self) -> None:
        source = {
            "allowedUntracked": [".agents/example"],
            "clean": True,
            "commit": "a" * 40,
            "ignoredOutputPrefixes": ["output/"],
            "unexpected": [],
        }
        runtime = {"python": "test-runtime"}
        supervised = {
            "failures": [{"kind": "intentional-test-invalid"}],
            "fullLifecyclePeakWorkingSetBytes": 1,
            "schema": "mini-metro-history-profile-supervisor-v1",
            "valid": False,
            "workerResult": None,
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "campaign"
            args = SimpleNamespace(
                campaign="primary",
                output_dir=output_dir,
                repeats=3,
                seed=42,
                torch_interop_threads=24,
                torch_threads=24,
            )
            with (
                patch.object(
                    self.profile,
                    "collect_source_state",
                    return_value=source,
                ) as source_call,
                patch.object(
                    self.profile,
                    "runtime_metadata",
                    return_value=runtime,
                ),
                patch.object(
                    self.profile,
                    "sha256_file",
                    return_value="b" * 64,
                ),
                patch.object(
                    self.profile,
                    "supervise_worker",
                    side_effect=lambda *_args, **_kwargs: supervised.copy(),
                ) as supervise_call,
            ):
                summary_path = self.profile.run_campaign(args)

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(source_call.call_count, 19)
            self.assertEqual(supervise_call.call_count, 9)
            self.assertEqual(summary["runtime"], runtime)
            self.assertEqual(summary["source"], source)
            self.assertFalse(summary["decision"]["promoted"])
            self.assertEqual(len(summary["runSummaries"]), 9)
            for run in summary["runSummaries"]:
                self.assertEqual(run["runtime"], runtime)
                self.assertEqual(run["sourceBefore"], source)
                self.assertEqual(run["sourceAfter"], source)
                self.assertEqual(run["profileScriptSha256"], "b" * 64)
                self.assertEqual(run["workerScriptSha256"], "b" * 64)
                self.assertTrue(run["command"])
            self.assertFalse(summary["operationallyValid"])

    def test_main_distinguishes_operational_failure_from_failed_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary_path = Path(temporary) / "summary.json"
            argv = ["--torch-threads", "24", "--torch-interop-threads", "24"]
            for operational, expected in ((False, 1), (True, 0)):
                with self.subTest(operational=operational):
                    summary_path.write_text(
                        json.dumps({"operationallyValid": operational}) + "\n",
                        encoding="utf-8",
                    )
                    with patch.object(
                        self.profile,
                        "run_campaign",
                        return_value=summary_path,
                    ):
                        self.assertEqual(self.profile.main(argv), expected)

    def test_post_worker_source_drift_is_durable_and_aborts_future_runs(self) -> None:
        source = {
            "allowedUntracked": [],
            "clean": True,
            "commit": "a" * 40,
            "ignoredOutputPrefixes": ["output/"],
            "unexpected": [],
        }
        dirty = {**source, "clean": False, "unexpected": [" M src/rl/policy.py"]}
        supervised = {
            "failures": [{"kind": "worker-result-missing"}],
            "fullLifecyclePeakWorkingSetBytes": 1,
            "schema": "mini-metro-history-profile-supervisor-v1",
            "valid": False,
            "workerResult": None,
        }
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(
                campaign="primary",
                output_dir=Path(temporary) / "campaign",
                repeats=3,
                seed=42,
                torch_interop_threads=24,
                torch_threads=24,
            )
            with (
                patch.object(
                    self.profile,
                    "collect_source_state",
                    side_effect=(source, source, dirty),
                ),
                patch.object(self.profile, "runtime_metadata", return_value={}),
                patch.object(self.profile, "sha256_file", return_value="b" * 64),
                patch.object(
                    self.profile,
                    "supervise_worker",
                    return_value=supervised.copy(),
                ),
            ):
                summary_path = self.profile.run_campaign(args)

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertFalse(summary["operationallyValid"])
            self.assertEqual(len(summary["runSummaries"]), 1)
            self.assertEqual(
                summary["campaignFailures"][0]["kind"],
                "source-state-changed-during-worker",
            )


@unittest.skipUnless(sys.platform == "win32", "Windows supervisor integration")
class TestProfileSupervisor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile_script()

    def test_supervisor_handshake_samples_lifetime_and_hashes_raw_evidence(
        self,
    ) -> None:
        worker = textwrap.dedent(
            """
            import json, os, pathlib, sys, time
            result = pathlib.Path(sys.argv[1])
            print(json.dumps({"event": "ready", "pid": os.getpid()}), flush=True)
            if sys.stdin.readline() != "START\\n":
                raise SystemExit(9)
            print("x" * 200000, flush=True)
            started = time.perf_counter_ns()
            payload = bytearray(8 * 1024 * 1024)
            time.sleep(0.18)
            ended = time.perf_counter_ns()
            result.write_text(json.dumps({
                "measurementWindow": {
                    "startPerfCounterNs": started,
                    "endPerfCounterNs": ended,
                },
                "rates": {"endToEndFps": 12.5},
                "workload": {"batchSize": 64, "nEpochs": 4},
                "payloadBytes": len(payload),
            }) + "\\n", encoding="utf-8")
            """
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            result_path = run_dir / "worker-result.json"
            outcome = self.profile.supervise_worker(
                (sys.executable, "-c", worker, str(result_path)),
                run_dir=run_dir,
                result_path=result_path,
                working_directory=Path(__file__).resolve().parents[1],
                interval_ns=20_000_000,
                maximum_timing_ns=500_000_000,
            )

            self.assertTrue(outcome["valid"], outcome["failures"])
            self.assertEqual(outcome["exitCode"], 0)
            self.assertGreater(outcome["sampleCount"], 2)
            self.assertGreater(outcome["fullLifecyclePeakWorkingSetBytes"], 0)
            self.assertGreater(outcome["measuredPeakWorkingSetBytes"], 0)
            self.assertLessEqual(
                outcome["measuredPeakWorkingSetBytes"],
                outcome["fullLifecyclePeakWorkingSetBytes"],
            )
            self.assertEqual(len(outcome["sampleSha256"]), 64)
            self.assertEqual(len(outcome["stdoutSha256"]), 64)
            self.assertEqual(len(outcome["stderrSha256"]), 64)
            self.assertEqual(outcome["workerResult"]["payloadBytes"], 8 * 1024 * 1024)
            sample_lines = (
                (run_dir / "resource-samples.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            self.assertEqual(len(sample_lines), outcome["sampleCount"])
            self.assertTrue(all(json.loads(line)["schema"] for line in sample_lines))

    def test_supervisor_times_out_and_cleans_a_pre_ready_worker(self) -> None:
        source = textwrap.dedent(
            """
            import os, pathlib, sys, time
            pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding="utf-8")
            time.sleep(5)
            """
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            pid_path = run_dir / "pid.txt"
            with self.assertRaisesRegex(RuntimeError, "pre-import barrier"):
                self.profile.supervise_worker(
                    (sys.executable, "-c", source, str(pid_path)),
                    run_dir=run_dir,
                    result_path=run_dir / "missing.json",
                    working_directory=Path(__file__).resolve().parents[1],
                    ready_timeout_seconds=0.1,
                )
            pid = int(pid_path.read_text(encoding="utf-8"))
            with self.assertRaises(OSError):
                os.kill(pid, 0)

    def test_supervisor_accepts_a_venv_style_ready_descendant(self) -> None:
        child_source = textwrap.dedent(
            """
            import json, os, pathlib, sys, time
            result = pathlib.Path(sys.argv[1])
            print(json.dumps({"event": "ready", "pid": os.getpid()}), flush=True)
            if sys.stdin.readline() != "START\\n":
                raise SystemExit(9)
            started = time.perf_counter_ns()
            time.sleep(0.15)
            ended = time.perf_counter_ns()
            result.write_text(json.dumps({
                "measurementWindow": {
                    "startPerfCounterNs": started,
                    "endPerfCounterNs": ended,
                }
            }) + "\\n", encoding="utf-8")
            """
        )
        launcher_source = textwrap.dedent(
            """
            import subprocess, sys
            completed = subprocess.run(
                [sys.executable, sys.argv[1], sys.argv[2]],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            raise SystemExit(completed.returncode)
            """
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            child_path = run_dir / "child.py"
            launcher_path = run_dir / "launcher.py"
            result_path = run_dir / "worker-result.json"
            child_path.write_text(child_source, encoding="utf-8")
            launcher_path.write_text(launcher_source, encoding="utf-8")

            outcome = self.profile.supervise_worker(
                (sys.executable, str(launcher_path), str(child_path), str(result_path)),
                run_dir=run_dir,
                result_path=result_path,
                working_directory=Path(__file__).resolve().parents[1],
                interval_ns=20_000_000,
                maximum_timing_ns=500_000_000,
            )

            self.assertTrue(outcome["valid"], outcome["failures"])
            self.assertNotEqual(outcome["launcherPid"], outcome["workerPid"])


if __name__ == "__main__":
    unittest.main()

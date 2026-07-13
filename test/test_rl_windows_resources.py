from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.windows_api import WindowsCallError
from rl.windows_resources import (
    ACQUISITION_DURATION_EXCEEDED,
    LIVE_PROCESS_QUERY_FAILED,
    PROCESS_EXITED_DURING_SAMPLE,
    SAMPLE_GAP_EXCEEDED,
    ProcessLifetime,
    ProcessRecord,
    WindowsProcessTreeSampler,
    absolute_deadline_ns,
    discover_descendants,
    sleep_until_deadline_seconds,
    timing_failures,
)


class TestProcessAncestry(unittest.TestCase):
    def test_discovers_out_of_order_descendants_after_parent_exit(self) -> None:
        known = (ProcessLifetime(pid=10, creation_time=100, exit_time=200),)
        rows = (
            ProcessRecord(pid=30, parent_pid=20, creation_time=175),
            ProcessRecord(pid=20, parent_pid=10, creation_time=150),
        )

        discovered = discover_descendants(rows, known)

        self.assertEqual(
            [(row.pid, row.parent_pid) for row in discovered], [(20, 10), (30, 20)]
        )

    def test_rejects_pid_reuse_after_historical_parent_exit(self) -> None:
        known = (ProcessLifetime(pid=10, creation_time=100, exit_time=200),)
        rows = (
            ProcessRecord(pid=20, parent_pid=10, creation_time=201),
            ProcessRecord(pid=30, parent_pid=20, creation_time=202),
        )

        self.assertEqual(discover_descendants(rows, known), ())

    def test_existing_identity_is_not_rediscovered(self) -> None:
        known = (
            ProcessLifetime(pid=10, creation_time=100),
            ProcessLifetime(pid=20, creation_time=150),
        )
        rows = (
            ProcessRecord(pid=20, parent_pid=10, creation_time=150),
            ProcessRecord(pid=30, parent_pid=20, creation_time=175),
        )

        self.assertEqual(
            discover_descendants(rows, known),
            (ProcessRecord(pid=30, parent_pid=20, creation_time=175),),
        )


class TestSamplingSchedule(unittest.TestCase):
    def test_absolute_deadlines_do_not_accumulate_acquisition_time(self) -> None:
        self.assertEqual(absolute_deadline_ns(1_000, 0, 50), 1_000)
        self.assertEqual(absolute_deadline_ns(1_000, 3, 50), 1_150)
        self.assertEqual(sleep_until_deadline_seconds(1_150, 1_125), 0.000000025)
        self.assertEqual(sleep_until_deadline_seconds(1_150, 1_200), 0.0)

    def test_timing_failures_report_gap_and_acquisition_metadata(self) -> None:
        failures = timing_failures(
            sample_starts_ns=(0, 50, 151),
            acquisition_durations_ns=(10, 101, 20),
            maximum_ns=100,
        )

        self.assertEqual(
            [failure.kind for failure in failures],
            [SAMPLE_GAP_EXCEEDED, ACQUISITION_DURATION_EXCEEDED],
        )
        self.assertEqual(failures[0].observed_ns, 101)
        self.assertEqual(failures[0].limit_ns, 100)
        self.assertEqual(failures[1].sample_index, 1)
        self.assertEqual(failures[1].observed_ns, 101)

    def test_equality_at_timing_limit_passes(self) -> None:
        self.assertEqual(
            timing_failures(
                sample_starts_ns=(0, 100),
                acquisition_durations_ns=(100, 100),
                maximum_ns=100,
            ),
            (),
        )


@unittest.skipUnless(sys.platform == "win32", "Windows API integration")
class TestWindowsProcessTreeSampler(unittest.TestCase):
    def test_surviving_grandchild_remains_tracked_after_root_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ready = directory / "ready.txt"
            child_ready = directory / "child-ready.txt"
            release = directory / "release.txt"
            child_script = directory / "child.py"
            grandchild = directory / "grandchild.py"
            root_script = directory / "root.py"
            grandchild.write_text(
                "import os,pathlib,sys,time\n"
                "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8')\n"
                "data=bytearray(8*1024*1024)\n"
                "time.sleep(10)\n",
                encoding="utf-8",
            )
            child_script.write_text(
                "import os,pathlib,subprocess,sys,time\n"
                "pathlib.Path(sys.argv[3]).write_text(str(os.getpid()), encoding='utf-8')\n"
                "subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])\n"
                "release=pathlib.Path(sys.argv[4])\n"
                "while not release.exists(): time.sleep(0.01)\n",
                encoding="utf-8",
            )
            root_script.write_text(
                "import pathlib,subprocess,sys,time\n"
                "subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]])\n"
                "release=pathlib.Path(sys.argv[5])\n"
                "while not release.exists(): time.sleep(0.01)\n",
                encoding="utf-8",
            )
            root = subprocess.Popen(
                [
                    sys.executable,
                    str(root_script),
                    str(child_script),
                    str(grandchild),
                    str(ready),
                    str(child_ready),
                    str(release),
                ]
            )
            try:
                deadline = time.monotonic() + 5
                while (
                    not ready.exists() or not child_ready.exists()
                ) and time.monotonic() < deadline:
                    time.sleep(0.01)
                child_pid = int(ready.read_text(encoding="utf-8"))
                intermediate_pid = int(child_ready.read_text(encoding="utf-8"))
                with WindowsProcessTreeSampler(root.pid) as sampler:
                    first = sampler.sample()
                    first_pids = {row.identity.pid for row in first.processes}
                    self.assertIn(intermediate_pid, first_pids)
                    self.assertIn(child_pid, first_pids)
                    release.touch()
                    root.wait(timeout=5)
                    surviving = None
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        candidate = sampler.sample()
                        candidate_pids = {
                            row.identity.pid for row in candidate.processes
                        }
                        if (
                            not candidate.root_alive
                            and candidate.tree_alive
                            and intermediate_pid not in candidate_pids
                            and child_pid in candidate_pids
                        ):
                            surviving = candidate
                            break
                        time.sleep(0.02)
                    self.assertIsNotNone(surviving)
                    assert surviving is not None
                    self.assertIn(
                        child_pid,
                        {row.identity.pid for row in surviving.processes},
                    )
                    self.assertIn(child_pid, sampler.terminate_tree())
            finally:
                if root.poll() is None:
                    root.kill()
                root.wait(timeout=5)

    def test_live_descendant_contributes_to_aggregate_working_set(self) -> None:
        child_code = (
            "import os,time; "
            "data=bytearray(8*1024*1024); data[::4096]=b'x'*(len(data)//4096); "
            "print(os.getpid(),flush=True); time.sleep(1)"
        )
        with WindowsProcessTreeSampler(os.getpid()) as sampler:
            child = subprocess.Popen(
                [sys.executable, "-c", child_code],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                assert child.stdout is not None
                worker_pid = int(child.stdout.readline())
                sample = sampler.sample()
            finally:
                if child.stdout is not None:
                    child.stdout.close()
                child.wait(timeout=5)

        by_pid = {
            process.identity.pid: process.working_set_bytes
            for process in sample.processes
        }
        self.assertIn(os.getpid(), by_pid)
        self.assertIn(worker_pid, by_pid)
        self.assertGreaterEqual(
            sample.aggregate_working_set_bytes,
            by_pid[os.getpid()] + by_pid[worker_pid],
        )

    def test_live_query_failure_is_invalidating_metadata(self) -> None:
        with WindowsProcessTreeSampler(os.getpid()) as sampler:
            with mock.patch.object(
                sampler._api,
                "working_set",
                side_effect=WindowsCallError("GetProcessMemoryInfo", 5),
            ):
                sample = sampler.sample()

        own_failures = [
            failure
            for failure in sample.failures
            if failure.kind == LIVE_PROCESS_QUERY_FAILED and failure.pid == os.getpid()
        ]
        self.assertEqual(len(own_failures), 1)
        self.assertEqual(own_failures[0].winerror, 5)
        self.assertFalse(sample.valid)

    def test_exit_between_snapshot_and_working_set_is_reported_nonfatally(self) -> None:
        with WindowsProcessTreeSampler(os.getpid()) as sampler:
            with (
                mock.patch.object(
                    sampler._api,
                    "working_set",
                    side_effect=WindowsCallError("GetProcessMemoryInfo", 87),
                ),
                mock.patch.object(
                    sampler._api,
                    "is_alive",
                    side_effect=(True, True, False, False),
                ),
            ):
                sample = sampler.sample()

        races = [
            failure
            for failure in sample.failures
            if failure.kind == PROCESS_EXITED_DURING_SAMPLE
        ]
        self.assertEqual(len(races), 1)
        self.assertFalse(races[0].fatal)
        self.assertTrue(sample.valid)

    def test_live_self_sample_reports_current_working_set_and_system_memory(
        self,
    ) -> None:
        with WindowsProcessTreeSampler(os.getpid()) as sampler:
            sample = sampler.sample()

        own_measurements = [
            process
            for process in sample.processes
            if process.identity.pid == os.getpid()
        ]
        self.assertEqual(len(own_measurements), 1)
        self.assertGreater(own_measurements[0].working_set_bytes, 0)
        self.assertGreaterEqual(
            sample.aggregate_working_set_bytes, own_measurements[0].working_set_bytes
        )
        self.assertGreater(sample.system_memory.physical_total_bytes, 0)
        self.assertGreater(sample.system_memory.physical_available_bytes, 0)
        self.assertGreater(
            sample.system_memory.commit_limit_bytes,
            sample.system_memory.commit_total_bytes,
        )
        self.assertNotIn(
            LIVE_PROCESS_QUERY_FAILED, {failure.kind for failure in sample.failures}
        )
        self.assertEqual(sampler.sample_starts_ns, (sample.started_ns,))


if __name__ == "__main__":
    unittest.main()

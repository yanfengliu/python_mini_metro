"""Source provenance and Windows process supervision for RL resource profiles."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import queue
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rl.windows_resources import (
    DEFAULT_MAXIMUM_TIMING_NS,
    DEFAULT_SAMPLE_INTERVAL_NS,
    WindowsProcessTreeSampler,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SCHEMA = "mini-metro-history-resource-sample-v1"
SUPERVISOR_SCHEMA = "mini-metro-history-profile-supervisor-v1"
ALLOWED_UNTRACKED_PREFIX = ".agents/"
IGNORED_OUTPUT_PREFIXES = ("output/",)
DEFAULT_READY_TIMEOUT_SECONDS = 30.0

__all__ = (
    "analyze_status_records",
    "collect_source_state",
    "runtime_metadata",
    "sha256_file",
    "supervise_worker",
    "write_json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        document,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    )
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        temporary.write_text(f"{payload}\n", encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def analyze_status_records(records: tuple[str, ...]) -> dict[str, Any]:
    """Apply the preregistered cleanliness rule to porcelain-v1 records."""

    allowed = []
    unexpected = []
    for record in records:
        if record.startswith("?? ") and record[3:].replace("\\", "/").startswith(
            ALLOWED_UNTRACKED_PREFIX
        ):
            allowed.append(record[3:].replace("\\", "/"))
        else:
            unexpected.append(record)
    return {
        "allowedUntracked": sorted(allowed),
        "clean": not unexpected,
        "ignoredOutputPrefixes": list(IGNORED_OUTPUT_PREFIXES),
        "unexpected": unexpected,
    }


def collect_source_state(
    repo_root: Path = REPO_ROOT, *, require_clean: bool = True
) -> dict[str, Any]:
    git = ("git", "-c", f"safe.directory={repo_root.as_posix()}")
    status = subprocess.run(
        (*git, "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    records = tuple(row for row in status.stdout.split("\0") if row)
    state = analyze_status_records(records)
    commit = subprocess.run(
        (*git, "rev-parse", "HEAD"),
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    state["commit"] = commit
    if require_clean and not state["clean"]:
        raise RuntimeError(f"profile source tree is not clean: {state['unexpected']}")
    return state


def _sample_document(sample: Any) -> dict[str, Any]:
    return {"schema": SAMPLE_SCHEMA, **asdict(sample)}


def _readline_with_timeout(stream: Any, timeout_seconds: float) -> str:
    result: queue.Queue[str | BaseException] = queue.Queue(maxsize=1)

    def read() -> None:
        try:
            result.put(stream.readline())
        except BaseException as error:
            result.put(error)

    threading.Thread(target=read, daemon=True).start()
    try:
        value = result.get(timeout=timeout_seconds)
    except queue.Empty as error:
        raise RuntimeError(
            "worker did not reach the pre-import barrier in time"
        ) from error
    if isinstance(value, BaseException):
        raise value
    return value


def _drain_stream(stream: Any, chunks: list[str]) -> None:
    try:
        for chunk in iter(lambda: stream.read(8192), ""):
            chunks.append(chunk)
    except (OSError, ValueError):
        return


def _positive_timeout(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and value > 0
        and value != float("inf")
    )


def supervise_worker(
    command: tuple[str, ...],
    *,
    run_dir: Path,
    result_path: Path,
    working_directory: Path = REPO_ROOT,
    interval_ns: int = DEFAULT_SAMPLE_INTERVAL_NS,
    maximum_timing_ns: int = DEFAULT_MAXIMUM_TIMING_NS,
    ready_timeout_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Attach before worker imports, then sample its complete process lifetime."""

    if not _positive_timeout(ready_timeout_seconds):
        raise ValueError("ready_timeout_seconds must be positive and finite")
    run_dir.mkdir(parents=True, exist_ok=True)
    sample_path = run_dir / "resource-samples.jsonl"
    stdout_path = run_dir / "worker.stdout.log"
    stderr_path = run_dir / "worker.stderr.log"
    process = subprocess.Popen(
        command,
        cwd=working_directory,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    summaries: list[tuple[int, int]] = []
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    full_peak = 0
    min_physical_available: int | None = None
    max_commit_total = 0
    max_commit_limit = 0
    ready_line = ""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    stdout_thread: threading.Thread | None = None
    stderr_thread = threading.Thread(
        target=_drain_stream,
        args=(process.stderr, stderr_chunks),
        daemon=True,
    )
    stderr_thread.start()
    sampler: WindowsProcessTreeSampler | None = None
    try:
        sampler = WindowsProcessTreeSampler(
            process.pid,
            interval_ns=interval_ns,
            maximum_timing_ns=maximum_timing_ns,
        )
        with (
            sampler,
            sample_path.open("w", encoding="utf-8", newline="\n") as samples,
        ):

            def record_sample() -> Any:
                nonlocal full_peak, min_physical_available
                nonlocal max_commit_total, max_commit_limit
                sample = sampler.sample()
                samples.write(
                    json.dumps(
                        _sample_document(sample),
                        allow_nan=False,
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    + "\n"
                )
                samples.flush()
                summaries.append(
                    (sample.started_ns, sample.aggregate_working_set_bytes)
                )
                full_peak = max(full_peak, sample.aggregate_working_set_bytes)
                available = sample.system_memory.physical_available_bytes
                if available > 0:
                    min_physical_available = (
                        available
                        if min_physical_available is None
                        else min(min_physical_available, available)
                    )
                max_commit_total = max(
                    max_commit_total, sample.system_memory.commit_total_bytes
                )
                max_commit_limit = max(
                    max_commit_limit, sample.system_memory.commit_limit_bytes
                )
                for failure in sample.failures:
                    target = failures if failure.fatal else warnings
                    target.append(asdict(failure))
                return sample

            try:
                sample = record_sample()
                ready_line = _readline_with_timeout(
                    process.stdout, ready_timeout_seconds
                )
                ready = json.loads(ready_line)
                worker_pid = ready.get("pid") if ready.get("event") == "ready" else None
                if isinstance(worker_pid, bool) or not isinstance(worker_pid, int):
                    raise RuntimeError(
                        f"worker emitted invalid ready record: {ready!r}"
                    )
                stdout_thread = threading.Thread(
                    target=_drain_stream,
                    args=(process.stdout, stdout_chunks),
                    daemon=True,
                )
                stdout_thread.start()
                sample = record_sample()
                sampled_pids = {item.identity.pid for item in sample.processes}
                if worker_pid not in sampled_pids:
                    raise RuntimeError(
                        "ready PID is not the launcher or a sampled descendant: "
                        f"launcher={process.pid}, worker={worker_pid}, "
                        f"sampled={sorted(sampled_pids)}"
                    )
                process.stdin.write("START\n")
                process.stdin.flush()
                process.stdin.close()
                process.stdin = None
                while True:
                    if process.poll() is not None and not sample.tree_alive:
                        break
                    time.sleep(sampler.sleep_seconds())
                    sample = record_sample()
            except BaseException:
                try:
                    sampler.terminate_tree()
                except BaseException:
                    pass
                raise
        process.wait(timeout=5)
    except BaseException:
        if process.stdin is not None:
            process.stdin.close()
            process.stdin = None
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        for stream in (process.stdout, process.stderr):
            stream.close()
        if stdout_thread is not None:
            stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        stdout_path.write_text(
            ready_line + "".join(stdout_chunks), encoding="utf-8", newline="\n"
        )
        stderr_path.write_text("".join(stderr_chunks), encoding="utf-8", newline="\n")
        raise
    if stdout_thread is not None:
        stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    if (
        stdout_thread is not None and stdout_thread.is_alive()
    ) or stderr_thread.is_alive():
        failures.append({"kind": "worker-log-drain-timeout"})
    stdout_path.write_text(
        ready_line + "".join(stdout_chunks), encoding="utf-8", newline="\n"
    )
    stderr_path.write_text("".join(stderr_chunks), encoding="utf-8", newline="\n")
    process.stdout.close()
    process.stderr.close()
    worker_result = None
    if result_path.is_file():
        try:
            worker_result = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            failures.append({"kind": "worker-result-invalid", "error": str(error)})
    else:
        failures.append({"kind": "worker-result-missing"})
    if process.returncode != 0:
        failures.append({"kind": "worker-exit-nonzero", "exitCode": process.returncode})

    if worker_result is not None and not isinstance(worker_result, dict):
        failures.append(
            {"kind": "worker-result-invalid", "error": "root must be an object"}
        )
        worker_result = None
    measured_peak = 0
    if worker_result is not None:
        window = worker_result.get("measurementWindow", {})
        start = window.get("startPerfCounterNs")
        end = window.get("endPerfCounterNs")
        if isinstance(start, int) and isinstance(end, int) and 0 < start < end:
            measured_peak = max(
                (
                    working_set
                    for timestamp, working_set in summaries
                    if start <= timestamp <= end
                ),
                default=0,
            )
        if measured_peak <= 0:
            failures.append({"kind": "measured-window-unsampled"})
    starts = [timestamp for timestamp, _working_set in summaries]
    gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
    return {
        "command": list(command),
        "exitCode": process.returncode,
        "failures": failures,
        "fullLifecyclePeakWorkingSetBytes": full_peak,
        "maxAcquisitionDurationNs": max(sampler.acquisition_durations_ns, default=0),
        "maxCommitLimitBytes": max_commit_limit,
        "maxCommitTotalBytes": max_commit_total,
        "maxSampleGapNs": max(gaps, default=0),
        "measuredPeakWorkingSetBytes": measured_peak,
        "minPhysicalAvailableBytes": min_physical_available,
        "maximumTimingNs": maximum_timing_ns,
        "launcherPid": process.pid,
        "readyTimeoutSeconds": ready_timeout_seconds,
        "sampleIntervalNs": interval_ns,
        "sampleCount": len(summaries),
        "sampleSha256": sha256_file(sample_path),
        "schema": SUPERVISOR_SCHEMA,
        "stderrSha256": sha256_file(stderr_path),
        "stdoutSha256": sha256_file(stdout_path),
        "valid": not failures,
        "warnings": warnings,
        "workerPid": worker_pid,
        "workerResult": worker_result,
    }


def runtime_metadata() -> dict[str, Any]:
    packages = ("numpy", "pygame-ce", "sb3-contrib", "stable-baselines3", "torch")
    versions = {name: importlib.metadata.version(name) for name in packages}
    cpu = platform.processor()
    if sys.platform == "win32":
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as key:
            cpu = str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    return {
        "cpu": cpu,
        "logicalCpuCount": __import__("os").cpu_count(),
        "platform": platform.platform(),
        "python": sys.version,
        "versions": versions,
    }

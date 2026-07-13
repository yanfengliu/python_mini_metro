"""Dependency-free Windows process-tree working-set sampling."""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from rl.windows_api import (
    ERROR_INVALID_PARAMETER,
    SystemMemory,
    WindowsApi,
    WindowsCallError,
)

DEFAULT_SAMPLE_INTERVAL_NS = 50_000_000
DEFAULT_MAXIMUM_TIMING_NS = 100_000_000
LIVE_PROCESS_QUERY_FAILED = "live-process-query-failed"
SAMPLE_GAP_EXCEEDED = "sample-gap-exceeded"
ACQUISITION_DURATION_EXCEEDED = "acquisition-duration-exceeded"
PROCESS_DISCOVERY_FAILED = "process-discovery-failed"
SYSTEM_MEMORY_QUERY_FAILED = "system-memory-query-failed"
PROCESS_EXITED_DURING_SAMPLE = "process-exited-during-sample"


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    creation_time: int


@dataclass(frozen=True, slots=True)
class ProcessLifetime:
    pid: int
    creation_time: int
    exit_time: int | None = None


@dataclass(frozen=True, slots=True)
class ProcessRecord:
    pid: int
    parent_pid: int
    creation_time: int


@dataclass(frozen=True, slots=True)
class ProcessMeasurement:
    identity: ProcessIdentity
    working_set_bytes: int


@dataclass(frozen=True, slots=True)
class ResourceFailure:
    kind: str
    sample_index: int | None = None
    pid: int | None = None
    winerror: int | None = None
    observed_ns: int | None = None
    limit_ns: int | None = None
    fatal: bool = True


@dataclass(frozen=True, slots=True)
class ResourceSample:
    index: int
    started_ns: int
    finished_ns: int
    processes: tuple[ProcessMeasurement, ...]
    aggregate_working_set_bytes: int
    system_memory: SystemMemory
    failures: tuple[ResourceFailure, ...]
    root_alive: bool
    tree_alive: bool

    @property
    def acquisition_duration_ns(self) -> int:
        return self.finished_ns - self.started_ns

    @property
    def valid(self) -> bool:
        return not any(failure.fatal for failure in self.failures)


def absolute_deadline_ns(start_ns: int, sample_index: int, interval_ns: int) -> int:
    """Return an absolute cadence deadline without accumulating sample duration."""
    if sample_index < 0 or interval_ns <= 0:
        raise ValueError("sample index must be non-negative and interval positive")
    return start_ns + sample_index * interval_ns


def sleep_until_deadline_seconds(deadline_ns: int, now_ns: int) -> float:
    return max(0, deadline_ns - now_ns) / 1_000_000_000


def timing_failures(
    *,
    sample_starts_ns: Sequence[int],
    acquisition_durations_ns: Sequence[int],
    maximum_ns: int = DEFAULT_MAXIMUM_TIMING_NS,
) -> tuple[ResourceFailure, ...]:
    if maximum_ns <= 0:
        raise ValueError("maximum_ns must be positive")
    if len(sample_starts_ns) != len(acquisition_durations_ns):
        raise ValueError("sample timestamps and durations must have equal lengths")
    failures = [
        ResourceFailure(
            SAMPLE_GAP_EXCEEDED, index, observed_ns=gap, limit_ns=maximum_ns
        )
        for index, gap in enumerate(
            (b - a for a, b in zip(sample_starts_ns, sample_starts_ns[1:])), start=1
        )
        if gap > maximum_ns
    ]
    failures.extend(
        ResourceFailure(
            ACQUISITION_DURATION_EXCEEDED,
            index,
            observed_ns=duration,
            limit_ns=maximum_ns,
        )
        for index, duration in enumerate(acquisition_durations_ns)
        if duration > maximum_ns
    )
    return tuple(failures)


def _within_lifetime(creation: int, parent: ProcessLifetime) -> bool:
    return parent.creation_time <= creation and (
        parent.exit_time is None or creation <= parent.exit_time
    )


def discover_descendants(
    rows: Iterable[ProcessRecord], known: Iterable[ProcessLifetime]
) -> tuple[ProcessRecord, ...]:
    """Resolve rows whose creation falls within a known parent's lifetime."""
    remaining = sorted(rows, key=lambda row: (row.creation_time, row.pid))
    lifetimes = list(known)
    identities = {(item.pid, item.creation_time) for item in lifetimes}
    discovered: list[ProcessRecord] = []
    changed = True
    while changed:
        changed = False
        for row in tuple(remaining):
            identity = (row.pid, row.creation_time)
            if identity in identities:
                remaining.remove(row)
            elif any(
                parent.pid == row.parent_pid
                and _within_lifetime(row.creation_time, parent)
                for parent in lifetimes
            ):
                discovered.append(row)
                lifetimes.append(ProcessLifetime(row.pid, row.creation_time))
                identities.add(identity)
                remaining.remove(row)
                changed = True
    return tuple(discovered)


@dataclass(slots=True)
class _Tracked:
    identity: ProcessIdentity
    handle: object
    exit_time: int | None = None

    def lifetime(self) -> ProcessLifetime:
        return ProcessLifetime(
            self.identity.pid, self.identity.creation_time, self.exit_time
        )


class WindowsProcessTreeSampler:
    """Retain process identities and sample current aggregate tree working set."""

    def __init__(
        self,
        root_pid: int,
        *,
        interval_ns: int = DEFAULT_SAMPLE_INTERVAL_NS,
        maximum_timing_ns: int = DEFAULT_MAXIMUM_TIMING_NS,
    ) -> None:
        if root_pid <= 0 or interval_ns <= 0 or maximum_timing_ns <= 0:
            raise ValueError("PID and timing values must be positive")
        self.root_pid = root_pid
        self.interval_ns = interval_ns
        self.maximum_timing_ns = maximum_timing_ns
        self._api = WindowsApi()
        handle, creation = self._api.open_process(root_pid)
        root = ProcessIdentity(root_pid, creation)
        self._root = root
        self._tracked = {root: _Tracked(root, handle)}
        self._starts: list[int] = []
        self._durations: list[int] = []
        self._failures: list[ResourceFailure] = []
        self._closed = False

    @property
    def sample_starts_ns(self) -> tuple[int, ...]:
        return tuple(self._starts)

    @property
    def acquisition_durations_ns(self) -> tuple[int, ...]:
        return tuple(self._durations)

    @property
    def failures(self) -> tuple[ResourceFailure, ...]:
        return tuple(self._failures)

    @property
    def next_deadline_ns(self) -> int | None:
        if not self._starts:
            return None
        return absolute_deadline_ns(
            self._starts[0], len(self._starts), self.interval_ns
        )

    def sleep_seconds(self, now_ns: int | None = None) -> float:
        if self.next_deadline_ns is None:
            return 0.0
        return sleep_until_deadline_seconds(
            self.next_deadline_ns,
            time.perf_counter_ns() if now_ns is None else now_ns,
        )

    def _failure(
        self, kind: str, index: int, error: WindowsCallError, pid: int | None = None
    ) -> ResourceFailure:
        return ResourceFailure(kind, index, pid=pid, winerror=error.winerror)

    def _refresh(self, index: int, failures: list[ResourceFailure]) -> list[_Tracked]:
        live: list[_Tracked] = []
        for tracked in self._tracked.values():
            if tracked.exit_time is not None:
                continue
            try:
                alive = self._api.is_alive(tracked.handle)
                if not alive:
                    tracked.exit_time = self._api.process_times(tracked.handle)[1]
                else:
                    live.append(tracked)
            except WindowsCallError as error:
                failures.append(
                    self._failure(
                        LIVE_PROCESS_QUERY_FAILED, index, error, tracked.identity.pid
                    )
                )
                live.append(tracked)
        return live

    def _discover(
        self, rows: tuple[tuple[int, int], ...], index: int
    ) -> list[ResourceFailure]:
        failures: list[ResourceFailure] = []
        attempted: set[tuple[int, int]] = set()
        changed = True
        while changed:
            changed = False
            parent_pids = {item.identity.pid for item in self._tracked.values()}
            live_pids = {
                item.identity.pid
                for item in self._tracked.values()
                if item.exit_time is None
            }
            for pid, parent_pid in rows:
                pair = (pid, parent_pid)
                if pair in attempted or parent_pid not in parent_pids:
                    continue
                if pid in live_pids:
                    attempted.add(pair)
                    continue
                attempted.add(pair)
                try:
                    handle, creation = self._api.open_process(pid)
                except WindowsCallError as error:
                    if error.winerror != ERROR_INVALID_PARAMETER:
                        failures.append(
                            self._failure(LIVE_PROCESS_QUERY_FAILED, index, error, pid)
                        )
                    continue
                identity = ProcessIdentity(pid, creation)
                parents = (
                    item.lifetime()
                    for item in self._tracked.values()
                    if item.identity.pid == parent_pid
                )
                if identity in self._tracked or not any(
                    _within_lifetime(creation, parent) for parent in parents
                ):
                    self._api.close(handle)
                    continue
                self._tracked[identity] = _Tracked(identity, handle)
                changed = True
        return failures

    def sample(self) -> ResourceSample:
        if self._closed:
            raise RuntimeError("sampler is closed")
        index = len(self._starts)
        started = time.perf_counter_ns()
        failures: list[ResourceFailure] = []
        if (
            self._starts
            and (gap := started - self._starts[-1]) > self.maximum_timing_ns
        ):
            failures.append(
                ResourceFailure(
                    SAMPLE_GAP_EXCEEDED,
                    index,
                    observed_ns=gap,
                    limit_ns=self.maximum_timing_ns,
                )
            )
        self._starts.append(started)
        try:
            rows = self._api.snapshot()
        except WindowsCallError as error:
            rows = ()
            failures.append(self._failure(PROCESS_DISCOVERY_FAILED, index, error))
        self._refresh(index, failures)
        failures.extend(self._discover(rows, index))
        measurements: list[ProcessMeasurement] = []
        for tracked in self._refresh(index, failures):
            try:
                measurements.append(
                    ProcessMeasurement(
                        tracked.identity, self._api.working_set(tracked.handle)
                    )
                )
            except WindowsCallError as error:
                try:
                    alive = self._api.is_alive(tracked.handle)
                except WindowsCallError:
                    alive = True
                if alive:
                    failures.append(
                        self._failure(
                            LIVE_PROCESS_QUERY_FAILED,
                            index,
                            error,
                            tracked.identity.pid,
                        )
                    )
                else:
                    failures.append(
                        ResourceFailure(
                            PROCESS_EXITED_DURING_SAMPLE,
                            index,
                            pid=tracked.identity.pid,
                            fatal=False,
                        )
                    )
        try:
            system = self._api.system_memory()
        except WindowsCallError as error:
            system = SystemMemory(0, 0, 0, 0)
            failures.append(self._failure(SYSTEM_MEMORY_QUERY_FAILED, index, error))
        finished = time.perf_counter_ns()
        duration = finished - started
        self._durations.append(duration)
        if duration > self.maximum_timing_ns:
            failures.append(
                ResourceFailure(
                    ACQUISITION_DURATION_EXCEEDED,
                    index,
                    observed_ns=duration,
                    limit_ns=self.maximum_timing_ns,
                )
            )
        live = self._refresh(index, failures)
        self._failures.extend(failures)
        processes = tuple(sorted(measurements, key=lambda item: item.identity.pid))
        return ResourceSample(
            index,
            started,
            finished,
            processes,
            sum(item.working_set_bytes for item in processes),
            system,
            tuple(failures),
            any(item.identity == self._root for item in live),
            bool(live),
        )

    def close(self) -> None:
        if self._closed:
            return
        first_error: BaseException | None = None
        for tracked in self._tracked.values():
            try:
                self._api.close(tracked.handle)
            except BaseException as error:
                first_error = first_error or error
        self._closed = True
        if first_error:
            raise first_error

    def terminate_tree(self, exit_code: int = 1) -> tuple[int, ...]:
        """Terminate live tracked descendants before their launcher."""

        if self._closed:
            raise RuntimeError("sampler is closed")
        terminated = []
        first_error: BaseException | None = None
        tracked = sorted(
            self._tracked.values(),
            key=lambda item: item.identity.creation_time,
            reverse=True,
        )
        for item in tracked:
            try:
                if item.exit_time is None and self._api.is_alive(item.handle):
                    self._api.terminate(item.handle, exit_code)
                    terminated.append(item.identity.pid)
            except BaseException as error:
                first_error = first_error or error
        if first_error:
            raise first_error
        return tuple(terminated)

    def __enter__(self) -> WindowsProcessTreeSampler:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

# Initial review

No plan-breaking issue found. A dependency-free Toolhelp32 + PSAPI sampler is viable at ≤100 ms, with two important integrity rules:

- Sum current `WorkingSetSize` across the live tree at each sample; never sum per-process `PeakWorkingSetSize`.
- Invalidate a repeat if the observed sample-start gap exceeds 100 ms or a live descendant cannot be queried. Otherwise memory could be silently undercounted.

Tested locally on Python 3.13.10 x64:

- `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS=0x2, 0)` + `Process32FirstW`/`Process32NextW`
- `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION=0x1000 | SYNCHRONIZE=0x00100000, ...)`
- `GetProcessTimes` for `(PID, creation FILETIME)` identity
- `WaitForSingleObject(handle, 0)` using `WAIT_OBJECT_0=0`, `WAIT_TIMEOUT=0x102`
- `GetProcessMemoryInfo` with `PROCESS_MEMORY_COUNTERS.WorkingSetSize`
- `GetPerformanceInfo` for system physical and commit metadata
- `CloseHandle` for every snapshot/process handle

Verified ctypes x64 ABI sizes:

- `PROCESSENTRY32W`: 568 bytes
- `PROCESS_MEMORY_COUNTERS`: 72 bytes
- `PERFORMANCE_INFORMATION`: 104 bytes
- `MEMORYSTATUSEX`: 64 bytes

Live measurements:

- 348-process Toolhelp snapshot: median 6.07 ms, max 10.35 ms over 50 calls.
- A 25 ms sampler tracking a root and 64 MiB child allocation completed 56 samples, max start gap 26.22 ms, zero query errors, and measured a 161,685,504-byte aggregate peak.
- Current machine snapshot: 68,423,581,696 bytes physical RAM, 44,671,545,344 available; system commit 28,095,094,784 / 72,718,548,992 bytes. These are current system-wide values, not benchmark results.

Recommended algorithm:

1. Launch a lightweight benchmark worker that blocks on a supervisor handshake. Open its root handle and record creation time before releasing it; this avoids missing startup allocation.
2. Retain handles for every accepted descendant and identify processes by `(PID, creation_time)`, not PID alone.
3. Each sample:
   - Timestamp with `perf_counter_ns`.
   - Snapshot `(pid, ppid)`.
   - Refresh known-process liveness/exit times.
   - Discover descendants to a fixed point. Accept a candidate only when its creation time falls within a known parent identity’s lifetime. This rejects PID-reuse false attribution and still finds a surviving child after its parent exits.
   - Sum current WSS for all live accepted identities.
   - Capture `PhysicalAvailable`, `CommitTotal * PageSize`, and `CommitLimit * PageSize`.
   - Record acquisition duration, process count, individual query failures, and sample-start gap.
4. Schedule absolute 50 ms deadlines (`deadline += 50 ms`), not `sleep(50 ms)` after each sample.
5. After the root exits, continue until known descendants exit and one final snapshot finds no new valid descendants.
6. Fail the repeat on access denied, persistent query failure for a live process, worker/allocation failure, nonzero worker exit, or observed gap >100 ms. Treat a process exiting between snapshot and query as an expected race, but count/report it.

Pitfalls to document:

- Toolhelp is sampled, so a process born and dead entirely between samples can be missed; this is inherent in the declared sampled-instantaneous metric.
- WSS queries are sequential within a short acquisition window, not atomic. Report the maximum acquisition duration.
- Aggregate WSS double-counts shared pages across processes. That is acceptable for this preregistered comparative metric but is not unique physical RAM.
- `MEMORYSTATUSEX.ullTotalPageFile`/`ullAvailPageFile` can be constrained by the current process. Use `GetPerformanceInfo` for system-wide commit.
- `PROCESS_MEMORY_COUNTERS.PagefileUsage` is commit charge, not evidence that bytes were paged to disk. Do not claim absence or presence of paging.
- Do not use `STILL_ACTIVE` alone for liveness; an application can use exit code 259. Retained handles plus zero-time waits avoid that ambiguity.
- Set `argtypes`, `restype`, `use_last_error=True`, structure size fields, and compare the snapshot handle with `ctypes.c_void_p(-1).value`.

Deterministic test set:

- Pure ancestry closure: out-of-order root/child/grandchild; missing exited parent with surviving child; cycle protection.
- PID reuse: candidate created after historical parent exit is rejected.
- Aggregation: current WSS is summed, duplicate identities counted once, noncoincident lifetime peaks ignored.
- Error classification: access denied invalidates; vanished-after-snapshot is recorded but nonfatal; failed WSS on a still-live handle invalidates.
- Fake-clock scheduler: absolute 50 ms deadlines, overruns, and exact >100 ms invalidation.
- Lifecycle: root exits before child; final snapshot discovers a surviving last child.
- System metrics: page-count-to-byte conversion using `PageSize`.
- Windows integration: self-query and a handshake-controlled root/child allocation; skip off Windows.
- ABI assertions conditional on pointer width: x64 sizes above; x86 expected `PROCESSENTRY32W=556`, counters `40`, performance info `56`.

Verified against Microsoft’s [Toolhelp snapshot](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot), [PROCESSENTRY32](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32), [GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo), [process counters](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters), [process access rights](https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights), [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes), and [GetPerformanceInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getperformanceinfo) contracts.

# First re-review

NOT APPROVED — two substantive measurement/provenance defects remain:

1. Plan-breaking cleanliness rule: the live repo permanently contains untracked `.agents/`, so “reject a dirty tree” is impossible if implemented as normal `git status --porcelain`. Define the exact rule: require no staged or tracked modifications and reject untracked runtime-affecting files, while explicitly allowlisting `.agents/**` and ignored benchmark outputs. Record the allowlist and cleanliness result in every worker artifact.

2. The sampler records acquisition duration but only invalidates on sample-start gaps over 100 ms. A final or isolated sample could take over 100 ms without producing a subsequent excessive gap, making the “instantaneous” aggregate span too wide. Also invalidate when any acquisition duration exceeds 100 ms.

The remaining Windows API, cadence, PID-reuse, WSS semantics, lifecycle, bounded-evidence, source-commit, and fingerprint clauses are sound.

# Final re-review

APPROVED. The corrected cleanliness allowlist and acquisition-duration invalidation resolve the remaining Windows measurement and provenance defects. No substantive issues remain.

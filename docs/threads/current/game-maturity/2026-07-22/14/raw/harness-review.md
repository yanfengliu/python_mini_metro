# Harness adversarial review — GM-07b:E locomotive-fleet stale-cache tolerance

Commit under review: `ab91ca4` (`fix: tolerate stale service cache in locomotive assign/queue/cancel [GM-07b:E]`)
Reviewer: independent harness lane (read live code + executed probes)
Verdict: **CLEAN** — no BLOCKER/MAJOR/MINOR findings. Two NIT-level observations, both pre-existing and non-blocking.

## What the change does (verified against live code)

`git diff HEAD~1 -- src/ test/` threads the pre-existing opt-in `allow_stale_bound=True` through the locomotive fleet-management guards, exactly mirroring the carriage twin (abe36fe / GM-07b:D):

- New `_fleet_state_is_canonical(host)` = `_queue_state_is_canonical(host, allow_stale_bound=True)` (`src/fleet_management.py:160-172`). Substituted at the five user-op read/postcondition sites: `can_assign` precondition (`:220`), `assign` postcondition (`:280`), `unassignment_candidate` (`:303`), `cancel_candidate` (`:362`), `queued_count` (`:456`).
- `_detach` gains `allow_stale_bound` kwarg (default False), threaded into both its precondition `_queue_state_is_canonical(...)` (`:477`) and its postcondition `carriage_state_is_canonical(host, allow_stale_bound=...)` (`:519`). The queue fast path passes `True` (`:342`); `settle` calls `_detach` with the default (strict).
- `reconcile_queue_transition` gains `allow_stale_bound` (`src/fleet_queue_transition.py:49`), threaded ONLY to the whole-fleet postcondition `queue_state_is_canonical(host, allow_stale_bound=...)` (`:72`). The touched metro's own `service_cache_is_canonical(host, metro, allow_unbound=False)` (`:70-71`) stays strict. queue and cancel pass `True` (`fleet_management.py:352,396`).
- `QueueStateCheck` type widened `Callable[[Any], bool]` → `Callable[..., bool]` (annotation only; no runtime effect).

The relaxation reduces to exactly one behavioral axis: `service_cache_is_canonical`'s `allow_stale_bound` branch (`src/fleet_validation.py:122-129`), which accepts a well-formed bound action `(kind, passenger)` with boarding-invariant timers **iff** `passenger` is in the global registry (`service_action_passenger_is_live`, `:56-69`). All other structural checks remain.

## Regression suites (executed)

- `test.test_gm06c_carriage_stale_sibling` — 9/9 OK.
- `test.test_gm06d_cancel_unassignment test.test_gm06d_occupied_return test.test_gm06d_reconcile` — 40/40 OK.
- `unittest discover -p "test_gm0*.py"` — **618/618 OK**.
- `*checkpoint*` — 47/47 OK; `test_recursive*` — 41/41 OK.
- `ruff check` + `ruff format --check` on all three changed files — clean.

## Refutation targets — results

### Target 1 — TOUCHED METRO STRICT — PASS (probe + code)
The touched metro is validated strictly at its own site in every path:
- assign: the new metro is off-station; `_assignment_initialized` (strict, `:194-206`) plus `service_cache_is_canonical(...allow_unbound=False)` on a `station is None` metro reduces to `action is None and zero_timing` — `allow_stale_bound` is irrelevant to it.
- queue/cancel reconcile: `fleet_queue_transition.py:70-71` ANDs the strict touched-metro check before commit.
Probe `probe123.py` (committed cancel) and `probe_queue_reconcile.py` (committed queue-reconcile with an occupied at-station candidate) both show `service_cache_is_canonical(mediator, touched, allow_unbound=False) == True` after commit. No reachable state found where an op commits with a stale/oracle-mismatched TOUCHED metro. The queue fast path *removes* the touched metro entirely, so "touched left stale" is N/A there.

### Target 2 — UNRELATED SIBLING PRESERVED ON COMMIT — PASS (probe + code)
After committed assign / cancel / queue-reconcile / queue-fast-path, the unrelated stale sibling's `_station_service_action` is the **same object identity** and still stale. Mechanism: for non-touched metros `transaction_state_matches` requires `getattr(metro,"_station_service_action",_MISSING) is service` (strict identity, `carriage_transaction_snapshot.py:443-448`); only `allow_service_change=metro` (the touched/removed metro) is exempt. assign never reconciles (`entity/path.py:161-166` `add_metro` mutates only the new metro). Probes `probe123.py`, `probe_queue_reconcile.py`, `probe46.py` (T6a) all confirm `sibling._station_service_action is stale_cache`.

### Target 3 — SIBLING PRESERVED ON ROLLBACK — PASS (probe)
Forced mid-transaction failures via `monkeypatch mediator._reconcile_station_service -> raise`:
- Cancel reconcile rollback (`probe123.py` T3a): `cancel` returns False; the touched metro's flag, cache identity, and timers are restored verbatim; the sibling cache identity and staleness are unchanged.
- Queue reconcile rollback (`probe_queue_reconcile.py`, occupied candidate): `queue` returns False; candidate flag/cache/timers restored; sibling verbatim.
- Assign rollback (`probe123.py` T3c): calling `_fleet.assign` with a factory that returns an uninitialized object fails the postcondition → both fleet lists restored to prior identity tuples; sibling verbatim.

### Target 4 — SETTLE / REMOVAL STAY STRICT — PASS (probe + code)
- `settle` uses strict `_queue_state_is_canonical(host)` (`:427`) and calls `_detach(host, path, metro)` with the default (strict) `allow_stale_bound=False`. `probe46.py` T4a: `settle()` returns 0 and leaves a queued-empty-at-station candidate in place while a sibling is stale. T4b: direct `_detach(default)` returns False; `_detach(allow_stale_bound=True)` returns True on the identical state — confirming the flag, not leakage.
- `remove_path` uses strict `_queue_state_is_canonical(host)` (`path_lifecycle.py:164`). T4c: `mediator.remove_path(path)` is a clean no-op in the stale window (paths unchanged, sibling verbatim). The relaxation did NOT leak into either.

### Target 5 — REAL CORRUPTION STILL REJECTED — PASS (probe), highest-value target
`probe5_corruption.py` constructs eight non-legitimate cache shapes on a sibling and confirms `carriage_state_is_canonical(host, allow_stale_bound=True)` AND `_queue_state_is_canonical(host, allow_stale_bound=True)` STILL return False, and `can_assign`/`can_queue`/`can_attach` all stay False, for each of:

| corrupt shape | rejected? |
|---|---|
| unknown action kind `("teleport", p)` | True |
| boarding progress < 0 | True |
| boarding progress >= interval | True |
| remaining != interval - progress | True |
| bound cache while off-station (`current_station=None`) | True |
| null cache with nonzero timers | True |
| `("board", ghost)` dangling (not in registry) | True |
| `("board", p)` where p removed from `host.passengers` | True |

All rejected. The dangling-passenger cases are caught precisely by `service_action_passenger_is_live` (`fleet_validation.py:129`); the timer/kind cases by the structural block at `:105-121`. **No corrupt shape passes the relaxed gate.** No HIGH finding.

### Target 6 — FAST-PATH PARTIAL COMMIT — PASS / NIT (pre-existing)
In `queue`, the empty-at-station fast path (`fleet_management.py:338-343`) sets the flag, clears the candidate's cache, calls `_detach(..., allow_stale_bound=True)`, and `return True` **unconditionally** (ignores `_detach`'s bool). Findings:
- This unconditional-True is byte-identical to HEAD~1 (`git show HEAD~1:src/fleet_management.py`): the only diff is the added `allow_stale_bound=True`. **Not introduced by this change.**
- In the pre-change code the fast path was *unreachable* in the stale window (candidate selection was strict → `None`), so the whole op no-opped cleanly. After the change the window is reachable and `_detach(allow_stale_bound=True)` **succeeds** (probe `probe46.py` T6a: metro removed, sibling verbatim). Forcing `_detach` to return False (T6b, monkeypatched) reproduces the pre-existing partial shape (flag set, cache cleared, metro not removed, returns True), but this is not reachable via the relaxation — the relaxed `_detach` is strictly *more* likely to succeed than the prior strict one. Net effect of the change on this path is a fix, not a regression.
- NIT (pre-existing, out of scope): the fast path discarding `_detach`'s return is a latent fragility independent of GM-07b:E.

### Target 7 — BROADER-THAN-INTENDED — PASS (probe + grep)
- `queued_count` relaxation feeds **only the UI badge path and tests**. `mediator.queued_locomotives_for_path` (`mediator.py:545`) is consumed solely by `test/` (grep-verified: `test_gm06d_*`). The on-screen badge in `ui/fleet_button.py:_queued_count` computes independently from raw metro flags and does NOT call the mediator method. The checkpoint reads the raw `is_unassignment_queued` via `metro_queue_state` (`recursive_checkpoint.py:189,366`), never `queued_count`. Probe `probe7.py` T7b: `canonical_checkpoint(env, schema_version=4)` succeeds inside the stale window (it already uses the fleet-wide `allow_stale_bound=True`, `recursive_checkpoint_carriages.py:164`) and encodes queued flags `[False, True]` from the raw attribute. So no checkpoint/save/observation value changes because of the `queued_count` relaxation. T7a confirms `queued_locomotives_for_path` now returns the real count (1) instead of a strict-gate 0.
- Multiple stale-but-live siblings: `allow_stale_bound` is per-metro and uncapped, so N>1 stale-but-live metros are tolerated. Probe `probe7.py` T7c builds two simultaneously-stale-but-live metros: the tolerant gate accepts, strict rejects, `assign` still commits, and BOTH siblings are preserved verbatim. This is the *same* fleet-wide structural contract the GM-07b:C checkpoint verifier already applies, each tolerated cache is structurally valid and references a live passenger, and every non-touched metro is pinned verbatim by `transaction_state_matches` — so N>1 is not harmful and is consistent with the established save/load tolerance. Not a finding.

## Consistency audit of the threading (code read)

Enumerated all five `_fleet_state_is_canonical` call-sites and both `allow_stale_bound=True` threads; every user-op path is uniformly relaxed (can_assign→assign postcondition; unassignment_candidate→fast `_detach`/reconcile; cancel_candidate→reconcile), while both automatic/lifecycle paths (`settle`, `remove_path`) remain uniformly strict. The touched-metro strict check is preserved at each mutation site. No half-relaxed path (relaxed precondition + strict postcondition or vice-versa) exists.

## Findings summary

| # | Severity | Status |
|---|---|---|
| Fast-path `queue` discards `_detach`'s bool return (returns True unconditionally) | NIT | Pre-existing (identical in HEAD~1); out of scope for GM-07b:E |
| `allow_stale_bound` per-metro tolerance is uncapped (N>1 stale-but-live tolerated) | NIT | By design; matches GM-07b:C checkpoint contract; non-harmful (probe-confirmed verbatim preservation) |

No BLOCKER / MAJOR / MINOR. The change is a faithful, correctly-scoped twin of the carriage fix: it fixes the reachable one-tick no-op for assign/queue/cancel, keeps the touched metro strict, preserves unrelated siblings verbatim on both commit and rollback, keeps settle and path-removal strict, and continues to reject all genuinely-corrupt cache shapes.

## Probe artifacts (scratchpad, not committed)
`probe5_corruption.py`, `probe123.py`, `probe_queue_reconcile.py`, `probe46.py`, `probe7.py` — all printed their PASS lines; key outputs quoted inline above.

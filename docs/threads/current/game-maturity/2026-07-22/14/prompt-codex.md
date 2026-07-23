You are a senior code reviewer. Flag bugs, security issues, and performance concerns. Do NOT modify files or propose patches. Only return findings, explanations, and suggestions in plain text. Be concise but effective: keep the reasoning, impact, and file/line evidence needed to act without preserving transcripts, command chatter, or repetitive detail. Only point out an issue if it is real and important. If there is no issue, say so instead of nit-picking.

You MUST read the live code in this repository to ground every claim — do not review from the diff alone. This is the reviewers-must-read directive from AGENTS.md. Read src/fleet_management.py, src/fleet_queue_transition.py, src/fleet_validation.py, src/carriage_transaction_snapshot.py, src/carriage_management.py, and test/test_gm06c_carriage_stale_sibling.py in full before reasoning. Verify each finding against the actual code. Also flag any process regressions, stale documentation, or missing validation you notice (per AGENTS.md Code review).

## Change under review (GM-07b:E)

This is the locomotive-fleet twin of a prior carriage fix (commit abe36fe, GM-07b:D). Background: when two Metros of one line stop at the same station, the live `move_passengers` loop walks metros in order, so a later sibling can consume an earlier metro's cached `('board', passenger)` target inside one tick, leaving that earlier metro holding a structurally valid but stale `_station_service_action` whose passenger is still live. This is a real, reachable state that ordinary multi-Metro play produces and GM-07b save/load persists verbatim (seed-9 reproduces it). The strict oracle-deriving `_queue_state_is_canonical` returns False for such a state.

The defect being fixed: `can_assign_locomotive`/`assign_locomotive`, `can_queue_locomotive_unassignment`/`queue_locomotive_unassignment`, `can_cancel_unassignment`/`cancel_unassignment`, and the `queued_locomotives_for_path` badge count all gated on the STRICT `_queue_state_is_canonical`, so they silently no-opped (or under-reported 0) on EVERY path during the one-tick self-healing window — even though a locomotive op is orthogonal to an unrelated metro's transient cache, and even with free locomotives or a genuinely queued metro.

The fix threads the pre-existing opt-in `allow_stale_bound` (already used by the checkpoint verifier and carriage guards) through the fleet-management guards:
- new helper `_fleet_state_is_canonical(host)` = `_queue_state_is_canonical(host, allow_stale_bound=True)`, used at can_assign, the assign ownership postcondition, unassignment_candidate, cancel_candidate, and queued_count.
- `_detach` gained an `allow_stale_bound` kw param (threaded to its gate and its `carriage_state_is_canonical` postcondition); the queue immediate-detach fast path passes True, but `settle` calls `_detach` WITHOUT it (stays strict).
- `reconcile_queue_transition` gained an `allow_stale_bound` kw param threaded ONLY to the whole-fleet `queue_state_is_canonical` postcondition; the touched metro's own `service_cache_is_canonical(host, metro, allow_unbound=False)` stays strict. queue and cancel both pass True.

## Anti-regression checklist — verify each holds in the LIVE code

1. THE TOUCHED METRO STAYS STRICT. assign's new metro is off-station (verify `service_cache_is_canonical` early-returns strictly for station=None regardless of allow_stale_bound, and `_assignment_initialized` pins it). reconcile_queue_transition still checks the touched metro with `allow_unbound=False` and NO allow_stale_bound. If a locomotive op could leave the metro it TOUCHED with a stale/oracle-mismatched cache, that is a real bug — find it.

2. SIBLING PRESERVED VERBATIM ON COMMIT. The only tolerated staleness must be an UNRELATED already-present metro. Confirm `transaction_state_matches` compares `_station_service_action` by identity (`is`) for every metro except `allow_service_change`, so an op that mutated an unrelated sibling's cache would be caught and rolled back. Confirm assign (which uses collection-identity checks, not transaction_state_matches) cannot touch any existing metro's cache.

3. SIBLING PRESERVED VERBATIM ON ROLLBACK. `restore_transaction_state` must restore every metro's `_station_service_action` from the snapshot, so a failed op leaves the sibling's stale cache exactly as it was.

4. SETTLE + PATH-LIFECYCLE STAY STRICT. `settle` must still call `_detach` without allow_stale_bound (default False) and gate on strict `_queue_state_is_canonical`. path_lifecycle.remove_path (src/path_lifecycle.py:~164) must stay strict. If the relaxation leaked into settle or removal, flag it.

5. REAL CORRUPTION STILL REJECTED. allow_stale_bound must NOT accept: unknown action kind, off-invariant boarding timers, a bound-while-off-station cache, a null-with-nonzero-timers cache, or a cache referencing a passenger NOT in the live registry (dangling). Verify `service_cache_is_canonical`/`service_action_passenger_is_live` still reject these under allow_stale_bound=True.

6. NO SERIALIZED-BYTE CHANGE. The claim is that no checkpoint/save/observation bytes change because those read the raw `is_unassignment_queued` flag, not `queued_count`, and the fix never changes flags — it only stops spurious no-ops. Assess whether making these ops SUCCEED where they previously no-opped could change any FROZEN fixture (v1-v5, save-v1) or the RL observation in a way the test suite would not catch.

7. FAST-PATH PARTIAL COMMIT. In `queue`, the fast path sets the queue flag, clears the target's cache/timers, then calls `_detach(..., allow_stale_bound=True)` and returns True unconditionally. Reason about whether relaxing `_detach` there can leave a partial/inconsistent state (flag set, cache cleared, but metro not removed) in any scenario, and whether that is worse than the prior no-op behavior.

8. TYPE/CONTRACT. `QueueStateCheck` changed from `Callable[[Any], bool]` to `Callable[..., bool]`. Confirm both call sites (queue, cancel) pass a callable that accepts the `allow_stale_bound` kwarg, and that `reconcile_queue_transition`'s default (False) keeps any other hypothetical caller strict.

Focus your effort on transactional safety (commit-around and rollback of the unrelated sibling), the touched-metro strictness, and any path where the relaxation is broader than "tolerate one unrelated stale-but-structural sibling." A stale sibling that is NOT structurally valid (dangling passenger, bad timers) getting through is the highest-severity class.

Begin your review with the literal token "===BEGIN-REVIEW===" on its own line and end with "===END-REVIEW===" on its own line. Do not emit those markers anywhere else in your output.

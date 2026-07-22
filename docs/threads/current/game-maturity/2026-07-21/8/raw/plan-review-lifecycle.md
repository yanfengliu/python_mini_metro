# GM-06d simulation timing / lifecycle review (verbatim)

Verdict: **the critical freeze-forever deadlock the plan's Case 1 could have introduced does NOT exist** — the oracle is structured to alight queued metros. However, **Case 4 (line-removal) and its Case 3 recovery story have two MAJOR holes**, plus several minor timing gaps.

## CONFIRMED correct against the code

**C1 — No queued-metro deadlock (the central risk).** `next_service_action` (`src/passenger_capacity.py:36-51`) evaluates unload candidates first and returns `DESTINATION`/`TRANSFER` *before* the `can_board_at_station` gate at line 41. The mediator gates only boarding on the queue flag (`src/mediator.py:630-631`, `:667-670`); `get_unloading_candidates_for_metro` (`:641-646`) is not queue-gated. `move_passengers` iterates all `host.metros` with no queue check (`src/passenger_flow.py:310`). Riders are not frozen aboard.

**C2 — Queued metro stops at every station so riders can alight.** `should_stop_at_next_station` returns True for a queued metro whenever a next station exists (`src/mediator.py:651-652`); confirmed by `test_queued_return_is_a_stop_override_not_a_phantom_service_action` (`test/test_gm06c_station_service.py:84-96`). A queued metro with nothing to alight departs normally (`src/entity/path.py:173-174`).

**C3 — Settle fires the same tick the metro empties, at the station.** `settle` runs in `mediator.increment_time` (`src/mediator.py:618`) after `move_passengers`; the just-emptied metro is still at its real station; predicate (`src/fleet_management.py:333-336`) matches same tick. "No new settlement rule required" is accurate.

**C4 — Immediate-detach fast path already gates on empty** (`src/fleet_management.py:368`, `:315-319`). Nit: that branch still resets service cache/timers for an occupied metro before the no-op detach — benign.

**C5 — Cancel un-queue needs only to clear the flag.** `move_passengers` calls `reconcile_service_action` first each iteration (`src/passenger_flow.py:317`), which zeroes `boarding_progress_ms` on any action change (`src/passenger_capacity.py:176-177`). Timing-safe.

**C6 — Reconcile-at-settle-seam adds no new determinism surface.** `settle` already invokes the oracle every tick through `_queue_state_is_canonical` → `carriage_state_is_canonical` → `service_cache_is_canonical` (`src/fleet_validation.py:100,193`).

## FINDINGS

### F1 — MAJOR — Case 4 alight can overflow station capacity → assertion / rider loss
`station_capacity = 12`; a metro holds up to 18 with two carriages; `add_passenger`/`move_passenger` assert `has_room()` (`src/entity/holder.py:69-80`); `remove_path` has no try/except or snapshot (`src/path_lifecycle.py:71-93`). Under `-O`, asserts strip and the station silently over-fills instead. The plan must state an overflow policy and where a rider goes when every candidate station is full.

### F2 — MAJOR — Case 3 reconcile cannot repair the realistic Case 4 partial failure; dropping an occupied dangling metro strands riders
The realistic failure (full-station assert) happens before any global-collection removal: metro still in both collections, button already detached (`src/path_lifecycle.py:77`), rider state half-migrated — none of reconcile's three repairs touch that; every fleet transition gated on `_queue_state_is_canonical` stays permanently inert. If reordered so global removal happens first, the dangling `path.metros` metro may still hold riders; reconcile must refuse to drop non-empty entries. Require `remove_path` to fully alight riders before any collection mutation, so the only reconcile-visible partial shape is an empty dangling metro.

### F3 — MINOR — Case 4 mid-segment alight on a padding segment has no station endpoints
`PaddingSegment` never sets `start_station`/`end_station` (`src/entity/padding_segment.py:10-21`, `src/entity/segment.py:18-19`); only `PathSegment` does (`src/entity/path_segment.py:39-40`). Derive the alight station from the adjacent path segment.

### F4 — MINOR — reconcile ordering vs settle
Settle is called from `mediator.increment_time` (`src/mediator.py:617-618`); reconcile must be placed there too and run **before** settle (and before the shared canonical gate), or recovery costs an extra tick.

### F5 — MINOR — reconcile repair #3 (stale service action) is largely redundant
Per-tick reconciliation already covers all `host.metros`; `remove_path` already clears the removed metro's cache (`src/path_lifecycle.py:85-88`). Scope repair #3 to metros absent from `host.metros` or drop it.

### F6 — MINOR — non-terminating return (livelock) and wait_ms
A rider aboard a queued metro whose only exit is a transfer to a permanently full station never alights (transfer needs `station.has_room()`, `src/passenger_capacity.py:39`) → the return never completes; state this conditionality. Also reset `passenger.wait_ms = 0` on removal-alight for parity with the transfer path (`src/passenger_flow.py:386`).

### F7 — MINOR — reconcile gated like settle skips pause/game-over
`settle` returns early when paused (`src/fleet_management.py:323`) and only runs when `transition_active` (`src/mediator.py:611-618`). A malformed state produced just before a pause would not be repaired until unpause and could be serialized by GM-07. Consider running reconcile unconditionally.

## Bottom line
Case 1 and Case 2 are timing-sound; the reconcile seam is determinism-safe. The real exposure is Case 4: unbounded station overflow on alight (F1) and a Case 3 recovery story that does not cover the realistic partial-failure shape (F2). Both must be resolved before implementation.

# GM-06d conservation review — REFUTATION REPORT (verbatim)

Verdict: The plan is **not** conservation-sound as written. Case 1 (occupied return) and Case 2 (cancellation) are essentially sound with minor caveats, but **Case 4 (line-removal rider cleanup) has a blocker** (station-capacity overflow on alight) and **Case 3 (reconcile) has major gaps** (can retire riders, and its repair scope does not cover the partial state Case 4 actually produces).

## BLOCKER

### B1 — Case 4: alighting onboard riders ignores station capacity; overflow raises mid-removal with no rollback, then cascades into rider loss
- Evidence: `Holder.add_passenger` hard-asserts room: `entity/holder.py:69-71` (`assert self.has_room()`), and `move_passenger` asserts `holder.has_room()` at `entity/holder.py:77-80`. Station capacity is `station_capacity = 12` (`config.py:24`). A single Metro's capacity is `_base_capacity(6) + Σ carriage.capacity` (`entity/metro.py:57-61`); with the two starting 6-seat carriages (D-023) a Metro can carry **up to 18**. `remove_path` has no try/except (`path_lifecycle.py:71-93`), nor does the Mediator facade (`mediator.py:461-462`), nor either caller (`input_coordinator.py:346` mouse; `:451-456` structured action).
- Failure scenario: Remove a line whose train at station S carries 12–18 riders while S already has ≥1 waiting passenger. Alighting them calls `add_passenger`/`move_passenger` → `assert self.has_room()` fails → uncaught `AssertionError`. Because there is no rollback, the loop has already (a) cleared the button (`path_lifecycle.py:77`), (b) removed earlier metros from `host.metros` (refunded), (c) moved some riders to stations, leaving a partial, non-canonical, button-detached line. On loops/short lines two metros can share a station and dump up to 36 onto a 12-cap station.
- Suggested fix: Decide an explicit capacity policy and make `remove_path` fail-closed or transactional. Options: (a) snapshot/rollback the whole `remove_path` like the fleet ops; (b) permit controlled station over-capacity via direct append; or (c) validate total incoming vs. free station room before any destructive mutation and reject/return.

## MAJOR

### M1 — Case 3: `reconcile` "drop dangling `path.metros` entry absent from global" can retire a Metro that still carries riders
Partial `remove_path` failure can leave a global-absent Metro still holding passengers; dropping that entry retires the Metro with its riders → rider loss/duplication. Reconcile must only drop **empty** global-absent path entries; `remove_path` must alight riders before removing from `host.metros`.

### M2 — Case 3: reconcile's scope (fleet-only) does not repair button/color/path state that a partial `remove_path` corrupts
A mid-loop raise leaves the button already detached (`path_lifecycle.py:77`) but `path` still in `host.paths`; reconcile as specified only touches queue flags/dangling metros/service-action → line left permanently inert (the exact outcome Case 3 claims to cure). Make `remove_path` transactional (preferred).

### M3 — Case 3: one-directional "trust global, discard path-side" ratifies real conservation bugs
If any real bug erroneously removes a Metro/consist from `host.metros`, reconcile finalizes that loss instead of surfacing the discrepancy. Prefer re-adding to global over discarding when path-side entry is non-empty; at minimum flag rather than silently ratify.

### M4 — Case 4: re-plan sweep only reaches riders that sit in a `station.passengers` list and have no travel plan
`iter_bulk_route_proposals` skips passengers with a plan (`route_planner.py:207-209`) and only iterates `station.passengers`. A removed-line rider whose plan's `next_path` is a surviving path is not cleared by `invalidate_travel_plans_for_path` (`path_lifecycle.py:104-107`), is no longer onboard, and is skipped → stuck. Fix: explicitly clear `host.travel_plans` for every alighted rider and add to a real `station.passengers` list.

### M5 — Case 4: existing public-contract tests directly assert the opposite behavior and must be rewritten (Mediator public API = high-risk)
`test/test_mediator_paths.py:23-35` and `test/test_path_lifecycle.py:103-162` assert onboard riders are removed after `remove_path`. Case 4 inverts both. Name these as conscious contract flips and route through the high-risk review path.

## MINOR

### m1 — Case 1: an onboard rider that can never alight on the queued line strands both rider and locomotive
A rider whose destination shape is not served by this line matches neither DESTINATION nor TRANSFER; onboard riders are never re-planned; `settle` never fires. New reachability introduced by widening candidate selection to occupied metros. Fix: force-alight any onboard rider whose next stop is unreachable at the current real station and re-plan it (reuse the Case 4 alight path).

### m2 — Case 2: cancellation cannot restore state "identical to never having queued" for an occupied metro queued at a station
`queue` clears `_station_service_action`/`stop_time_remaining_ms`/`boarding_progress_ms` when `_real_station` (`fleet_management.py:315-318`) regardless of occupancy; the destroyed `boarding_progress_ms` cannot be restored. Soften wording, or preserve service/timing for occupied metros (only clear on the empty immediate-detach fast path).

### m3 — Case 4: a rider dumped at a station of its own destination shape is silently removed without a delivery credit
The bulk iterator's `arrival` branch removes the rider but does not `record_delivery` (`route_planner.py:217-218`), unlike the true delivery path (`passenger_flow.py:372-378`). Acknowledge, or route at-destination riders through a crediting path.

## Claims CONFIRMED correct against the code
- Occupied queued metros are not force-emptied: boarding blocked (`mediator.py:630-631`,`:668-669`), still stop (`:651-652`), still unload destination/transfer (un-gated `passenger_flow.py:230-242`), settle only once empty (`fleet_management.py:322-344`).
- Availability accounting does not double-count a queued-but-assigned occupied metro; refund only on `_detach` from both collections (`fleet_management.py:386-387`).
- Whole-consist refund is via global-Metro removal, independent of whether riders are kept.
- `settle` runs after `move_passengers` in the same tick and only when not paused/game-over (`mediator.py:610-618`).
- Cancellation restoring `is_unassignment_queued=False` re-enables candidacy and boarding.

## Bottom line
Fix B1 (station capacity / make `remove_path` transactional) before implementation. The cleanest single fix for B1+M1+M2+M3 is to make `remove_path` a snapshot/rollback transaction like the existing fleet ops (`carriage_transaction_snapshot.py`).

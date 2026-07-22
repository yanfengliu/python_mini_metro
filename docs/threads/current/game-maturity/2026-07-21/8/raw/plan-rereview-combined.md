# GM-06d revised-plan re-review — verdict: NOT CLEAN (verbatim)

All 16 original findings are genuinely closed against live code, but the revision introduces one new MAJOR hole (incomplete transaction footprint around the delivery-credited alight it itself added) and one MAJOR-borderline contract gap (persisted-action gating for `cancel_unassignment`). Both are one-to-two-sentence plan fixes. The parent's hypothesized checkpoint-v4 blocker does **not** exist.

## Part 1 — Original finding closure (verified against live code)

- B1/F1 CLOSED: D-024 overflow-permitted alights + transactional `remove_path`. Verified the only `add_passenger`/`move_passenger` assert sites (`entity/holder.py:69-80`) are reached via spawn (`passenger_flow.py:135-136`), transfer (`passenger_capacity.py:39` + `passenger_flow.py:383-385`), and board (`passenger_flow.py:404-405`); direct-append forced alight bypasses all. With over-capacity, `has_room()` False yields exact D-024 semantics with zero gate edits; spawn timer still resets outside the `has_room` branch (`passenger_flow.py:138`) so no burst on drain.
- M1/F2 CLOSED: alight-before-mutation ordering + empty-only reconcile drops; the mid-loop partial shape can no longer exist.
- M2 CLOSED at the source by transactionality (modulo NEW-1).
- M3 CLOSED: non-empty globally-absent metros never dropped, left rejected and visible (see N4).
- M4 CLOSED: verified `iter_bulk_route_proposals` skips planned riders (`route_planner.py:207-209`); plan clears `travel_plans` and joins station lists so the sweep reaches them.
- M5 CLOSED: both named tests exist (`test_mediator_paths.py:23`, `test_path_lifecycle.py:103-162`) and are named as conscious flips routed through high-risk review.
- m1/F6 CLOSED: the three drain sub-cases exactly cover the stranding shapes; a rider with a valid future alight correctly rides on.
- m2 CLOSED: verified live `queue()` clears service state whenever `_real_station` (`fleet_management.py:315-319`); plan gates the clear to the empty fast path and softens the cancel wording.
- m3 CLOSED in intent (opens NEW-1).
- F3 CLOSED: verified `PaddingSegment` has no station endpoints (`entity/padding_segment.py:10-21`, `entity/segment.py:18-19`); adjacent-`PathSegment` rule deterministic.
- F4 CLOSED: verified `Mediator.increment_time` (`mediator.py:610-618`) supports reconcile-before-settle.
- F5 CLOSED: repair dropped; a dangling metro's stale cache is inert (`passenger_flow.py:310`).
- F7 CLOSED: unconditional reconcile feasible; the pause early-return lives in `PassengerFlow.increment_time` (`passenger_flow.py:147-148`), not the facade.

## Part 2 — New holes

### NEW-1 — MAJOR — remove_path snapshot footprint omits the delivery/progression cluster
The delivery hook's live footprint (`passenger_flow.py:372-380`) is `host.passengers.remove`, `passenger.is_at_destination = True`, `record_delivery()` incrementing `deliveries` and `line_credits` (`progression.py:96-100`, D-002), then `update_unlocked_num_paths()` (`input_coordinator.py:63-73`) and `update_unlocked_num_stations()` (`mediator.py:354-368`) which rebinds `host.stations` and starts blinks. None of that state appears in the enumerated footprint, and RNG coverage is scoped only "around the re-plan sweep". Concrete failure: a credited delivery crosses a station milestone (`progression.py:39-45`), a later alight raises an ordinary Exception (e.g. `assert next_station is not None`, `route_planner.py:169`), rollback restores only the enumerated footprint → deliveries/credits/stations persist, violating "a failed removal is a complete no-op". The model helper (`carriage_transaction_snapshot.py:29-137`) never covered progression either. Fix: extend the footprint (deliveries, line_credits, unlocked_num_paths/unlocked_num_stations in aggregate and facade views, `host.stations` binding, blink/lock state, `host.passengers` membership, per-rider `wait_ms`/`is_at_destination`) or restructure so credits and sweep run in a commit phase after the last failure point, and say which; add a "progression restored after injected post-credit failure" red test.

### NEW-2 — MAJOR (borderline) — persisted-action gating for `cancel_unassignment` unspecified
`validate_replay_action` (`recursive_contract.py:147-179`) version-gates only known sets; an unknown `{"type": "cancel_unassignment", "path_index": 0}` falls through lines 171-172 and validates at every version v1-v5 in both recursive and agent validation (`agent_play.py:184-188`). If the implementer never touches `recursive_contract.py`, a crafted v1-v3 document carrying the action executes the new mutation silently, violating the D-022/D-023 boundary as implemented for assign/unassign (rejected pre-v4 at lines 162-164). Fix: one gating sentence plus a persisted-gating red test.

### NEW-3 — MINOR — queued forced-alight pacing and order unspecified
Trigger verified stop-only (`entity/path.py:214-219`; `passenger_flow.py:311-313` services only `current_station is not None`). But the plan doesn't say one-interval-per-rider vs. one batch, nor rider order; both are deterministic but produce different drain durations, settle ticks, and replay traces. One sentence fixes it.

### Notes
- N4: "left rejected and visible" names no mechanism; name it (canonical-gate refusal is the visibility).
- N5: mirror plan-clear + wait-reset into Case 1's forced-alight bullet.
- N6 (probe negative): the hypothesized checkpoint blocker does not exist — generation serializes station passengers uncapped (`recursive_checkpoint.py:232-245`), v4 validation checks capacity only for metros (`recursive_checkpoint_schema.py:360-361`; `fleet_validation.py:193`), observations use variable-length arrays (`env.py:170-171, 273-275, 307-311`), no restore path calls `add_passenger`, `update_waiting_and_game_over` makes no capacity assumption (`passenger_flow.py:439-451`), `Holder.draw` renders arbitrary counts.

## Bottom line
Every original finding is genuinely dispositioned. Fix NEW-1 (footprint or commit-phase, plus red test), NEW-2 (gating sentence plus red test), NEW-3 (one clarifying sentence). NOT CLEAN — re-revise on those points; no other structural changes needed.

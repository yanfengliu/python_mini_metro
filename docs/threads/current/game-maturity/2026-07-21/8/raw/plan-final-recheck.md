# GM-06d second-revision narrow recheck — verdict: CLEAN (verbatim)

All five re-review items (NEW-1, NEW-2, NEW-3, N4, N5) are genuinely closed in `docs/threads/current/game-maturity/2026-07-21/8/PLAN.md`, and the new wording introduces no contradiction with live code.

## NEW-1 (Case 3 snapshot footprint) — CLOSED
Plan enumerates every item the re-review demanded, and each name matches the live state shape: `deliveries`/`line_credits` (`src/progression.py:25-26,96-100`; mediator exposes them only as delegating properties, `src/mediator.py:209-222`, so aggregate restoration suffices); `unlocked_num_paths`/`unlocked_num_stations` in both aggregate and facade views (real duplicated facade attrs: `src/mediator.py:357`, `src/input_coordinator.py:66-67`); `host.stations` binding (rebound at `src/mediator.py:365`); station/button unlock-blink and lock state (`src/mediator.py:368`, `src/input_coordinator.py:72,77`); `host.passengers` membership (`src/passenger_flow.py:375`); per-rider `wait_ms`/`is_at_destination`/`travel_plans` (`src/passenger_flow.py:373,376-377,386,406`); RNG upgraded to whole-transaction. Walking the full delivery hook (`src/passenger_flow.py:372-380`) plus both update calls, no touched state is missing (`purchased_num_paths` is purchase-only). Red test present at step 2.

## NEW-2 (persisted gating for cancel_unassignment) — CLOSED
Plan states the action joins the known version-gated persisted-action sets in `recursive_contract.py` and agent preflight as explicitly rejected at every persisted version v1-v5 before environment construction or mutation; step 2 adds the crafted-document red test. Implementable as specified: the fall-through is `src/recursive_contract.py:171-172`; agent preflight funnels through the same `validate_replay_action` (`src/agent_play.py:183-189`); no schema bump; genuine matrices unaffected. Implementation note (not a plan gap): the v4 agent path currently runs full action validation after `env.reset` (`src/agent_play.py:395-396`), so "before construction" at v4 needs a small pre-construction pass — the existing `_reject_record_carriage_actions` pre-pass (`src/agent_play.py:192-197`, invoked at 389) is the exact in-repo template; the red test enforces the endpoint.

## NEW-3 (drain pacing/order/trigger/cache) — CLOSED
Plan specifies one atomic batch within the tick, exact holder order, the oracle-quiet trigger, and no `_station_service_action` mutation. The cache-contract claim verifies: `reconcile_service_action` clears the cache to `None` with zero timers precisely when the oracle resolves `None` (`src/passenger_capacity.py:170-175`) — the drain-fire condition — and `service_cache_is_canonical` accepts a None cache in lenient mode and, in strict `require_bound_service` mode (`src/path_replacement_snapshot.py:308`), exactly when the pure oracle is None (`src/fleet_validation.py:69-82`), which the trigger guarantees; after the batch the emptied queued metro's oracle stays None (boarding queue-gated). Matches the queued stop-override contract (`test/test_gm06c_station_service.py:84-96`). Metro-side v4 capacity validation (`src/recursive_checkpoint_schema.py:360-361`) only tightens.

## N4 — CLOSED
Visibility mechanism named: canonical-gate refusal with continued presence in `path.metros`, rendering, and structured observations.

## N5 — CLOSED
Plan-clear + wait-reset mirrored into Case 1's forced-alight bullet.

## Fresh-contradiction sweep
The apparent Case 1 tension between oracle-first service (cache non-None during an in-progress unload) and the None-cache claim is not a contradiction: the None-cache claim is scoped to the batch moment, which by the trigger definition is exactly when reconcile has cleared the cache.

**CLEAN** — the second revision may proceed to red tests. Carry-forward implementation note: the v4 agent pre-construction validation pass under NEW-2, which the plan's own red test already forces.

# GM-06d conservation review — adversarial implementation report (verbatim)

Scope: working-tree delta vs `a21a3c0` — `src/fleet_management.py`, `src/path_removal_snapshot.py` (new), `src/path_lifecycle.py`, `src/passenger_capacity.py`, `src/passenger_flow.py`, `src/mediator.py`, `src/fleet_input.py`, `src/recursive_contract.py`, `src/agent_play.py`. Baseline: GM-06d modules 38/38 green; full suite OK (1036 collected, 12 skipped). Nine probe scripts run from the scratchpad; no repo file modified.

## Findings

### MINOR-1: Queueing an occupied metro with a bound BOARD cache creates a non-canonical window that persists across pause, refusing cancel and under-reporting `queued_locomotives_for_path`

Mechanism: `queue` (src/fleet_management.py:323-330) preserves the occupied candidate's cache, but `can_board_at_station` (src/mediator.py:688-690) gates boarding once the flag is set, so a preserved BOARD cache disagrees with the pure oracle and `service_cache_is_canonical` (src/fleet_validation.py:100-106) fails → every canonically-gated facade refuses (cancel_candidate, can_queue/can_assign, queued_count → 0, remove_path silent refusal, carriage attach/detach). The healing seam is flow-gated (paused `PassengerFlow.increment_time` early-returns, src/passenger_flow.py:148-149), so the window never closes while paused. DESTINATION/TRANSFER caches stay oracle-consistent; only BOARD flips. Pre-GM-06d this shape was impossible (only empty metros queueable).

Reproduction (probe4, seed 2): pause → queue occupied mid-BOARD metro → while paused: can_cancel False, count 0 (badge and observation truthfully show 1), remove_path no-op; after unpause + one tick everything heals. Zero conservation impact — every effect is a refusal; drain/settle correctly skip (preserved stop_time excludes the metro). But it cuts against Case 2's "a queued return can be cancelled" and D-023's paused-play spirit, and the removed stale-service-action repair is exactly not redundant while paused.

Suggested fix: in `queue()`, preserve the cache only for DESTINATION/TRANSFER identities and clear for BOARD (boarding is the one action queueing revokes).

### Observations (no severity)

1. Dead rider-drop branch: `_alight_metro_riders` (src/path_lifecycle.py:192-195) removes a rider and continues without placing it when `_alight_station_for_metro` returns None — a deletion if ever reached; unreachable through the gated facade (64/64 direct mid-padding removals placed correctly). Worth an explicit refusal.
2. D-024 wording vs the "no plan" sub-case: a planless rider whose destination shape matches a downstream station on the same line drains at the first quiet stop — matches the plan's explicit three-sub-case enumeration and the flipped GM-06b test; planless-aboard is unreachable in live flow; conservation holds either way.
3. `replay_playthrough(record, env=None)` constructs a fresh env before the generator's live-only rejection fires; no reset/step/mutation ever occurs; wrapper shape predates GM-06d.
4. Duplicated `_LIVE_ONLY_ACTION_TYPES` (recursive_contract.py:51, agent_play.py:38) — drift risk; import instead.

## Confirmed sound (probed)

Snapshot completeness & restoration exactness: failure injected at 7 points of the removal chain (incl. after a milestone-crossing credited delivery that rebound `host.stations` and started unlock blinks; mid-alight; KeyError; KeyboardInterrupt rethrow) across 4 seeds — exhaustive value+identity fingerprint incl. both RNG streams showed zero drift; restore rebinds the exact original objects and refills in place so aliases stay coherent; renderer survives rollback. Removal success conservation: exact per-rider delivery credits, milestone unlock fires, overflow placement, exactly one whole-consist refund, idempotent retired-path re-removal. Drain conservation across 24 fuzz seeds × 140 rounds and 100+ targeted runs: every rider in exactly one holder; global-list departures only as credited deliveries; no rider aboard detached metros; queued metros never gain riders; over-capacity stations only drain; plan-bearing riders with an on-line alight never drained early; capacity-blocked exits overflow exactly there. Occupied queued return: bounded settlement, exact single refund, cancel-after-partial-drain restores candidacy then re-queue settles with one refund. Cancel atomicity: rejection paths fingerprint-identical including both RNG streams. Reconcile: double-run no-op on canonical states across thousands of fuzz ticks; runs before drain so a cleared ghost is never drained same-tick; every legitimate transition is call-atomic. Persisted gating: rejected v1-v5 before construction (spy factory never called); recorder rejects a cancel-emitting agent; nested sneaks inert. Cross-feature: queue flag and rider survive replace_path; drain completes on new topology; replacement over an overflowed station loses no riders; mid-gesture removal safe; terminal-tick parity with pre-GM-06d settle. Budgets: all changed files within limits.

## Verdict

CLEAN — no blocker or major finding; rider/resource conservation could not be refuted at any probed surface. One minor finding (the paused stale-BOARD window, refusal-only, surgical fix available) and four observations listed for disposition.

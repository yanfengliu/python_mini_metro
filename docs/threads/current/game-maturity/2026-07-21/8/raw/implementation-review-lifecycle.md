# GM-06d adversarial implementation review — simulation timing / lifecycle / determinism (verbatim)

VERDICT: NOT CLEAN — one substantive probe-backed defect (F-1) plus corollaries. No conservation, determinism, or rollback violations found; the timing seam itself is sound.

## F-1 (MAJOR): `queue()`/`cancel()` flip boarding legality without reconciling the service cache — under pause the state is observably non-canonical, and v4 checkpoint generation crashes on legitimately-reached states

Mechanism: the pure oracle reads `is_unassignment_queued` through the boarding gates (`src/mediator.py:687-690`, `src/passenger_capacity.py:41`). `FleetManagement.queue` preserves the full service cache for an occupied selection (`src/fleet_management.py:323-330`, per plan m2), and `cancel` restores only the flag (`src/fleet_management.py:350-369`). Both change what the oracle resolves while leaving `_station_service_action` unreconciled. In running play the next tick's `move_passengers` reconcile self-heals within the same `env.step`. While paused, nothing reconciles (paused `increment_time` runs only `_fleet.reconcile`), so the stale cache persists indefinitely: `service_cache_is_canonical` fails → every canonical fleet query/action returns False/0 (`queued_locomotives_for_path → 0` while the flag and observation report 1; the fleet-button badge shows 1); a queue created while paused cannot be cancelled while paused; and `canonical_checkpoint` v4 raises (`src/recursive_checkpoint_carriages.py:158`; also "Metro service cache is stale" in the cancel direction).

Reproductions (public actions only, default config): queue direction (probe_a: dt=250, seed 0, 13 noops to mid-BOARD, pause, unassign); cancel direction (probe_b: dt=500, seed 0, step 4, pause, cancel → oracle resolves board vs None cache); end-to-end (probe_i): a schema-valid v5 recursive document (create_path, assign_locomotive, 14 noops, pause, unassign_locomotive, dtMs 250, seed 0) crashes `run_scenario` with `ValueError: checkpoint runtime carriage graph is malformed` at `src/recursive_playtest.py:348`.

Why tests missed it: the cache-preservation test uses a DESTINATION unload — the one kind the queue flag does not invalidate — and no GM-06d test contains `pause` in the queue/cancel window; no test generates a checkpoint inside that window.

Suggested fix: reconcile the affected at-station metro synchronously inside `queue()` and `cancel()`, exactly as carriage attach/detach already do (`src/mediator.py:549-565` pass `reconcile_station_service`; D-023: "composition changes … reconcile stopped trains").

## F-2 (MINOR, same root cause): `remove_path` never reconciles surviving metros' caches

`src/path_lifecycle.py:154-206` clears caches only on removed metros. Conserving alights and the re-plan sweep can flip a surviving parked metro's oracle on another line; under pause that is the same stale class (checkpoint raises until resume). Fix family: reconcile stopped survivors post-removal.

## F-3 (MINOR, cosmetic): drain can fire on a queued metro coasting through a station

`move_metro` sets `current_station` on pass-through arrival (`src/entity/path.py:219`); the drain gate checks only `stop_time_remaining_ms <= 0` (`src/passenger_capacity.py:217-220`). Queueing during the one-tick arrival window of a non-stopping metro force-alights at a station the metro never stopped at. Deterministic and conserving; deviates from D-024's "stopped" wording only visually.

## F-4 (NOTE): terminal-tick drain/settle

`transition_active` is computed before the flow; when the game ends mid-tick, the post-flow drain+settle still run. Terminal-tick settle is pre-existing GM-06b behavior; the terminal-tick drain (rider moves + wait resets after game over) is new. Deterministic.

## F-5 (NOTE): silent-rollback removals report `action_ok=True`

`remove_path_by_index` returns True for any valid index including internal rollback and canonicity-gate refusal. Pre-existing shape, widened by the new rollback path. Replay-deterministic.

## CONFIRMED SOUND (probe-backed)

Cross-run determinism (3 seeds × 70 v4 checkpoints byte-identical; identical action_ok sequences). Drain/oracle purity (double drain byte-neutral incl. both RNG streams; queued metros short-circuit before every RNG-consuming boarding path). Bounded occupied return + conservation (settles in 32 steps; exact single refund; every rider accounted). Transactional removal (riders alight or credit; injected mid-transaction failure restores a byte-identical checkpoint and both RNG streams; interpolator/renderer survive rollback; snapshot covers the delivery/progression cluster, station unlock extension + blink, button rebinding, sweep RNG). Structured/manual cancel parity byte-identical. Persisted gating rejected v1-v5 before construction/mutation. Reconcile-at-top RNG-free, byte-neutral, ghost-drop consistent with badge and rendering; interpolation snapshots id-keyed with safe live fallback. Single-line stranding impossible (replacement preflight refuses orphaned alights). Full suite OK; default v5 recursive fixture contains no queue/cancel ops, so CI's clean pass does not exercise F-1.

Accepted deviations assessed sound: double drain+settle seam (pre-flow no-op when nothing changed; no double-service path exists); unconditional reconcile at top; drain core in `passenger_capacity.py`.

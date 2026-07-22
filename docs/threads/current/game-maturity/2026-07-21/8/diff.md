# GM-06d fleet edge-case hardening diff ledger

Status: delivered as Commit A `62d26a2` (rebased over the owner-launched CI-actions commits with one additive PROGRESS.md merge), exact [run 29893340731](https://github.com/yanfengliu/python_mini_metro/actions/runs/29893340731) green; evidence-only Commit B active

## Implemented production surface

- Widen queued-return selection to occupied locomotives (empty-preferred, then fewest riders with latest-order tie-break) with preserved in-progress unload timing and a synchronous transactional service-cache reconcile shared with cancellation through the new `fleet_queue_transition.py`.
- Add the oracle-quiet one-batch forced-alight drain for queued locomotives (`passenger_capacity.py` core, `passenger_flow.py` wrapper), gated off terminal ticks, guaranteeing bounded occupied returns under D-024 overflow-permitted placement.
- Add `can_cancel_unassignment`/`cancel_unassignment` facades, the `cancel_unassignment` structured action, and its live-only persisted gating rejected at recursive/agent v1-v5 before construction or mutation (`fleet_management.py`, `mediator.py`, `fleet_input.py`, `recursive_contract.py`, `agent_play.py`).
- Make `remove_path` a rider-conserving snapshot/rollback transaction (`path_lifecycle.py` plus new `path_removal_snapshot.py`): alight-before-mutation ordering, delivery-credited destination-shape alights, overflow-permitted station placement, plan clearing and wait reset, deterministic station/mid-segment/padding placement, surviving-metro service reconcile, explicit refusal of unplaceable riders, exact-identity restoration across the complete topology/holder/service/progression/blink/RNG footprint, and non-`Exception` rethrow.
- Add the narrow unconditional `FleetManagement.reconcile` seam at the top of `Mediator.increment_time` (paused and terminal ticks included): clears queue flags on globally absent metros and drops only empty globally absent path entries, refusing everything else.

## Implemented evidence surface

- Reconcile GM-06c Commit A run `29853718512` and Commit B run `29854939135`; record D-024 (owner-selected overflow-permitted forced alights) in the parent decision log.
- Three-round adversarial plan gate, four red-test modules with 46 red records plus combined baseline, eight conscious contract flips (three planned, five surfaced), two-lane adversarial implementation review, one major fix round with seven red-first regressions, and a clean final re-review — all preserved verbatim under `raw/`.
- Update `README.md` (widened unassignment, `cancel_unassignment`, conserving removal), `GAME_RULES.md` (occupied return and drain rules, soft-cap semantics, conserving removal, programmatic action list), and `ARCHITECTURE.md` (new modules, boundary prose, test listing).
- File two out-of-scope background tasks: CI Node-20 actions deprecation; pre-existing padding-segment recursive-oracle false positives, pinned by the new harness regression.

Local gates: full py313 suite 1043/0 with 12 expected skips (re-verified on the rebased tree); guarded `npm test` 249/0 with 4 expected skips; Ruff and per-file pre-commit clean; all line budgets held. Commit A `62d26a2` passed exact [run 29893340731](https://github.com/yanfengliu/python_mini_metro/actions/runs/29893340731); evidence-only Commit B binds this result, and GM-07 opens only after B's own exact workflow is green.

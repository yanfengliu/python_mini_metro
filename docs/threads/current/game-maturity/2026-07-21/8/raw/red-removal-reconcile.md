# GM-06d red evidence — line-removal and reconcile lane

Command: `python -m unittest test.<module> -v` in `py313` at the GM-06c-finalized baseline (`a21a3c0`), before any production change.

- `test_gm06d_line_removal.py` (491 physical lines): 10 tests — 11 FAIL records (with subtests) / 0 ERROR / 2 guard greens. Reds: rider conservation and destination-credit (`deliveries 0 != 1`; riders deleted today), station/mid-segment/padding alight placement (riders `not found in []`), 14-rider overflow dump (`0 != 14`), and the four transaction tests — ordinary-failure restoration, `KeyboardInterrupt` rethrow-with-restoration, RNG-stream restoration, and milestone-crossing progression restoration — all failing on exact-identity restoration (rethrow itself already propagates today; restoration is the red). Guard greens: ordinary D-024 gates exact at and above capacity (including the spawn-timer reset while full and blocked-transfer completion after drain), and consist refund via derived availability.
- `test_gm06d_reconcile.py` (318 physical lines): 7 tests — 7 FAIL records / 1 guard green. Four direct tests fail cleanly on the missing `FleetManagement.reconcile` via the gm06c `require_attribute` idiom; seam tests fail on missing repair (ghost entry not dropped while paused/terminal; same-tick ghost repair plus settle). Guard green: paused/terminal ticks on canonical state change nothing.
- Contract flips: `test_remove_path_cleans_passengers` → `test_remove_path_conserves_onboard_riders` (`test/test_mediator_paths.py`, now 1 FAIL / 7 ok) and `test_remove_path_preserves_snapshots_and_plan_invalidation_contract` → `test_remove_path_conserves_onboard_riders_and_plan_invalidation_contract` (`test/test_path_lifecycle.py`, now 1 FAIL / 9 ok, plus removal of the flip-orphaned `CallbackList` import). The deletion-specific mid-iteration machinery and the `button:clear`-first assertion were dropped (Case 3 moves rider safety before button detachment); the plan-invalidation matrix and the `invalidate < release < assign < replan` order chain are retained green.
- Adjacent modules (`test_gm06b_fleet_queue`, `test_mediator_path_contract`, `test_mediator_path_failure_contract`, `test_gm06c_station_service`) run OK — no src file was modified. Ruff check/format clean on all four touched files.

Baseline discoveries:

- `remove_path` has a silent no-op gate on non-canonical/incomplete targets (`path_lifecycle.py:72-76`); every removal setup asserts dispatchability first so reds fail on the contract, not the gate. The implementation must keep reject-before-snapshot ordering.
- Consist refund is already green at baseline under destructive removal (derived counts), so it is a guard; refund-with-riders is asserted inside the red conservation test.
- Future-green mechanics probed against live code: a queued empty metro arriving in-tick settles same-tick once canonical; an over-capacity station drains exactly one rider per 500 ms in holder order; all seven reconcile seeds produce geometry-valid dispatchable paths.

# Combined red

`python -m unittest test.test_gm06d_occupied_return test.test_gm06d_cancel_unassignment test.test_gm06d_line_removal test.test_gm06d_reconcile test.test_mediator_paths test.test_path_lifecycle -v` → **Ran 56 tests: failures=40, errors=6**, remainder green (guards plus untouched tests in flipped files). No production file changed before this capture.

# GM-10a IMPLEMENTATION REVIEW — harness general-purpose lane (agentId a2ac75156eef931c7)

**Verdict: SHIP.** Full py313 suite green (1488 passed, 12 skipped), GM-10a 14/14, RL contract smoke green (26 tests), ruff clean on all 7 changed files. All 6 plan-review folds verified present + correct. Every attack vector reproduced empirically.

## Attack-by-attack (NO code finding on any)
1. GATING: every Mediator construction takes default week_calendar=False (env.py:21/62, rl/player_env.py:142, main.py:78 tutorial, save_load.py:346); only main.build_game/build_from set it, gated on `max_frames is None` (same signal as audio/start-state). Probe: MiniMetroEnv→1300, PlayerPixelEnv→1206, both never pending/frozen. Tutorial never sets it.
2. HOLD PLACEMENT/determinism: `_maybe_hold_week_boundary` is the last statement of increment_time, after both settlements; `fleet_management.settle` early-returns on is_paused (:369) so placement matters. Probe across 7 seeds with REAL boards (paths+metros+1-5 deliveries): on/off byte-identical at the boundary except _pause_reasons/is_paused. Queued-metro probe settles identically on/off. Speed-4: single hold at 1200, no skip/double. Frozen tick: no re-trigger.
3. TERMINAL PRECEDENCE: `_maybe_hold` reads live post-tick is_game_over; update_waiting_and_game_over runs at the END of the passenger tick. Genuine simultaneous case → is_game_over=True, pending=False (game-over wins). reconcile_game_over before reconcile_week_boundary in both handle_event + run_game; week reconcile requires is_game_over is not True.
4. OFFER/ARMING: the `is True` guard is load-bearing (MagicMock probe stays PLAYING). Letterbox-cancel fires before the switch + clears arming. _handle_offer never dispatches to the session; Continue needs an offer-local down→up.
5. SAVE/PERSISTENCE: mid-week serialize rejected with the clear message; validate_save is the structural backstop; after resolve, save succeeds pauseReasons=[]. Window-close-mid-OFFER resolves+autosaves; round-trip week_index survives (derived from steps); second boundary at exactly 2400.
6. AUDIO: OFFER frame re-baselines via snapshot_of (no burst); headless never opens a device.
7. DETERMINISM/RL: env.py NOT touched; observe() has no "week" key; recursive_checkpoint has zero week references → RL observation/checkpoint byte-identical. Full suite + RL smoke green.

## Findings — 3× MINOR (test-strength only; shipped code correct on every path)
- MINOR — test_the_boundary_hold_is_after_the_full_tick (test_gm10a_calendar.py:109-125) does NOT exercise settlement: both boards have no paths/metros, so the boundary tick settles nothing. Mutation moving the hold before the second settle STILL passes, yet would strand a queued metro. Fix: add a path + assigned metro with a queued unassignment near the boundary, assert available_locomotives/len(metros) equality vs a calendar-off control.
- MINOR — test_no_hold_on_the_game_over_tick (:99-107) doesn't advance across the boundary: pre-sets is_game_over=True so steps stay at W-1 and old//W < steps//W is False regardless of the guard. Deleting the `or is_game_over` guard still passes. Fix: time an overdue-passenger game-over to coincide with the boundary crossing.
- MINOR/NIT — test_a_stub_mediator_never_enters_the_offer (:199-209) uses a SimpleNamespace with no is_week_boundary_pending, so getattr→False; passes whether the guard is `is True` or truthy. Fix: use a MagicMock (truthy-but-not-True) to pin the `is True` semantics.

## Verdict: SHIP. Code correct on all 8 vectors; the 3 MINORs are test-mutation-coverage gaps (not defects) — harden the three regression tests so the two folded MAJORs and the `is True` guard are actually pinned.

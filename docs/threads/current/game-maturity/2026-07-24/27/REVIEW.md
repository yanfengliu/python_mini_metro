# GM-10a plan — dual adversarial review synthesis

Both lanes **REVISE**; both verified the deterministic-calendar CORE sound (derived `week_index`, the `"week"` pause reason, 1×/2×/4× boundary arithmetic, Space/speed independence, the checkpoint-safe observation sibling, `1200` provisional default, Mediator ownership). The dual review earned its keep enormously here — the harness caught a BLOCKER, and Codex went far deeper with reproduced live counterexamples (2 BLOCKER + 4 MAJOR).

- Harness (`raw/plan-harness.md`, REVISE): 1 BLOCKER (`PlayerPixelEnv` + RL train/eval soft-lock — the `env.py` auto-resolve doesn't reach the pixel env, which drives via `GameSession.advance_exact`) + a reconcile-ordering MINOR + save-block NIT. Attack points 1/3/4/5/6 verified sound.
- Codex ultra (`raw/plan-codex.md`, REVISE): 2 BLOCKER + 4 MAJOR + 2 MINOR, several with reproduced state. Corroborated the pixel-env BLOCKER and the reconcile ordering, and ADDED: pause-invariance is FALSE through the real `FixedStepClock` (my probe bypassed the cadence); the boundary hold interrupts queued-return settlement mid-tick (inventory corruption); the tutorial is a third freezing shell; the async OFFER lacks gesture-cancel/arming; simultaneous game-over+week bypasses the game-over promotion; window-close-during-OFFER + audio-during-OFFER gaps.

## Load-bearing decisions
- **GATE the calendar to the human PLAYING shell** (`Mediator.week_calendar`, default False; `build_game`/`build_from` opt in). This resolves BOTH pixel-env/tutorial freezes structurally (weeks never hold headless), moots the cadence-reset determinism concern (the calendar branch is never taken in any deterministic/RL path), and removes the `env.py` change entirely.
- **Correct the pause-invariance claim** — it is false through the real clock (my direct-`increment_time` probe bypassed the `(17,17,16)` cadence). "No version bump" is justified by gating (weeks out of deterministic paths), NOT invariance; the cadence-reset-on-pause is pre-existing (shared with user/menu pauses) and out of scope.
- **Hold `"week"` AFTER the full tick** (after the post-passenger `_drain_and_settle_queued_returns()`), guarded by `week_calendar and not is_game_over`, else settlement is skipped mid-tick.
- **Game-over precedence** (reconcile game-over first; week reconcile rejects terminal/non-PLAYING) + **gesture-cancel & arming** on the OFFER promotion + **window-close-during-OFFER resolves-then-autosaves** + **audio consumed on the OFFER frame**.

## Findings + dispositions — ALL folded into PLAN v2
- BLOCKER (both): pixel-env/tutorial freeze → GATE (Mediator flag, human opt-in). FOLD.
- BLOCKER (Codex): cadence-reset → correct the premise; justify via gating; add an RL-checkpoint-byte-identical regression; pre-existing cadence out of scope. FOLD.
- MAJOR (Codex): hold after the full tick (settlement) + not-game-over guard. FOLD.
- MAJOR (Codex)/MINOR (harness): terminal precedence — game-over first, week reconcile rejects terminal. FOLD.
- MAJOR (Codex): OFFER gesture-cancel + Continue arming. FOLD.
- MINOR (Codex): window-close during OFFER resolves+autosaves. FOLD.
- MINOR (Codex): audio consumed on the OFFER frame. FOLD.
- Observation `"week"` block DEFERRED to GM-10b (meaningless for gated-off RL); GM-10a touches no `env.py`. FOLD.
- NIT: keep `_require_quiescent` for the error message (validate_save is the structural barrier); comment the speed-4 landing. FOLD.

## Result
Both REVISE → all folded into PLAN v2. The human-shell-gated design makes RL/tutorial/tests structurally free of weeks (no freeze, no determinism risk, no `env.py` change), holds after the complete tick, and makes the OFFER promotion game-over/gesture/window-close safe. Ready for red tests.

---

# GM-10a implementation — dual adversarial review synthesis

Both lanes independently confirmed the **production code CORRECT** — the gate (`week_calendar = max_frames is None`), the after-the-full-tick hold with the `not is_game_over` guard, the crossing arithmetic (`old//W < steps//W`), the game-over-first reconcile with the `is True` guard, the OFFER gesture-cancel/arming, the save block, and the silent-audio OFFER frame all behave as specified. **Every finding was TEST-STRENGTH** (a surviving mutation), not a production defect — so this is the review-coverage lesson again: one lane rated the suite shippable while the other proved, by mutation, that it was not.

- Harness (`raw/impl-harness.md`, **SHIP** + 3 MINOR): production correct; flagged the terminal/settlement tests as pre-set rather than genuinely crossing, and the stub test as not pinning `is True`.
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST** + 6 MAJOR, each mutation-confirmed): the same suite passed against six distinct mutants — an exact-landing-only hold, a hold-before-settlement, a dropped `not is_game_over` guard, a truthy (not `is True`) OFFER guard, a wrong/None letterbox-cancel event, and a missing run-loop OFFER promotion/QUIT path.

## Findings + dispositions — ALL 6 folded (every fold re-run green)
- MAJOR (Codex) **exact-landing hold**: `test_speed_4_crossing_holds_without_landing_exactly` drives speed-1→`W-2`, then one speed-4 tick to `W+2` (jumps ACROSS `W`, never on it) — an `== W` mutant survives the old suite, fails this.
- MAJOR (Codex) **hold vs. queued settlement**: `test_the_boundary_hold_does_not_interrupt_queued_settlement` queues a locomotive unassignment to settle ON the crossing tick and asserts `metros`/`available_locomotives`/`deliveries` equal to a calendar-OFF control — a hold-before-settle strands the metro.
- MAJOR (Codex) **terminal precedence**: `test_no_hold_when_the_boundary_tick_also_game_overs` calls `_maybe_hold_week_boundary(W-1)` with `steps==W` + `is_game_over` (a GENUINE crossing) and asserts no hold, with an alive control that DOES hold — dropping `or is_game_over` survives a pre-set never-crossing version, fails this.
- MAJOR (Codex) **`is True` semantics**: `test_a_truthy_but_not_true_pending_flag_stays_out_of_offer` uses a live `MagicMock` (truthy auto-attr, never the literal `True`) — a `truthy` guard promotes to OFFER, the `is True` guard does not; the `SimpleNamespace` stub couldn't distinguish them.
- MAJOR (Codex) **exact cancel event**: `test_reconcile_promotes_a_pending_boundary_to_offer` now asserts the dispatched event IS a `MOUSE_UP` at `(-1, -1)`, not merely `len == 1` — a None/`MOUSE_DOWN`/on-viewport mutant survives a length check, fails this.
- MAJOR (Codex) **run-loop OFFER path**: `TestGM10aGating` + `TestGM10aRunLoopOffer` drive the REAL `main.run_game`/`AppController` behind recording fakes — bounded→calendar OFF, unbounded→ON, tutorial OFF, pixel-RL env OFF past a boundary; a pending boundary promotes+renders `draw_offer_screen(week_index)` over the frozen frame; an OFFER-QUIT resolves+autosaves (with a title-QUIT control proving non-vacuity).
- MINOR (harness): the pre-set terminal/settlement tests — superseded by the genuine-crossing versions above.

## Result
Both lanes confirmed the production code; all 6 mutation-confirmed test-strength gaps folded and re-run green (23 GM-10a tests). Full `py313` suite green (1500 tests). Gated (ruff check/format, pre-commit) on the changed files. Ready to deliver [GM-10a:A] → CI → [GM-10a:B].

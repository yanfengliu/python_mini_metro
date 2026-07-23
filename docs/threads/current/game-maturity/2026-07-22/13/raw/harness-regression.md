# Harness adversarial review — regression / test-quality lens (verbatim)

Model: harness general-purpose subagent (Opus 4.8). Lens: find where the change silently breaks pinned frame-loop composition, or where the new tests fail to pin what they claim. Empirically verified red-first by reverting only the main.py change in place, then restoring byte-identically.

---

## Verdict: No confirmed regressions. Change is a faithful, guarded extraction. All 44 assigned-module tests pass; none are flipped.

### What I verified against live code

The diff (uncommitted working tree) is exactly what the task described: the inline promotion block moved verbatim into `reconcile_game_over()` (guard `self.mediator.is_game_over is True` unchanged), `handle_event` calls it at top, `run_game` adds `controller.reconcile_game_over()` + `state = controller.state` re-read after `advance`.

Four mechanisms protect every pinned assertion:
1. **The `is True` identity guard** (`app_controller.py:129`) makes both reconcile call-sites a **no-op for any MagicMock mediator** — a MagicMock auto-attribute is never `is True`. Belt-and-suspenders: every `test_main.py` mediator *also* sets `is_game_over = False` explicitly (lines 106/143/179/214) or uses a real fresh `Mediator` (plain bool `False`, `mediator.py:157`). The task's concern #4 trap is **not** realized.
2. **QUIT is handled inline in `run_game` and raises `SystemExit` before the post-advance reconcile** — so in every GM-07c/GM-07d run-loop test the per-frame reconcile never runs on the QUIT frame, and the QUIT gate still sees pre-reconcile state. Mutual exclusion preserved.
3. **GM-07a mediators set `is_game_over = False`** (`test_gm07a_run_game_loop.py:65`) → reconcile no-op → advance args, draw count/order, dispatch counts all unchanged (traced each of the 3 frame tests).
4. **The `state` re-read differs from the pre-advance read only when reconcile actually promotes** (PLAYING→GAME_OVER) — the intended new behavior; identical everywhere else. `test_gm07a_app_controller.py`'s `run_game` spy tests fully mock `AppController`, so the new call is a harmless MagicMock no-op not touching asserted constructor args.

Controller-level GM-07c/GM-07d promotion tests (`_press(K_SPACE)`) still promote-then-route identically (reconcile at handle_event top == old inline block, confirmed by the diff).

### Empirically verified red-first (reverted `main.py` reconcile+re-read, ran, restored)
- `test_eventless_game_over_records_once_and_draws_indicator` → **FAILS** at baseline (`record.call_count` 0 != 1). Genuine red-first.
- `test_eventless_game_over_then_quit_records_exactly_once` → **FAILS** at baseline, but on `best.call_count` (0 != 1), **not** `record.call_count`.

### Test-quality findings (MINOR — not blockers)

**TQ-1 (MINOR) — the mutual-exclusion test's headline assertion is not the red-first discriminator.** The `record.call_count == 1` assertion **passes even with the fix reverted**, because at baseline the window-close QUIT gate records exactly once on its own (confirmed empirically — only the `best.call_count == 1` assertion failed). So "exactly one record across the reconcile and the QUIT gate" is pinned only in the *no-double-record* direction (a broken fix recording in both surfaces → 2, would be caught), not the *fix-records-at-all* direction. The test is red-first and non-vacuous **as a whole** via the best-indicator assertion, but its named guarantee rests on that assertion, not the record-count. If stronger mutual-exclusion pinning is wanted, assert which surface recorded (e.g., that the QUIT branch was not the recorder).

**TQ-2 (INFO) — controller-level `TestGM07eReconcileGameOverController` tests pin logic byte-identical to the pre-existing inline promotion.** They are red-first only *structurally*, via the `_require_reconcile` `hasattr` guard: reverting GM-07e removes the method so `assertTrue(hasattr(...))` fails cleanly. They do add real guard/idempotency coverage — `test_reconcile_is_idempotent` would catch a mis-implementation guarding only on `is_game_over` (records/deletes 3× instead of once), and `test_seamless_reconcile_reads_no_deliveries_and_mints_no_best` genuinely pins MAJOR-3 (no `deliveries` access when seamless). Not a defect; just no *new* promotion behavior beyond the extracted seam's existence.

### Plausible concerns — checked and cleared
- **Intra-frame `[promoting_event, quit]` batch** (event promotes, then same-frame QUIT): correct by idempotency (reconcile's `state is PLAYING` guard fails post-promotion; QUIT gate sees GAME_OVER → skips). No test covers this exact sequence, but behavior is sound.
- **Post-game-over frames keep advancing with `elapsed`** (advance-arg branch selects `advance(elapsed)` for GAME_OVER): pre-existing GM-07a behavior, unchanged by GM-07e.
- **PAUSE_MENU + game-over never promotes via reconcile** (PLAYING-only guard): intentional and consistent — the window-close QUIT gate handles PAUSE_MENU game-over recording (GM-07d `test_quit_when_game_over_in_pause_menu_records_once`).

Files reviewed: `src/app_controller.py`, `src/main.py`, and the 7 assigned test modules plus `test/test_gm07a_app_controller.py`.

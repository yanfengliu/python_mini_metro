You are an adversarial code reviewer. READ THE LIVE CODE in this workspace (do not trust the diff alone). Your job is to find real defects, not to approve. Range freely across the repo; grep and read whatever you need.

## Change under review (GM-07e: deterministic per-frame game-over reconciliation)

This is the accepted follow-up to a MAJOR finding your own persistence lane raised on GM-07d (see docs/threads/current/game-maturity/2026-07-22/12/raw/codex.md and codex-2.md): an eventless PLAYING->GAME_OVER transition recorded nothing and showed no best indicator until the next incidental event or the window-close QUIT.

Two edits (piped diff above; read the full files):
1. `src/app_controller.py`: the PLAYING->GAME_OVER promotion block was extracted from `AppController.handle_event` into a new public idempotent method `reconcile_game_over()` (no-op unless `state is PLAYING and mediator.is_game_over is True`; else set state=GAME_OVER, `_autosave_delete()`, `_record_highscore()`). `handle_event` now calls `self.reconcile_game_over()` at its top, then routes the event as before.
2. `src/main.py` `run_game`: after `session.advance(...)` and `previous_session = session`, it now calls `controller.reconcile_game_over()` then re-reads `state = controller.state` before rendering. Note `state` was first read BEFORE advance to choose the advance argument (TITLE or session-swap -> advance(0), else advance(elapsed_ms)).

## Invariants the change must uphold (verify or REFUTE with a concrete repro)

- Deterministic: the game-over promotion (record high score, delete autosave, set `last_highscore_result` for the best indicator) fires the exact frame `mediator.is_game_over` flips during `session.advance`, even with zero events that frame.
- Records EXACTLY ONCE per game-over — never zero, never twice.
- MUTUALLY EXCLUSIVE with the window-close `pygame.QUIT` gate in `run_game` (~src/main.py:189-203), which when `controller.state in (PLAYING, PAUSE_MENU)` and `mediator.is_game_over` does `delete_autosave()` + `record_highscore(controller.mediator)`. No double record/delete across the reconcile and the QUIT gate.

## Hunt specifically for

1. Any frame ordering that double-records or double-deletes one game-over (reconcile via handle_event AND/OR the per-frame call AND/OR the QUIT gate).
2. A zero-record path that still exists after the change.
3. Wrong-time promotion (PAUSE_MENU / TITLE / GAME_OVER / session-swap Restart frame) or bad interaction with the `previous_session` advance(0) swap logic.
4. The `state = controller.state` re-read after reconcile altering a render decision incorrectly for non-game-over frames, or the advance-arg decision using a stale/wrong state.
5. Regression risk to the mutation-pinned frame-loop composition tests: test/test_gm07a_run_game_loop.py, test/test_gm07c_run_game_loop.py, test/test_gm07d_run_game_loop.py, test/test_main.py (advance() args, draw-call composition/order, dispatch counts). Does the per-frame reconcile or the state re-read flip any pinned assertion? Check each test's mediator: is `is_game_over` False, or an implicit truthy MagicMock attribute that reconcile (`is X is True`) would trip?
6. TEST-QUALITY of test/test_gm07e_game_over_reconcile.py: are the new assertions real red-first contracts (would they fail if the fix were reverted), or vacuous? Does the run-loop `_FlipSession`+spies actually prove "records once the frame it ends" + "best indicator drawn with the fresh result", and does the `[[], [quit]]` mutual-exclusion test distinguish fixed-vs-broken?
7. Per AGENTS.md → Code review: also flag process regressions, stale documentation (README.md:65, GAME_RULES.md:106, ARCHITECTURE.md:374 describe this behavior — do they now match?), and missing validation.

You may run the suite: `C:/Users/38909/miniconda3/envs/py313/python.exe -m unittest test.test_gm07e_game_over_reconcile test.test_gm07a_run_game_loop test.test_gm07c_run_game_loop test.test_gm07d_run_game_loop test.test_main -v`. A green suite is not proof of absence — reason about the code.

Output a ranked list: CONFIRMED defects (file:line + exact repro + wrong outcome), PLAUSIBLE concerns (with why), and a final VERDICT line (CLEAN / NOT CLEAN). Be concrete and terse.

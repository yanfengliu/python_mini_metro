# Harness adversarial review — correctness / mutual-exclusion lens (verbatim)

Model: harness general-purpose subagent (Opus 4.8). Lens: refute the change on correctness — double/zero record, mutual exclusion with the window-close QUIT gate, wrong-time promotion, state re-read, seam mismatch, max_frames/headless.

---

## Verdict: NO REAL DEFECT FOUND

I tried hard to break it across all seven hunt targets and could not. The change is correct. The conclusion rests on one invariant I verified in the live code, then traced every ordering against.

### The load-bearing invariant (verified, not assumed)
`mediator.is_game_over` is written `True` at exactly ONE site — `src/passenger_flow.py:463` (`update_waiting_and_game_over`) — reachable ONLY through the tick: `game_session.advance/_apply_steps` -> `mediator.increment_time` -> `update_waiting_and_game_over`. Event dispatch (`mediator.react` at `src/mediator.py:452`) delegates to `input_coordinator.react` (`src/input_coordinator.py:374`), which only *reads* `is_game_over` as an input-suppression guard (lines 162, 430) and never writes it. `step_time`/`increment_time` (`input_coordinator.py:118-119`) is not on the `react` path.

Consequently: `is_game_over` flips only during `advance`, which runs AFTER the event loop. The new per-frame `controller.reconcile_game_over()` at `src/main.py:236` runs unconditionally immediately after every `advance`, so the frame the flag flips, `PLAYING`->`GAME_OVER` is promoted and recorded that same frame — before any later frame's event loop can observe it.

### Hunt results (each REFUTED)
1. **Double-record / double-delete** — Not found. Traced 0-event, 1-event, and 2+event frames (incl. a trailing `QUIT`). Because promotion happens the flip-frame, any subsequent `QUIT` sees `state == GAME_OVER`, so the QUIT gate's record branch (`src/main.py:194-200`) is guarded out by `controller.state in (PLAYING, PAUSE_MENU)`. `reconcile_game_over` is idempotent (no-op once `GAME_OVER`). Exactly one record. Test `test_eventless_game_over_then_quit_records_exactly_once` corroborates.
2. **Zero-record** — Not found. `reconcile` at `main.py:236` is unconditional (not inside any `if`), the highscores seam is always present in `run_game`, and recording no longer depends on an incidental event. No frame flips the flag without the following reconcile.
3. **Wrong-time promotion** — Not found. `reconcile` guards on `self.state is AppScreen.PLAYING` (`app_controller.py:129`). PAUSE_MENU holds the `"menu"` pause reason -> `is_paused` True (`mediator.py:585-588`) -> `advance` no-ops (`game_session.py:54`), so the flag can neither flip nor pre-exist in PAUSE_MENU (`handle_event` reconciles at its top, `app_controller.py:137`, before an Escape could pause). Session-swap frames (New Game / Restart / Continue) build a fresh `is_game_over=False` mediator and take `advance(0)`, so reconcile no-ops.
4. **`state` re-read (`main.py:237`) corrupting a render/advance decision** — Not found. For non-game-over frames reconcile is a no-op, so the re-read equals the pre-reconcile value. The advance-arg decision correctly uses the *pre*-advance `state` (`main.py:222`), so the terminal tick runs with real `elapsed_ms`; only after it flips the flag does reconcile promote. Ordering is right.
5. **`is_game_over` True while `PLAYING` at the QUIT gate** — Not reachable after this change, by the invariant above. The QUIT-gate record branch is now effectively defensive-redundant in real play. Benign, and the code comment documents the mutual-exclusivity intent.
6. **`deliveries` seam mismatch** — Not found. `run_game` always uses a real `Mediator` (property at `mediator.py:211`); `_record_highscore` reads `deliveries` only when the seam is present (`app_controller.py:107-110`). The sim is frozen after game over, so the flip-frame value equals the old lagged value — no wrong value.
7. **max_frames / headless** — Not found. Reconcile records at the flip frame even on the `frames >= max_frames` boundary (record precedes the break at `main.py:276-279`). RL/headless surfaces don't use `run_game`, so they're unaffected.

### Benign observations (NOT bugs)
- The QUIT-gate `is_game_over` record/delete branch (`src/main.py:195-200`) is now unreachable in normal play (reconcile always promotes first). It's harmless defensive redundancy, correctly state-gated; could be simplified but the comment states the intent.
- Terminal-frame `renderer.draw(..., alpha=advance.alpha)` uses the pre-reset alpha — pre-existing behavior, unchanged by GM-07e, and interpolation is cleared on the terminal step anyway.

### One anomaly I ran down (so you can trust the conclusion)
A `Grep` rendered the reconcile call as `main.py:237: # controller.reconcile_game_over()` (looked commented-out, which would make the fix inert). Two authoritative `Read`s (`cat -n`) confirm line 236 is a LIVE `controller.reconcile_game_over()` and line 237 is `state = controller.state`. The passing `test_eventless_game_over_records_once_and_draws_indicator` (asserts `record.call_count == 1`, `best.call_count == 1`) independently proves the call executes — it would be red if commented. The grep output was a display artifact; the fix is active.

Tests run: `test_gm07e_game_over_reconcile`, `test_gm07a/c/d_run_game_loop`, `test_main` — 28 passed. (Green is not proof; the reasoning above is.)

Files examined: `src/app_controller.py`, `src/main.py`, `src/game_session.py`, `src/mediator.py`, `src/passenger_flow.py`, `src/input_coordinator.py`, `test/test_gm07e_game_over_reconcile.py`.

# GM-07e review — deterministic per-frame game-over reconciliation

Iteration 13 (2026-07-22). Change under review: commit `a720cf7` (`[GM-07e:A]`) — `src/app_controller.py`, `src/main.py`, `test/test_gm07e_game_over_reconcile.py`. Delivery base `28d86e5` (`origin/main`, GM-07d:D). See `diff.md`.

## What this closes

The GM-07d external Codex persistence lane flagged twice (iteration 12, `raw/codex.md` / `raw/codex-2.md`) that an eventless `PLAYING`->`GAME_OVER` transition records nothing and shows no best indicator until the next incidental event or the window-close QUIT — `main.run_game` drains events, then advances, with no post-advance reconciliation, so a tick that flips `mediator.is_game_over` leaves the controller in `PLAYING`. That MAJOR was accepted at GM-07d as consistent with D-027's window-close net, with a deterministic-per-frame reconciliation filed as a follow-up chip (STATE.md). This unit lands that chip.

The window-close net was judged sufficient at iteration 12; on re-evaluation it is not, for the common case: the D-028 "new best" indicator, in the natural flow (run ends on a tick, player immediately presses Restart), records-and-leaves in the same event so the indicator never renders a frame — the QUIT net only records on exit and never shows the indicator during play. Plus a windowed / `max_frames` `run_game` records zero on an eventless game-over. The fix is small and mutual-exclusion-preserving, so it was implemented rather than closed with rationale.

## The change

Extract the promotion block out of `AppController.handle_event` into a public idempotent `reconcile_game_over()` (no-op unless still `PLAYING` and `mediator.is_game_over is True`; else `GAME_OVER`, delete autosave, record score). `handle_event` calls it at its top (historical inline promotion preserved); `main.run_game` calls it once per frame after `session.advance` with a render-state re-read. Mutually exclusive with the window-close QUIT record, which fires only while the state is still `PLAYING`/`PAUSE_MENU` — now closed first by the reconcile.

## Review lanes

Three independent adversarial lanes, each reading live code (locally-high-risk boundary: `main.run_game` + `AppController` public surface).

- **Codex `gpt-5.6-sol` / reasoning=ultra, read-only sandbox** (`raw/codex.md`): VERDICT NOT CLEAN, but "No zero-record, double-record, stale-state render, session-swap, advance-argument, or truthy-MagicMock defect was found in the live implementation." All findings are doc-currency and test-strengthening.
- **Harness correctness lens** (`raw/harness-correctness.md`): NO DEFECT. Verified the load-bearing invariant against live code — `is_game_over` is written `True` at exactly one site (`passenger_flow.py:463`, tick-only via `advance`), never on the event-dispatch path — so the per-frame reconcile always promotes on the flip frame and the QUIT gate's record branch is defensively redundant. Traced 0/1/2+-event frames, session-swap, PAUSE_MENU, max_frames.
- **Harness regression / test-quality lens** (`raw/harness-regression.md`): NO CONFIRMED REGRESSIONS. Empirically re-verified red-first by reverting the `main.py` change in place and restoring byte-identically. Confirmed the `is True` identity guard makes reconcile a no-op for every MagicMock mediator and every `test_main` mediator also sets `is_game_over=False`.

## Findings and dispositions

| # | Lane | Sev | Finding | Disposition |
| --- | --- | --- | --- | --- |
| 1 | Codex | MAJOR | STATE.md still directs work to GM-07d:B (already HEAD) and calls the reconciliation "merely filed" — following it resumes the wrong transaction. | FIXED in `[GM-07e:B]`: STATE.md reconciled — GM-07d finalized through :D on `origin/main`, GM-07e set as current substep. |
| 2 | Codex | MINOR | `main.py` comment claimed "headless/RL runs record"; RL/agent/recursive surfaces never enter `run_game`. | FIXED in `[GM-07e:A]`: comment reworded to "the record no longer waits on an incidental event." |
| 3 | Codex | MINOR | ARCHITECTURE.md:374 omits the new post-advance `main -> reconcile_game_over` flow; PROGRESS leaves it a follow-up. (README:65/223, GAME_RULES:106 confirmed already accurate.) | FIXED in `[GM-07e:B]`: ARCHITECTURE clause + PROGRESS bullet added. |
| 4 | Codex | MINOR | Run-loop test made `renderer.draw` a no-op and did not pin indicator-after-frame order — a banner-before-frame regression would pass. | FIXED in `[GM-07e:A]`: `_LoopRenderer` logs its draw; Test A asserts `draw_log == ["renderer", "best"]`. |
| 5 | Codex / harness TQ-1 | MINOR | Mutual-exclusion test's `record.call_count == 1` passes even with the fix reverted (the QUIT gate records once on its own); it did not pin WHICH surface recorded, nor that no autosave is recreated on the QUIT. | FIXED in `[GM-07e:A]`: Test B now asserts the recorded arg has no `is_game_over` (reconcile's namespace, not the QUIT gate's mediator) and `write.call_count == 0`. Red-first re-verified: with the per-frame reconcile disabled, the surface discriminator flips (`AssertionError: True is not false`). |
| — | harness | INFO/PLAUSIBLE | QUIT-gate game-over branch now defensively redundant; controller tests structurally red-first via `hasattr`; intra-frame `[event, quit]` sound by idempotency but untested. | ACCEPTED with note: the QUIT branch stays (correct, D-027-consistent, pinned by GM-07c/d window-close tests); the intra-frame edge is covered in pieces by `test_reconcile_is_idempotent`, `test_handle_event_promotion_still_records_via_reconcile`, and GM-07d `test_quit_when_already_promoted_does_not_double_record`. |

No correctness defect survived any lane. All five actionable findings folded.

## Gates (delivery base `28d86e5`)

- Full `py313` unittest: **1231 passed, 12 skipped, 0 failed**.
- Changed-file `ruff check`, `ruff format --check`, per-file `pre-commit`: clean, no hook auto-fixes.
- Red-first evidence captured before implementation (9 failures) and re-verified for the strengthened assertions (per-frame reconcile disabled → both run-loop tests fail, incl. the surface discriminator).
- Guarded `npm test` is unavailable in this nested worktree (civ-engine resolution shadow: "pinned civ-engine checkout is unavailable") — a pre-existing environmental limitation, not caused by this Python-only change, which touches no loop machinery; validated by hosted CI (`test.yml`) on push.

**VERDICT: CLEAN after folding findings 1-5.**

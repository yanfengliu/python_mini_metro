## CONFIRMED defects

1. **MAJOR — durable resume state is stale.** [STATE.md:9](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:9), lines 23–25, 38, 82, and 131 still direct work toward GM-07d:B and describe deterministic reconciliation as merely filed. GM-07d:B is already HEAD (`60f59c0`), and GM-07e is implementing that reconciliation. Following these instructions would resume the wrong transaction.

2. **MINOR — false runtime-scope claim.** [src/main.py:233](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/src/main.py:233) says this makes “headless/RL runs record.” Only `main.run_game`/`AppController` records; RL, agent, recursive, and structured environments never enter this controller, as [ARCHITECTURE.md:374](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/ARCHITECTURE.md:374) itself states.

3. **MINOR — required architecture/progress documentation is missing.** [PROGRESS.md:160](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/PROGRESS.md:160) explicitly leaves per-frame reconciliation as a follow-up, while [ARCHITECTURE.md:374](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/ARCHITECTURE.md:374) omits the new post-`advance` `main → reconcile_game_over` flow. README:65/223 and GAME_RULES:106 are now accurate.

4. **MINOR — indicator visibility/order is not pinned.** [test_gm07e_game_over_reconcile.py:304](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/test/test_gm07e_game_over_reconcile.py:304) makes renderer drawing a no-op, while lines 383–392 assert only indicator invocation/result. Moving `draw_best_indicator` before `renderer.draw` would still pass, although the banner could be overwritten. Current production order is correct.

5. **MINOR — the mutual-exclusion test ignores autosave writes.** [test_gm07e_game_over_reconcile.py:334](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/test/test_gm07e_game_over_reconcile.py:334) discards the `write_autosave` mock, and the returned spies at line 367 omit it. A regression that recreates an autosave on the follow-up QUIT would pass lines 397–416.

## PLAUSIBLE concerns

- Literal “no double-delete” semantics conflict with existing D-027 behavior: reconciliation calls delete at [app_controller.py:131](/C:/Users/38909/Documents/github/python_mini_metro/.claude/worktrees/trusting-archimedes-dee34b/src/app_controller.py:131), then Escape/click Exit deletes again at lines 246/256. Direct probe: delete count `1 → 2`, record count remains `1`. Existing GM-07c tests intentionally pin this defense-in-depth behavior, and production deletion is idempotent; reconciliation versus `pygame.QUIT` itself is correctly mutually exclusive.

- Delivery validation is not final: HEAD is two commits behind `origin/main`. The requested 28-test command produced 14 passes and 14 environment errors because this read-only sandbox has no writable temporary directory—not product failures, but not a green gate. All eight GM-07e tests passed with a no-I/O temp shim; the no-op reconciliation mutation produced the expected red results. Changed-file Ruff, format, and `git diff --check` passed; full-suite and pre-commit gates remain unproven here.

No zero-record, double-record, stale-state render, session-swap, advance-argument, or truthy-`MagicMock` defect was found in the live implementation.

**VERDICT: NOT CLEAN**

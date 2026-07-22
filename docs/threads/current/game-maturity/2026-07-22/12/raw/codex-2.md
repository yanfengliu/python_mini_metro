All six targeted fixes are resolved, but the overall change remains not clean because an earlier major recording defect is still reachable.

## Fix verification

1. **CONFIRMED-RESOLVED — invalid persistence.** Input guards run at [src/highscores.py:119](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:119), and save validation precedes all filesystem operations at [src/highscores.py:199](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:199). Probes confirmed `-1`, `True`, `3.0`, and `"3"` all raise `ValueError`; saving a negative-deliveries document preserved an existing valid file byte-for-byte and left no temporary litter.

2. **CONFIRMED-RESOLVED — cross-key isolation.** [src/highscores.py:127](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:127) sorts the board, while lines 133–155 cap only the recorded key. An unsorted 11-entry `beta` group retained all 11 entries after recording `classic`; it was canonically re-sorted descending, which is acceptable normalization rather than data loss. The `classic` group remained capped at ten with correct rank and `is_best`.

3. **CONFIRMED-RESOLVED — required keys.** The signature at [src/highscores.py:100](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:100) requires keyword-only `map` and `rules_version`; omitting them raises `TypeError`. The sole production call supplies both explicitly at [src/main.py:58](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:58).

4. **CONFIRMED-RESOLVED — one patchable recorder.** [src/main.py:48](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:48) is the single persistence function. Promotion resolves it dynamically through [src/main.py:165](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:165), and QUIT calls it at [src/main.py:200](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:200). Patching `main.record_highscore` intercepted each implemented surface exactly once; `_record_deliveries` is absent. Promotion passes a `SimpleNamespace` while QUIT passes the mediator, but both expose the same deliveries scalar—the only attribute `record_highscore` reads.

5. **CONFIRMED-RESOLVED — read-only test.** [test/test_gm07d_run_game_loop.py:209](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07d_run_game_loop.py:209) exercises the real recorder through a temporary path, verifies the persisted deliveries, and asserts the mediator’s state dictionary remains unchanged. The test is meaningful.

6. **CONFIRMED-RESOLVED — writer documentation.** [README.md:223](/C:/Users/38909/Documents/github/python_mini_metro/README.md:223) and [DECISIONS.md:179](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:179) now accurately describe a save-local copy. That matches the re-inlined writer at [src/highscores.py:189](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:189).

## Remaining findings

- **MAJOR — STILL-BROKEN prior finding: eventless game over records zero times.** Promotion occurs only inside `AppController.handle_event` at [src/app_controller.py:117](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:117). The loop processes events first, then calls `session.advance()` at [src/main.py:222](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:222), with no post-advance reconciliation. A two-frame probe where the first advance set `is_game_over=True` and both event queues were empty produced zero recorder calls. The controller remained `PLAYING`, so the best indicator was also skipped.

- **MAJOR — STILL-BROKEN process finding.** [STATE.md:11](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:11), lines 38 and 82 still claim review-clean/external approval despite the prior `raw/codex.md` verdict and the unresolved defect above.

- **MINOR — documentation drift introduced by the fixes.** [EVIDENCE.md:921](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/EVIDENCE.md:921) still claims `record_score` has default map/rules arguments and reports obsolete line counts; [ARCHITECTURE.md:387](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:387) and [PLAN.md:15](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-22/12/PLAN.md:15) still attribute the `SAVE_RULES_VERSION` import to `highscores.py`. Live ownership is correctly in `main.py`; repository search and isolation tests found no runtime break.

Other requested checks passed: producer-generated boards validate and round-trip; normal deliveries remain nonnegative integers; all changed Python files are below 500 lines; `game_renderer.py` remains 494 lines and byte-identical to `HEAD`.

Validation: 45 focused tests passed; full suite passed **1216 tests with 12 expected skips**; Ruff check, Ruff format check, and `git diff --check` passed.

**VERDICT: NOT CLEAN**

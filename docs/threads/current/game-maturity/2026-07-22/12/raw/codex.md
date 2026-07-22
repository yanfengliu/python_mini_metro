## Findings

- **MAJOR — Game over can record zero times.** [src/main.py:185](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:185) drains events before `session.advance`; promotion exists only in [src/app_controller.py:117](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:117). If that advance causes game over and no later event arrives, the renderer shows Game Over while controller state remains `PLAYING`; no score is recorded and no best indicator appears. A first post-over Restart/Exit event records and immediately leaves the screen, so the indicator is never shown. This contradicts `PLAN.md:35-36`, D-028, `README.md:65,223`, and `GAME_RULES.md:106`.

- **MAJOR — Public write APIs can replace a valid leaderboard with an invalid one.** [src/highscores.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:115) does not validate new fields, and [src/highscores.py:182](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:182) serializes without calling `validate_highscores`. `record_score(empty, deliveries=-1)` returns rank 1/best; saving it replaces the prior valid file, after which `load_highscores` rejects it and starts empty. Non-ASCII identifiers behave likewise; NaN is serialized as `{"$nonFinite":"NaN"}` through [recursive_checkpoint_schema.py:46](/C:/Users/38909/Documents/github/python_mini_metro/src/recursive_checkpoint_schema.py:46).

- **MAJOR — Recording one key can reorder or delete another accepted key.** [src/highscores.py:85](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:85) accepts unsorted and over-cap groups, while [src/highscores.py:118](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:118) globally sorts and caps every group. A validated board with beta scores `[1,9]` becomes `[9,1]` when recording classic; a validated 11-entry beta group loses an entry. That violates cross-key isolation.

- **MAJOR — Review status was pre-approved and is false.** [STATE.md:11](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:11), lines 38 and 82 already call GM-07d review-clean and claim the external Codex lane passed. At inspection, its stdout was empty and iteration 12 had no `REVIEW.md`; this review is `NOT CLEAN`. [EVIDENCE.md:922](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/EVIDENCE.md:922) also records “zero findings” despite the reproducible validation and isolation failures above.

- **MINOR — `validate_highscores` can leak `TypeError`.** [src/highscores.py:80](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:80) delegates to [save_schema_records.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema_records.py:115), whose sorting of unknown keys fails when they contain both strings and integers. A document with unknown keys `0` and `"extra"` raises `TypeError`, violating the ValueError-only contract.

- **MINOR — Early writer failure leaks the raw descriptor.** [src/highscores.py:185](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:185) does not protect ownership of the `mkstemp` descriptor before `os.fdopen` succeeds. An `os.fdopen` failure leaves it open; on Windows the unlink can then fail, masking the original error and leaving the temp file.

- **MINOR — Map and rules identity can be omitted silently.** [src/highscores.py:104](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:104) defaults both keys despite the folded plan requiring them. Calling `record_score(beta_rules_v2_board, deliveries=7)` silently creates a `classic/rules-v1` group instead of failing fast. Current `main` passes both explicitly.

- **MINOR — The advertised patchable recorder covers only QUIT.** [src/main.py:164](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:164) wires normal promotion to private `_record_deliveries`; public `record_highscore` is used only at line 196. Patching `main.record_highscore` does not intercept ordinary promotion and real persistence still runs.

- **MINOR — Required regression validation is missing.** [test_gm07d_recorder_controller.py:155](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07d_recorder_controller.py:155) checks only the scalar passed and result returned; it lacks PLAN.md:27’s checkpoint-unchanged/mediator-read-only assertion. The isolation scan at [test_gm07b_save_determinism.py:303](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:303) also misses `import src.highscores`, `from src import highscores`, and relative imports.

- **MINOR — Writer documentation is contradictory.** `DECISIONS.md:179,181` and `README.md:223` claim the exact/same GM-07b writer is reused and avoids a parallel writer, while [src/highscores.py:174](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:174) contains a second inlined implementation.

## Verified sound

- All enumerated malformed/BOM/non-ASCII/duplicate/forward/deep/top-level-type inputs start empty; both `map` and `rulesVersion` reject escaped non-ASCII content.
- For recorder-generated valid boards, purity, stable ties, ordering, per-key cap, ranks, zero-first, and best semantics are correct.
- Valid saves are ASCII, sorted-key, compact, CR-free, and end in one LF. Normal replace failure preserves the prior file; parent creation and same-directory temp placement are correct.
- Once either lifecycle gate is actually reached, promotion and QUIT are mutually exclusive; load/record/save `Exception`s, including `RecursionError`, are swallowed.
- Current forbidden runtime surfaces import no persistence modules; checkpoint, observation, protocol, and frozen fixture content are unchanged.
- `game_renderer.py` is byte-identical to `HEAD` and remains 494 lines. All changed handwritten files remain below 500 lines.

**VERDICT: NOT CLEAN**

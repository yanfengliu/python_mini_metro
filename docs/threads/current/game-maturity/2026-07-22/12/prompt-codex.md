You are an adversarial code reviewer for a Python 3.13 pygame-ce Mini Metro implementation. Review the UNCOMMITTED working-tree change GM-07d (a map/rules high-score leaderboard) against the LIVE code. Your job is to REFUTE its correctness, not to approve it. Green tests already pass; that is not evidence of correctness.

Read these first for the binding contract:
- docs/threads/current/game-maturity/2026-07-22/12/PLAN.md (the folded plan; D-028 policy)
- docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md (search "D-028")

The change under review (read the live files; use `git diff` for the modified ones):
- src/highscores.py (NEW) — the leaderboard document type, strict validation, ranked insertion, atomic persistence. Reuses save-schema validators + canonical_save_bytes from src/save_schema.py / src/save_schema_records.py / src/save_game.py / src/save_load.py.
- src/app_controller.py — new optional `highscores` recorder seam; records at the PLAYING->GAME_OVER promotion into public `last_highscore_result`.
- src/main.py — binds the seam + patchable HIGHSCORES_PATH/record_highscore; window-close game-over record; best-indicator draw.
- src/ui/menu_screens.py — new byte-stable draw_best_indicator primitive.
- Docs: README.md, GAME_RULES.md, ARCHITECTURE.md, PROGRESS.md.
- Tests: test/test_gm07d_*.py (4 new), and the required edits to test/test_gm07b_save_determinism.py (isolation scan) and test/test_gm07c_run_game_loop.py.

Attack these dimensions specifically and report concrete defects with file:line and a failing scenario:
1. Persistence correctness: the inlined atomic writer (mkstemp -> fsync -> os.replace -> finally unlink) — is an interrupted write truly non-destructive of the prior valid file? Any fd/tempfile leak, wrong dir for os.replace atomicity (same-filesystem), missing parent-dir creation, or non-canonical bytes (must be ASCII, sorted keys, single trailing LF, no CR, no NaN/Inf)?
2. Validation strictness vs the start-empty stance: validate_highscores must do exact-key checks BEFORE field access (no KeyError/TypeError escaping as something other than ValueError). load_highscores must START EMPTY on ANY Exception (including RecursionError from deep nesting) and NEVER raise. Is there any input (missing/truncated/non-JSON/BOM/non-ASCII byte/non-ASCII \u-escape in map or rulesVersion/duplicate key/forward schemaVersion/deeply nested/null/array-top/number-top) that either crashes OR is wrongly accepted? Scrutinize the implementer deviation `_ascii_string` (content-level ASCII enforcement) for completeness on BOTH map and rulesVersion.
3. record_score purity + ordering + cap: must return a NEW document (never mutate input); canonical order (map asc, rulesVersion asc, deliveries desc, ties stable-over-append); per-(map,rulesVersion) cap exactly 10; cross-key isolation (recording under one key must never reorder/drop another key); rank 1-based within key, None beyond cap, is_best == (rank==1); tie-with-best -> rank 2 not best; empty-board-first -> rank 1 best even at deliveries 0. Find any sequence that violates these. Scrutinize the deviation where record_score gained default map/rules_version args — can any caller silently record under the wrong key?
4. Exactly-once + no-crash: the record must fire exactly once per game across the PLAYING->GAME_OVER promotion AND the window-close-at-game-over path in main, mutually exclusive (no double record). A failure inside record_highscore (load/save raising, incl. RecursionError) must be swallowed and never crash or block play/exit. The controller must read mediator.deliveries ONLY when the seam is present.
5. Isolation: highscores.py (and any save module) must NOT be imported by env.py, agent_play.py, recursive_playtest.py, recursive_checkpoint.py, or rl/*. The persistence AST isolation scan in test_gm07b_save_determinism.py must include "highscores". Recording must mutate no mediator state and change no checkpoint/observation/frozen artifact.
6. Process/doc regressions: any stale or wrong statement in README.md / GAME_RULES.md / ARCHITECTURE.md / PROGRESS.md vs the implemented behavior; any missing validation; any file over 500 LOC (hard ceiling 1000); game_renderer.py must be byte-unchanged.

Do NOT modify any file. Output a structured report: SEVERITY (blocker/major/minor) per finding with file:line and a concrete failing input/scenario, a list of what you verified sound, and a final VERDICT line: CLEAN or NOT CLEAN. Be terse and concrete.

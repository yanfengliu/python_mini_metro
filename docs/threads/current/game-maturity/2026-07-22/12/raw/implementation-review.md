# GM-07d Adversarial Implementation Review (harness lane) — VERDICT: CLEAN

Reviewed against the pre-fold baseline (before the external Codex persistence lane's findings were folded). This lane ran nine standalone probes plus a real windowed run and returned zero findings. NOTE (added at synthesis): this lane only ever exercised recorder-generated (already-canonical) boards, so it did not reach the cross-key and misuse paths the external Codex lane (`raw/codex.md`) later surfaced; it is preserved verbatim here as the record of what the harness lane did and did not cover.

Reviewed `src/highscores.py` (197), `src/app_controller.py` (244), `src/main.py` (274), `src/ui/menu_screens.py` (185), the docs, and the two required test edits against PLAN.md (folded D-028 policy), `raw/plan-review-combined.md`, and D-028. Green was not trusted.

## Attack results (all probes PASS)

**1. `highscores.py` core logic**
- validate_highscores fuzz (`probe1_validate_fuzz.py`): permuted/deleted/retyped every top-level and entry key with 17 adversarial values each. Every structural break raises `ValueError` — zero KeyError/TypeError/RecursionError escapes, confirming the exact-key-check-before-field-access ordering. Bool-as-int deliveries (`True`/`False`), negatives, non-ASCII map and rulesVersion, and forward/backward `schemaVersion` (incl. float `1.0`) all rejected.
- record_score (`probe2_record_score.py`, `probe2b_cap_stress.py`): PURITY verified over 500 random docs (input byte-identical via json + deep-eq; output entries non-aliased). 300 randomized sequences (≤40 records) cross-checked against a reference model for canonical order (map asc, rules asc, deliveries desc, stable-over-append), per-key cap exactly 10, 1-based rank / `None` beyond cap / `is_best == (rank==1)`, cross-key isolation. Pinned semantics confirmed: tie-with-best→rank 2/not-best, empty-board-first→rank 1/best even at deliveries 0, 11th-lower drops, 11th-higher evicts lowest. Incremental cap-drop proven equal to global stable top-K under heavy ties (caps 1/2/3/5 × 400 trials). [NOTE: these probes used only recorder-generated canonical boards — the externally-non-canonical cross-key path was NOT exercised here.]
- load_highscores START-EMPTY (`probe3_load_save.py`, subprocess): returns a fresh canonical empty doc (no singleton aliasing) and never raises on missing/truncated/non-JSON/BOM/non-ASCII(bytes and `\u`-escape, both fields)/dup-key/forward-version/wrong-contract/null-bytes/empty/`null`/array-top/number-top and the 200k-deep nested array (RecursionError) — exit code 0, no segfault.
- save_highscores atomicity: canonical ASCII + single trailing LF, no CR; parent dirs auto-created; injected `os.replace` failure → OSError raised, prior file byte-intact, zero `.tmp` litter; save→load round-trips.

**2. Exactly-once + no-crash across surfaces** (`probe4a_controller.py`, `probe4b_mainloop.py`): promotion records `mediator.deliveries` exactly once; no re-record on later GAME_OVER events; `last_highscore_result` (re)assigned every promotion and cleared when a record returns None; a seam-less controller with a `deliveries`-raising mediator promotes without touching `deliveries`. Window-close at game-over writes one real entry; a promoting-event-then-QUIT records once via the seam with the window-close path skipped (mutual exclusion); TITLE / already-GAME_OVER / un-over-PLAYING window-close record nothing; a `RecursionError` in the real `record_highscore` is swallowed while `SystemExit` still propagates.

**3. Real windowed run** (`probe5_windowed.py`, SDL dummy, real `set_mode` → 1920×1080): a real Mediator/GameRenderer/GameSession played to real game-over. Run 1 (best) paints "NEW BEST" composited over the untouched `game_renderer` game-over overlay (`run1_best.png`); run 2 (worse) shows no indicator (`run2_worse.png`). A real `highscores.json` written to a temp path: 194 bytes, trailing LF, no CR, canonical sorted keys, 2 entries ranked `[15,4]` keyed `classic`/`rules-v1`. No real `./saves` leaked. `game_renderer.py` byte-unchanged from HEAD (empty diff, 494 lines).

**4. Suite filesystem safety**: full `python -m unittest` → 1211 OK (skipped=12); `./saves` did not exist before and does not exist after.

**5. Isolation/determinism**: `highscores` imported only by `main.py`; `app_controller` uses the injected seam; `env.py`/`agent_play.py`/`recursive_playtest.py`/`recursive_checkpoint.py`/`rl/*` import neither `highscores` nor any save module; the AST isolation scan adds `"highscores"` to `SAVE_MODULE_NAMES`. `canonical_checkpoint` byte-identical across records and `mediator.deliveries` unchanged (`probe6_checkpoint.py`). No checkpoint/observation/frozen-artifact file touched.

**6. Doc honesty**: README, GAME_RULES, ARCHITECTURE, PROGRESS matched the (pre-fold) implemented behavior.

**7. Deviation scrutiny** — both sound at the time: `_ascii_string` content-level rejection complete for both map and rulesVersion; `record_score` default args keyword-only with the sole production caller passing both explicitly. [The default-args deviation was later reverted during the Codex fold, MINOR-3.]

## Findings
None at this lane's coverage. VERDICT: CLEAN. (Superseded by the external Codex persistence lane `raw/codex.md`, which reached the recorder-only-missed paths.)

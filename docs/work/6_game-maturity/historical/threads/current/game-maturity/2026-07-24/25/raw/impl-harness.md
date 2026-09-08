# GM-09f2 Adversarial Implementation Review — harness general-purpose lane (agentId aa02e9416d9583230)

**Verdict: SHIP.** No BLOCKER, MAJOR, MINOR. One intentional NIT (adjudicated in PLAN v2). Every load-bearing claim was reproduced against live code, not taken on faith.

## Evidence base
- Targeted suite `test_gm09f2_highscore_map test_gm07d_highscores test_gm07d_recorder_controller test_gm07d_run_game_loop test_gm07e_game_over_reconcile` — **53 pass**.
- **Full suite: 1459 pass, 12 skipped** (SDL dummy drivers).
- **45 hand-forged probes** (`record_score` across versions, `main.record_highscore` with SimpleNamespace mediators, `load_highscores` on forged v1/v3/bad boards, `_map_id` vs `save._validate_map_identity` across a 26-seed corpus, real `Mediator`) — **all pass**.
- `ruff check` + `ruff format --check` on all 8 changed files — clean.

## Findings per attack vector

**1. SEAM / MAJOR-3 / mutual-exclusion — NO FINDING.**
`app_controller._record_highscore` now passes `self.mediator` (a reference, no attribute access); a seam-less controller (`self._highscores is None`) still reads NOTHING off the mediator — MAJOR-3 holds *more* cleanly than at GM-07d. Both game-over surfaces funnel identically: the promotion via `_record_promotion(mediator)→record_highscore(mediator)` and the window-close QUIT via `record_highscore(controller.mediator)`. Mutual exclusion is unchanged: `reconcile_game_over` promotes only `PLAYING`→`GAME_OVER`, after which the QUIT gate can never fire; a same-frame QUIT is processed before advance/reconcile and exits first. In production only real `Mediator`s (always carry deliveries + map_definition) reach the recorder. The test_gm07e distinguisher swap (removing `assertFalse(hasattr(recorded_arg,"is_game_over"))`, now `best.call_count == 1`) is SOUND: I traced both worlds — correct code yields record=1/best=1; a no-reconcile baseline yields record=1/best=0, so the proof still flips red at baseline and uniquely identifies the reconcile.

**2. record_highscore fail-safe — NO FINDING.**
The `try` wraps the `mediator.deliveries` and `mediator.map_definition` reads; `save_highscores` is the last statement, so any earlier raise writes nothing. Probes: missing `map_definition` → None+no-write; missing `deliveries` → None+no-write; `map_id=""`/`"rivér"` (record_score raises pre-save) → None+no-write; valid classic → `classic@1`; valid river → keyed `river`. The direct read with no `or classic` is the correct fail-SAFE per the GM-09f `or DEFAULT` lesson.

**3. `_identity` for RANK/CAP/SORT — NO FINDING.**
`target = (map, map_definition_version, rules_version)` equals `_identity(entry)` exactly, and one `_identity` helper backs `_sort_key`, the cap loop, and the rank loop — they cannot disagree. Probes: `classic@1=[100]` + `classic@2=1` → **rank 1 / is_best True**; `classic@1` over-cap (11) + `classic@2` → `classic@1` group **stays 11**; a mid `classic@2` (75) among [100,75,50] ranks 2. `item is entry` is unambiguous (existing entries dict-copied, new entry appended by reference).

**4. record_score validation + grammar parity — NO FINDING.**
`map_definition_version` keyword-only, no default → TypeError when omitted. `_positive_int` rejects 0/-1/True/1.0/"1"; `_map_id` rejects ""/"a b"/"rivér"/non-str — enforced identically in `record_score` AND `validate_highscores`. `_map_id` is a true mirror of `save_schema._validate_map_identity`: **zero acceptance mismatches across a 26-seed corpus**.

**5. START-EMPTY on v1, NO migration — NO FINDING.**
`load_highscores` is decode→validate-as-v2→return, else `_empty_document()` (v2). Probes: v1 board → empty; forward v3 → empty; v2 with extra top key → empty; v2 with `mapDefinitionVersion=0` → empty; **`schemaVersion=True`/`1.0` → empty (NOT normalized)**. `grep` confirms no `_migrate` symbol in `src/`.

**6. Schema v2 exactness — NO FINDING.**
Rejects schemaVersion ∈ {1, 3, 0, True, "2", 2.0, None}, missing/extra top keys, missing/extra entry keys, bad `mapDefinitionVersion`, bad `map` grammar. `HIGHSCORES_STATE_CONTRACT` stays `"mini-metro-highscores-v1"`; `_empty_document()` emits v2.

**7. Blast radius — NO FINDING.**
AST import scan confirms `highscores.py` pulls in no `maps`/`pygame`/`mediator`/`entity`. `draw_best_indicator` reads only `result.is_best` — map-agnostic. The RL/headless isolation scan passes. Repo-wide sweep: the only `record_score`/`record_highscore`/highscores-seam callers are the 8 files in this change. Save fixtures untouched.

**8. Test surgery — NO FINDING.**
The two local spies now take `record(self, mediator)` and append `mediator.deliveries`, still pinning the objective ([42], [7,7]). `test_gm07d_run_game_loop` stubs gained `map_definition` and assert the recorded `map`/`mapDefinitionVersion`, plus a missing-`map_definition`→None case; the RecursionError swallow drives the real recorder. The gm07d_highscores v2 corpus is complete. `test_gm09f2` covers map-threading (classic + river), cross-version rank/cap isolation, and v1→START-EMPTY.

## The one NIT (intentional, non-blocking)
`HIGHSCORES_MAP_CLASSIC = "classic"` is now unused by any producer but deliberately retained (public constant asserted by `test_versioned_constants`, harmless). No action required.

## Docs — consistent
D-039, README, GAME_RULES, ARCHITECTURE all updated; every "migrate" mention is negated ("NOT migrated"/"starts empty"); ARCHITECTURE's two stale boundary descriptions (scalar seam; schema-v1 three-field identity) corrected to the live-mediator seam and the v2 triple key.

**FINAL: SHIP.**

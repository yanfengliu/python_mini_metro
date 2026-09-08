# GM-09f2 — high-score map identity (D-039)

**Roadmap:** GM-09f split, sub-unit 2 of 3 (save-schema ✓ → **high-score identity** → in-game menu). The menu (GM-09f3) lands LAST so it can never expose an alternate map to a still-classic-hardcoded recorder — so GM-09f2 must make the recorder map-aware NOW, while every game is still classic (no menu yet), so GM-09f3 needs zero recorder change.

## Problem

The leaderboard schema already keys entries by `(map, rulesVersion)` (GM-07d), but two things are classic-only:
1. `main.record_highscore` hardcodes `map=HIGHSCORES_MAP_CLASSIC` — it never reads the game's real map.
2. The entry records `map` (id) but not `mapDefinitionVersion`, so a hypothetical `classic@2` (a future terrain revision) would rank against `classic@1` — the same trajectory-incomparability D-026/D-038 guard against for saves.

The recorder has a subtle asymmetry: the window-close path (`main.py:311`) passes the real `controller.mediator`, but the promotion seam (`main.py:247`) passes `SimpleNamespace(deliveries=deliveries)` — the controller seam (`app_controller._record_highscore`) hands the seam only `self.mediator.deliveries` (a scalar), so the promotion path structurally cannot see the map.

## Design (chosen)

**Unify both game-over paths on the real mediator** (the window-close path already does this), so `record_highscore` reads deliveries + map identity from one place.

### 1. Controller seam — `app_controller._record_highscore` (app_controller.py:134)
- Pass `self.mediator` (the object) to the seam instead of `self.mediator.deliveries`:
  `self.last_highscore_result = self._highscores.record(self.mediator)`.
- MAJOR-3 (GM-07d) is satisfied MORE cleanly: the controller now reads NO mediator attribute — the seam does — so a seam-less controller still touches nothing. Update the comment.
- Seam contract: `record(mediator) -> RecordResult | None` (was `record(deliveries)`).

### 2. `main.run_game` promotion closure (main.py:246)
- `_record_promotion(mediator) -> record_highscore(mediator)` — drop the `SimpleNamespace(deliveries=...)` wrapper entirely. Both game-over surfaces now call `record_highscore(<the real mediator>)` identically.

### 3. `main.record_highscore(mediator)` (main.py:119)
- Read the live map: `map_definition = mediator.map_definition`; `deliveries = mediator.deliveries`.
- `record_score(document, deliveries=deliveries, map=map_definition.map_id, map_definition_version=map_definition.map_definition_version, rules_version=SAVE_RULES_VERSION)`.
- Drop the `HIGHSCORES_MAP_CLASSIC` import + hardcode. A real `Mediator` ALWAYS has `map_definition` (default CLASSIC, GM-09a); an exotic mediator lacking it raises → the existing try/except swallows to `None` (fail-SAFE: no record, never a wrong one — consistent with the cosmetic-leaderboard contract). No `or classic` default (per the GM-09f `or DEFAULT` fail-open lesson — the attribute is guaranteed on the real type).

### 4. `highscores.py` — schema v2 (the migration)
- `HIGHSCORES_SCHEMA_VERSION = 2`; keep a `HIGHSCORES_SCHEMA_VERSION_V1 = 1` reference for the migration. `HIGHSCORES_STATE_CONTRACT` UNCHANGED (`mini-metro-highscores-v1` — a stable contract id across the additive version, exactly as the save kept `mini-metro-save-v1` across schema v1→v2).
- `_ENTRY_KEYS = {map, mapDefinitionVersion, rulesVersion, deliveries}` (adds `mapDefinitionVersion`).
- `validate_highscores`: accepts ONLY v2; each entry's `mapDefinitionVersion` is `_positive_int` (rejects bool/0/neg/non-int, mirroring the save's `mapDefinitionVersion`).
- `record_score(*, deliveries, map, map_definition_version, rules_version)`: entry gains `mapDefinitionVersion`; the target key + `_sort_key` become `(map, mapDefinitionVersion, rulesVersion, -deliveries)`; the per-key cap keys on the full `(map, mapDefinitionVersion, rules_version)` triple. `map_definition_version` is required (never defaulted — mirrors the GM-07d `map`/`rules_version` MINOR-3 rule).
- `load_highscores`: MIGRATE a v1 board — if `schemaVersion == 1`, synthesize `mapDefinitionVersion = 1` on every entry and bump to 2 BEFORE validating (preserves the player's classic history, mirroring the save v1→v2 `classic@1` synthesis); on any failure still START-EMPTY. A forward version (≥3) or a malformed v1 still starts empty. `_empty_document()` emits v2.
- `_migrate_v1_document(document)`: the pure in-memory v1→v2 transform, applied only inside `load_highscores`'s try (so a malformed v1 still starts empty, never raises).

### 5. Isolation
`highscores.py` stays gameplay-free — `record_score` takes `map_definition_version` as a plain int; the migration synthesizes the literal `1`; no `maps` import. `highscores` remains in the persistence isolation set (unchanged scan).

## TDD (red first)

New `test/test_gm09f2_highscore_map.py`:
- **Recorder threads the live map**: drive the REAL `main.record_highscore` with a stub carrying `deliveries` + `map_definition` (classic AND a non-classic e.g. river) → the recorded entry has the right `map`/`mapDefinitionVersion`; a classic mediator records `classic`/`1`.
- **Both game-over paths agree**: the controller seam (`record(mediator)`) and the window-close call both reach `record_highscore(mediator)` with the same object (assert the promotion no longer wraps deliveries).
- **Schema v2 round-trip**: a v2 board validates; `mapDefinitionVersion` strictness (bool/0/neg/non-int rejected; missing rejected; unknown key rejected).
- **v1→v2 migration**: a v1 board (no `mapDefinitionVersion`) loads MIGRATED (entries gain `mapDefinitionVersion=1`, schemaVersion=2, classic scores preserved, ranking intact); a malformed v1 still starts empty; a forward v3 starts empty.
- **Cross-identity isolation**: recording `classic@2` never evicts a `classic@1` over-cap group (the cap keys on the full triple).
- **`record_score` requires `map_definition_version`** (TypeError when omitted).

Touched: `test_gm07d_highscores.py` (v2 entries: `_entry`/`_valid_doc`/`_record`/`_group` gain `mapDefinitionVersion`; `HIGHSCORES_SCHEMA_VERSION`→2; header-strictness forward-version 2→3; the canonical-order + cap + cross-key tests carry the new field). `test_gm07d_recorder_controller.py` (`_SpyHighscores.record(self, mediator)` records `mediator.deliveries`; assertions unchanged at `[42]`/`[7,7]`; `_DeliveringMediator` needs NO map_definition — the spy doesn't read it). `test_gm07d_run_game_loop.py` — UNCHANGED (already `assert_called_once_with(mediator)`).

## Docs
- D-039 (this decision) in DECISIONS.md.
- README (leaderboard "keyed by `(map, mapDefinitionVersion, rulesVersion)`"; the recorder reads the live map; v1→v2 migration).
- GAME_RULES (high-score identity now includes the map + its version).
- ARCHITECTURE (only if a boundary changes — likely wording only).
- PROGRESS (one bullet, 2026-07-24).

## Risk / review
HIGH-RISK (persistence migration + a public recorder seam + the two-path asymmetry + the MAJOR-3 invariant) → dual PLAN review then dual IMPL review; treat byte/migration/misuse probes as load-bearing (memory `gm07d-review-coverage-lesson`: the leaderboard is exactly where the external lane has caught cross-key data-loss before).

## Order
schema v2 + migration + record_score (red tests) → recorder + controller seam → docs → dual impl review → A (CI) → B.

---

## PLAN v2 — folds (after dual plan review)

Both lanes **REVISE**, both VALIDATED the core design (whole-mediator seam preserves MAJOR-3 and unifies both game-over paths — a minimal `(deliveries, map_id, version)` context is REJECTED because it would force the controller to read `map_definition`, reintroducing the attribute access MAJOR-3 forbids; direct fail-safe map read with no `or classic`; stable `mini-metro-highscores-v1` contract; `mapDefinitionVersion` in the key; isolation/RL/fixtures/forward-v3/save-raises all clean). The one DESIGN change is Codex MAJOR-2, which simplifies the unit. All folded:

- **DESIGN PIVOT — START-EMPTY on a v1 board, NO migration (Codex MAJOR-2; resolves Codex MAJOR-1).** Supersedes plan §4's migration. A v1 board is NOT provably all-Classic: GM-09f made non-classic saves loadable, and the classic-hardcoded recorder (`main.py:132`) labels a non-classic Continue run `"classic"` (VERIFIED reachable: `load_autosave→load_game→resolve_map→Mediator(map_definition=non-classic)`, `build_from` plays it, `record_score(map=HIGHSCORES_MAP_CLASSIC)`). Migrating such a row to authoritative `classic@1` would preserve contamination and assert precision the data lacks (UNLIKE the *save* v1→v2, where GM-09a's guard PROVED v1 saves were genuinely classic). So `load_highscores` treats a v1 board like any other unreadable format → **START-EMPTY** (no `_migrate_v1_document`, no v1 validator). This also kills Codex MAJOR-1 (no migrate-before-validate normalization of `schemaVersion: true`/`1.0`/forbidden-extra-key). Rationale: the board is cosmetic + START-EMPTY-tolerant by design; a one-time legacy reset is honest and consistent. Documented in D-039 as the accepted trade-off (normal users lose the legacy classic board on upgrade — acceptable for a cosmetic surface). `load_highscores`: decode → validate as v2 → return; ANY failure (v1, forward v3, malformed, corrupt) → `_empty_document()` (v2). Add a "v1 board → START-EMPTY" test.
- **MAJOR (both) — ONE identity helper for sort + cap + RANK (Codex M3 / harness MINOR).** `record_score`'s rank loop (highscores.py:144-149) matches `(map, rulesVersion)` only; with the new key a board `classic@1 [100]` + first `classic@2=1` miscounts rank 2/not-best instead of rank 1/best (the cap-only test stays green, hiding it). **Fold**: factor `_identity(entry) -> (map, mapDefinitionVersion, rulesVersion)` and use it in `_sort_key`, the cap loop, AND the rank loop; test first-entry rank 1/is_best True + ties across two `mapDefinitionVersion`s with an existing other-version group present.
- **MAJOR (both) — `test_gm07d_run_game_loop.py` is NOT unchanged (Codex M4 / harness #1).** VERIFIED: `TestGM07dRecordHighscoreIsReadOnly` (:214) drives the REAL `record_highscore(SimpleNamespace(deliveries=7))` — no `map_definition` → read AttributeErrors → swallow → `target.exists()` (:220) + `entries[0]` (:222) fail; the RecursionError test (:190) drives real `record_highscore` on `_LoopMediator` (:38, no `map_definition`). **Fold**: give the `deliveries=7` stub AND `_LoopMediator` a `map_definition = SimpleNamespace(map_id="classic", map_definition_version=1)`; assert the recorded `map`/`mapDefinitionVersion` fields; add a separate missing-`map_definition` fail-safe case (record → None, no write).
- **MAJOR (both) — `test_gm07e_game_over_reconcile.py` is OMITTED (Codex M5 / harness #2).** VERIFIED: its OWN local `_SpyHighscores.record(self, deliveries)` (:85-91) appends the raw arg; assertions `deliveries_seen == [42]/[7]/[5]` (:178/201/265) flip when the arg becomes the mediator; the run-loop assertions (:435-445) read `.deliveries`/`.is_game_over` off the recorded arg (the real `_LoopMediator` HAS both — check polarity). **Fold**: update the local spy to `record(self, mediator)` appending `mediator.deliveries`; re-verify the run-loop promotion-vs-QUIT assertions hold with the real mediator (its `_LoopMediator`/`_DeliveringMediator` never reach the real recorder — a MagicMock `driver.record` and the local spy stand in — so they need NO `map_definition`).
- **MINOR (Codex) — `record_score` input validation + `map` grammar.** `map_definition_version=True/0` currently mints an invalid `RecordResult` that only fails at save; `map=""`/`"river "` persists despite the save/RL mapId grammar. **Fold**: inside `record_score`, `_positive_int(map_definition_version)` + nonempty-ASCII-no-whitespace `map` (a true mirror of the save's `_validate_map_identity`, GM-09f); tighten `validate_highscores`'s entry `map` to the same grammar. Direct-misuse tests. No `maps` import (syntax-only; unknown-but-valid ids stay allowed).
- **MINOR (Codex) — ARCHITECTURE is MANDATORY, not conditional.** ARCHITECTURE.md:388/405 pin the scalar controller seam AND the schema-v1 three-field identity. Fix both boundary descriptions in this unit.
- **NIT (harness) — `HIGHSCORES_MAP_CLASSIC` + annotation + `_empty_doc`.** KEEP the constant in highscores.py (`test_versioned_constants` asserts it; only main.py drops its import/use). Fix `_sort_key`'s annotation → `tuple[str, int, str, int]`. Update `test_gm07d_highscores._empty_doc()` (:43, hardcodes `schemaVersion:1`) → 2, alongside `_entry`/`_valid_doc`/`_record`/`_group`; header-strictness forward-version 2→3; ADD a "v1 board → START-EMPTY" case (was `test_valid_file_returns_the_parsed_document`'s v1 doc → now uses a v2 doc).
- **NIT (harness) — note the deliberate save-asymmetry in D-039.** The save is version-aware-accept-both with construction-time `classic@1` synthesis + a `resolve_map` structural guard; the leaderboard is validate-v2-only + START-EMPTY-on-v1 with NO `resolve_map` guard — defensible because it stores identity only and reconstructs no terrain.

Net effect: the START-EMPTY pivot makes the unit SIMPLER (no migration/v1-validator) and SAFER (no contamination, no migrate-before-validate). Revised touched-test set: `test_gm07d_highscores.py`, `test_gm07d_recorder_controller.py`, `test_gm07d_run_game_loop.py`, `test_gm07e_game_over_reconcile.py`, + new `test_gm09f2_highscore_map.py`.

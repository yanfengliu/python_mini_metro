# GM-09f2 plan — dual adversarial review synthesis

Both lanes returned **REVISE** and both VALIDATED the core design; the fixes are bounded (no design rework beyond one simplifying pivot). Folded into PLAN v2.

- Harness (`raw/plan-harness.md`, REVISE): 1 MAJOR (incomplete test enumeration ⇒ red suite — `test_gm07d_run_game_loop` + `test_gm07e` broken by the seam change, `_empty_doc`) + 2 MINOR (strict v1-detection, rank-loop predicate) + NITs. Verified the seam change preserves MAJOR-3 MORE cleanly and is in fact REQUIRED (a minimal context would force the controller to read `map_definition`).
- Codex ultra (`raw/plan-codex.md`, REVISE): 5 MAJOR + 2 MINOR. Corroborated the two broken test files + the rank predicate + the v1-detection strictness, and ADDED the decisive **MAJOR-2** (a v1 board is not provably all-Classic → migrating preserves contamination) plus the `record_score` input-validation/`map`-grammar MINOR and the mandatory ARCHITECTURE update.

## Load-bearing decisions — both lanes UPHELD
- Whole-mediator seam: preserves MAJOR-3 (the `None`-guard still precedes the call, so a seam-less controller reads nothing), unifies both game-over surfaces on the identical `record_highscore(controller.mediator)`, and is REQUIRED (a `(deliveries, map_id, version)` tuple would re-introduce the controller's `map_definition` read).
- Direct `mediator.map_definition` read with raise→swallow→None: correct fail-SAFE for a cosmetic board; an `or classic` default would MISATTRIBUTE the already-reachable non-Classic Continue run (and repeats the GM-09f `or DEFAULT` fail-open).
- `mini-metro-highscores-v1` stateContract stays stable across the additive `schemaVersion` bump (mirrors the save keeping `mini-metro-save-v1`).
- `mapDefinitionVersion` belongs in the key: a definition revision changes palette/spawn/rivers/tunnel-budget, so scores are materially incomparable; with every predicate on the full triple, `classic@2` cannot cap or evict `classic@1`.

## Findings + dispositions (all folded into PLAN v2)
- **Codex MAJOR-2 → START-EMPTY on v1, NO migration (VERIFIED reachable).** The decisive pivot: since v1 `map="classic"` labels are unprovable (the recorder was classic-hardcoded while GM-09f made non-classic saves loadable via Continue), a v1 board starts empty like any other unreadable format. This also RESOLVES Codex MAJOR-1 (migrate-before-validate normalization of `schemaVersion: true`/`1.0`/forbidden-extra-key) by eliminating the migration + v1 validator. Simpler AND safer. FOLD; documented as the accepted cosmetic-board trade-off in D-039.
- **Codex M3 / harness MINOR — ONE `_identity` helper for sort + cap + rank.** The rank loop miscounts across `mapDefinitionVersion`s if left map+rules-only; the cap-only test hides it. FOLD + first-entry-rank-across-versions test.
- **Codex M4 / harness #1 — `test_gm07d_run_game_loop` stubs need `map_definition`.** FOLD (CLASSIC-identity stubs + assert new fields + a missing-map fail-safe case).
- **Codex M5 / harness #2 — `test_gm07e` local spy + omitted from the touched set.** FOLD (spy records `mediator.deliveries`; re-verify run-loop promotion-vs-QUIT assertions).
- **Codex MINOR-1 — `record_score` input validation + `map` grammar (mirror the save's `_validate_map_identity`).** FOLD (`_positive_int` version + nonempty-ASCII-no-whitespace map, in both `record_score` and `validate_highscores`; direct-misuse tests).
- **Codex MINOR-2 — ARCHITECTURE update mandatory.** FOLD (both boundary descriptions).
- **harness NITs — keep `HIGHSCORES_MAP_CLASSIC`, `_sort_key` annotation, `_empty_doc`→v2, save-asymmetry note.** FOLD.

## Result
Both REVISE → all folded into PLAN v2; the START-EMPTY pivot (Codex MAJOR-2) simplifies the unit and resolves Codex MAJOR-1; the design is dual-confirmed. Ready for red tests.

---

# GM-09f2 implementation — dual adversarial review synthesis

Both lanes independently confirmed the PRODUCTION code is behaviorally correct (all 8 attack vectors verified live: seam/MAJOR-3, fail-safe map read, `_identity` rank/cap/sort, validation+grammar parity, START-EMPTY/no-migration, schema-v2 exactness, blast radius, test surgery). The split verdict was purely about TEST STRENGTH.

- Harness (`raw/impl-harness.md`, **SHIP**): no BLOCKER/MAJOR/MINOR; 45 hand-forged probes + 53 focused + 1459 full all pass; the one NIT (unused `HIGHSCORES_MAP_CLASSIC`) is the intentional PLAN-v2 retention. Reproduced the rank-across-versions, the fail-safe (missing map → None + no write), the `_map_id`↔`save._validate_map_identity` parity over a 26-seed corpus, and `schemaVersion=True`/`1.0` → START-EMPTY (no migrate-before-validate).
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST**): also verified the production code correct on every vector, but flagged 3 MUTATION-RESISTANCE gaps — regressions that would survive the suite — plus a doc NIT. All folded (test/doc only; no production change):
  - **MAJOR (Codex) — controller spies pinned `deliveries`, not mediator IDENTITY.** A regression forwarding `SimpleNamespace(deliveries=mediator.deliveries)` (dropping the map) would still match `deliveries_seen`, so the real recorder would get no `map_definition`. **FOLD**: the spy retains the raw arg (`mediators_seen`) and the promotion test asserts `spy.mediators_seen[0] is controller.mediator`.
  - **MAJOR (Codex) — `test_gm09f2` used only `@1` fixtures.** A regression forwarding a literal version `1` would pass (CLASSIC and RIVER are both `@1`). **FOLD**: `test_a_non_one_map_version_is_read_not_hardcoded` drives the real recorder with a synthetic `map_definition_version=7` and asserts the returned AND persisted entry preserve 7.
  - **MINOR (Codex) — loader START-EMPTY test lacked malformed-supported-v2 cases.** A loader trusting any v2 mapping would pass. **FOLD**: added `malformed v2 (extra entry key)` and `malformed v2 (bad mapDefinitionVersion=True)` → START-EMPTY cases.
  - **NIT (Codex) — `highscores.py` module docstring still said the two-field `(map, rulesVersion)` key.** **FOLD** (updated to the full triple + the v1-not-migrated note). README:66 (user-facing feature bullet) left abstracted — `mapDefinitionVersion` is an internal detail (all current maps are @1) and the detailed README:225 + the docstring carry the precise triple.

## Result
Harness SHIP + Codex FIX-FIRST → production code confirmed correct by BOTH; the 3 Codex mutation-resistance gaps + the docstring NIT are folded (test/doc only), so a future seam/version/loader regression now fails the suite. Post-fold: focused 54/54, full suite **1460/0** (12 skips), ruff + format + pre-commit clean. Ready to deliver [GM-09f2:A].

# GM-09f plan — dual adversarial review synthesis

Both lanes returned **REVISE** and both CONFIRMED the load-bearing decisions: the SPLIT is sound (save-schema / high-score / menu, in that order) and the save-schema unit is verifiable end-to-end via the programmatic `Mediator(map_definition=...)` path with NO menu/env change; v1-load stays byte-identical (`Mediator(map_definition=CLASSIC)` ≡ `Mediator()` — same singleton, deserialize overwrites RNG + discards the construction pool); the blast radius is contained (RL manifest / recursive-checkpoint / high-scores are separate schemas; `SAVE_SCHEMA_VERSION` has one non-test consumer).

- Harness (`raw/plan-harness.md`, REVISE): 2 BLOCKER (structural serialize guard; incomplete test blast radius) + 4 MAJOR (validate ordering, mapId/version validators, omitted docs, cross-process test repointing) + MINORs.
- Codex ultra (`raw/plan-codex.md`, REVISE): 6 MAJOR — corroborated the structural guard, ADDED the state-legality invariant (identity must denote a LEGAL state, not just a registered definition), gave the EXACT deterministic v1→v2 upgrade fixture (`save-v2-classic.json` = v1 + header only), and corrected the sub-unit order (high-score before menu).

## Findings + dispositions (all folded into PLAN v2)
- BLOCKER/MAJOR (both) — STRUCTURAL serialize guard `map_definition == resolve_map(id, version)`, not mere resolvability (else a forged classic reloads as terrain-free CLASSIC — the GM-09b fail-open). Keep the forged-classic rejection GREEN; flip only registered-non-classic using canonical maps. FOLD.
- MAJOR (Codex) — STATE-legality: `_require_legal_map_state` (stations in `spawn_regions`, `consumed_tunnels <= num_tunnels`) on serialize + post-load, since a valid identity + illegal state is still corrupt (verified: relabeling strands stations; over-budget is constructible). FOLD.
- MAJOR (both) — `validate_save` two-phase: read/validate/support-check `schemaVersion` BEFORE key selection, fail-closed named ValueError; full negative corpus. FOLD.
- MAJOR (harness) — mapId/mapDefinitionVersion scalar validators (mirror `rl.manifest_schema`). FOLD.
- MAJOR (Codex) — `save-v2-classic.json` = the exact canonical v1→v2 header transform; pin the real length/SHA; the upgrade AND idempotence are both pinned. FOLD.
- BLOCKER/MINOR (both) — complete touched-tests table (gm09b/d/e rejection flips keeping forged-classic; gm07b schema constants/keys/corpus; gm07b determinism repoint). FOLD.
- MAJOR (harness) — docs deltas (README/PROGRESS/ARCHITECTURE/GAME_RULES + D-038). FOLD.
- MAJOR (Codex) — sub-unit order: save-schema → high-score → menu. FOLD (updated split).
- MINOR (harness) — stateContract/rulesVersion stay stable across v1/v2. FOLD.
- MINOR (Codex) — `.gitattributes text eol=lf` for the fixtures: **RE-DISPOSITIONED, not folded** — the repo memory lesson `gitattributes-scripts-fixtures-eol-trap` (evidence-anchored) says pinning `scripts/fixtures/*.json eol=lf` breaks the recursive source-provenance guard, and `save-v1.json`'s byte tests already pass on Ubuntu+Windows CI without it. Commit `save-v2-classic.json` LF (verify `git ls-files --eol` = `i/lf`); no `.gitattributes` change.
- MINOR (harness) — `main.load_autosave` unwrapped → unloadable-map autosave raises into Continue; flagged for the menu sub-unit.
- NITs — inexact D-026 citation (fixed), map-blind `canonical_checkpoint` (out-of-scope flag).

## Result
Both REVISE → all folded into PLAN v2; direction + split dual-confirmed; the two highest-risk decisions (structural guard, deterministic upgrade fixture) are dual-verified. Ready for red tests.

---

# GM-09f implementation — dual adversarial review synthesis

Reviewed the finished implementation (`diff.md`) against the LIVE code. Both lanes ran the targeted trio + full suite + ruff and hand-forged probes.

- Harness (`raw/impl-harness.md`, **SHIP**): BLOCKER none, MAJOR none; 1 MINOR (ASCII/whitespace `mapId` gap vs D-038 contract) + 2 NITs (no product test drives the over-budget LOAD branch; pre-existing throwaway-Mediator sampling in `deserialize_game`). Verified the state-legality check reuses the EXACT inclusive spawn predicate (`_point_in_rects`) over the full pool, so it cannot false-reject a legit river/delta/lake game while still catching a relabel-into-water forge on load.
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST**): BLOCKER none; 1 MAJOR (`getattr(...) or CLASSIC` fail-open on a FALSEY `MapDefinition`) + 2 MINOR (same ASCII/whitespace gap; stale v1 docs). Verified both fixtures pinned, inclusive boundaries pass, exact-budget round-trips, forged over-budget load rejected, blast radius contained.

## Findings + dispositions (all folded)
- MAJOR (Codex) — `_require_serializable_map` defaulted via `getattr(mediator, "map_definition", None) or CLASSIC`, which coerces a FALSEY `MapDefinition` (a subclass with `__bool__ -> False`) into `classic@1` and silently loses its terrain — the exact fail-open the guard exists to close. Not reachable today (the frozen `MapDefinition` dataclass is always truthy — `bool(RIVER) is True`, no `__bool__`), but latent. **FOLD**: default ONLY on `map_def is None`; a falsey non-registry map is now KEPT and rejected by the structural equality guard. Regression `test_serialize_rejects_a_falsey_map_definition` (fails on the old `or`, passes on `is None`).
- MINOR (BOTH — convergent) — `_validate_map_identity` enforced only non-empty `str`, not the ASCII + no-whitespace contract its own comment + D-038 claim (the real `rl.manifest_schema` mirror does `.isascii()` + `any(c.isspace())`). Fail-closed already (`resolve_map` rejects on load), but a code-vs-stated-contract gap. **FOLD**: true mirror — non-empty ASCII, no whitespace. Regressions in `test_gm09f_save_map.TestGM09fMapIdentityShape` (non-ascii/whitespace/empty/non-string) + the gm07b strictness corpus (`non-ascii mapId`, `whitespace mapId`, `list schemaVersion`).
- MINOR (Codex) — stale docs: README `serialize_game` comment + `SAVE_SCHEMA_VERSION == 1` (now 2); ARCHITECTURE fixtures tree omitted `save-v2-classic.json`; D-038's Reason ended with two sentences leaked from the D-037 template (a LAKE "four-strip frame" line + a "save-schema… still defer to GM-09f" line that contradicts the save-schema landing in D-038 itself). **FOLD**: README `== 2` + `schema-v2 dict`; ARCHITECTURE tree adds the v2 fixture; D-038 Reason ends cleanly at "…the still-classic-hardcoded high-score recorder."
- NIT (harness, echoed by Codex) — the load-side `consumed_tunnels > num_tunnels` branch had no driving test (the creation gate means normal play never reaches it; it is defense-in-depth for a corrupt doc). **FOLD**: `test_legality_gate_refuses_an_over_budget_reconstruction` drives it directly (as the reviewers did to verify). Also extended the structural-guard corpus to forged DELTA + LAKE (Codex asked to codify beyond river).
- NIT (harness) — `deserialize_game` builds a throwaway `Mediator` that runs region rejection-sampling before `_restore_stations` overwrites the pool. Wasteful but correct and PRE-EXISTING (the classic path does the same). **NOT folded** — out of scope for this unit; noted for a future perf pass.

## Result
Harness SHIP + Codex FIX-FIRST → the one MAJOR (latent fail-open) and the convergent ASCII MINOR are folded with regressions; stale docs corrected; the over-budget load branch is now covered. Post-fold: focused 42/42, full suite **1450 pass / 12 skipped**, ruff + format + pre-commit clean. The migration is fail-closed on both axes, byte-frozen (v1 unchanged; v2 the pinned deterministic upgrade), and blast-contained. Ready to deliver [GM-09f:A].

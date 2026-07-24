# Adversarial IMPL review — harness general-purpose lane (agentId a4a5cf7a087685fe4)

**Scope reviewed (live code):** `src/save_schema.py`, `src/save_game.py`, `src/save_load.py`, `src/maps.py`, `src/entity/get_entity.py`, `src/mediator.py`, `src/save_schema_records.py`, `src/recursive_checkpoint_schema.py`, both fixtures, and all seven touched/new test files. Ran the targeted trio, the full `py313` suite, ruff, and eight hand-forged probes (schemaVersion corpus, map-identity validators, over-budget branch, forged ids, disk round-trips).

**Verification results:** Targeted tests 34/34 pass; full suite **1442 pass, 12 skipped, exit 0**; ruff check + format clean on all changed files.

## Findings by the adversarial checklist

**1. Fail-closed structural guard — SOLID.** `_require_serializable_map` (save_game.py:30) rejects a drifted map via frozen-dataclass `map_def != resolve_map(id, version)`, and `resolve_map` raises *first* on an unregistered id (probed: `atlantis` -> `unknown map id 'atlantis'`). `test_gm09b_river::test_forged_classic_with_terrain_is_rejected` is intact and green; forged-river-without-terrain also rejected. No forged/drifted map slips through.

**2. State-legality — SOLID, no false-rejection risk.** `_require_legal_map_state` (save_load.py:305) uses the **identical inclusive predicate** (`left<=x<=right and top<=y<=bottom`) as the spawn sampler `_point_in_rects` (get_entity.py:24), over the same `spawn_regions`, iterating the full `all_stations` **pool** — so a legit station at an eroded bank edge always passes (the sampler could only have placed it where the check accepts it). Boundary is inclusive; a legit river/delta/lake game cannot be wrongly rejected (confirmed by 4-map disk round-trips). Budget check is `>` (consumed==budget is legal; consumed>budget raises — verified by direct invocation), runs on serialize AND post-load, tunnel counts stay derived.

**3. Two-phase validate_save — SOLID.** `_read_schema_version` runs before key selection. Probed the full negative corpus: `True/False/2.0/"2"/None/[]/{}` -> "must be an integer"; `0/3` -> "unsupported"; missing -> "is required"; v1-with-map-keys and v2-without-map-keys -> clean exact-key errors. All `ValueError`, never `KeyError`/`TypeError`. `_int`/`_string` use `type(...) is` so bool is correctly rejected, and `safe_checkpoint_value` preserves bool.

**4. Backward compat + byte-freeze — SOLID.** `save-v1.json` pins **unchanged** (15442 / `d34736a6...`), still loads as `classic@1`. The v1->v2 delta is exactly the header (`schemaVersion 1->2`, `mapId`/`mapDefinitionVersion` added, **+43 bytes**), pinned to `save-v2-classic.json` (15485 / `60f2bc16...`). Idempotent + cross-process deterministic. Confirmed `Mediator(map_definition=CLASSIC)` == `Mediator()`.

**5. Fail-closed load — SOLID.** Unknown id / unsupported version raise named errors via `resolve_map`; never a silent Classic fallback.

**6. Blast radius — CONTAINED.** `SAVE_SCHEMA_VERSION` has exactly one non-test consumer (save_game.py:230). Checkpoint, scenario, highscores, and settings all carry independent version fields. `main.py` delegates version-agnostically (load_autosave -> load_game). No unguarded `==1` assumption.

**7. Test surgery — CORRECT.** The three "not serializable" tests flipped to serialize+round-trip while keeping forged-classic rejection; GM-09a flip forges a registry-mismatched `river@1`; schema-test constants/corpus updated; walk-based missing-key test auto-covers the new keys. No test is tautological.

## Severity summary

- **BLOCKER: none.**
- **MAJOR: none.**
- **MINOR (1):** `_validate_map_identity` (save_schema.py:112) enforces only *non-empty str* via `_string`, but its own comment says "mirroring `rl.manifest_schema._validate_map_identity`" and **D-038 says "non-empty ASCII `mapId`"**. The actual RL mirror (`rl/manifest_schema.py:247`, `rl/protocol.py:181`) enforces `.isascii()` + no-whitespace; this one does not. **Zero functional/security impact** — a whitespace/non-ASCII `mapId` (e.g. `"river "`, `"rivér"`) passes `validate_save` but is rejected at `resolve_map` on load with a named `ValueError` (still fail-closed; no serialize path emits non-ASCII since ids come from the registry). It is a code-vs-stated-contract gap in a high-risk persistence decision record. Fix: add `map_id.isascii()` + no-whitespace to `_validate_map_identity` (true mirror), or soften the comment/D-038 wording. The plan's load-bearing goal for this item ("`mapId:123` fails `validate_save`") *is* met.
- **NIT (2):** (a) The load-side `consumed_tunnels > num_tunnels` branch of `_require_legal_map_state` has no product test driving it True (only the within-budget round-trip and the creation-gate path in test_gm09c are covered); verified the branch is correct by direct invocation, and it's hard to reach via a forged doc under the fixed config, but a forged single zigzag path can reach it — a targeted forged-over-budget load test would close the gap the plan's item 2 implied. (b) `deserialize_game` builds a throwaway `Mediator(seed=0, map_definition=…)` that runs region rejection-sampling for river/delta/lake before `_restore_stations` overwrites the pool — wasteful but correct and pre-existing.

## Verdict: **SHIP**

The migration is fail-closed on both axes the dual plan review demanded (structural registry-equality + state-legality on serialize *and* load), byte-frozen pins are intact with a deterministic pinned v1->v2 upgrade, the blast radius is contained to one consumer, and the test surgery faithfully preserves the forged-classic guard while flipping registered maps to round-trips. The single MINOR is a documentation-accuracy gap with no functional consequence.

**Most important thing verified:** the state-legality check reuses the *exact* inclusive spawn predicate over the full station pool, so it cannot false-reject a legitimate river/delta/lake game (4-map disk round-trips preserved map + tunnel budget) while still catching a relabel-into-water forge on load — the guard is tight in both directions.

# Harness plan review (GM-09f save-schema v2) — REVISE

Direction right (v2 additive map keys, keep v1 fixture as backward-compat anchor, synthesize classic on load, version-aware key sets) but under-enumerates test blast radius + leaves the key guard ambiguous. 2 BLOCKER + 4 MAJOR.

## BLOCKER 1 — "resolvable" is not fail-closed; it fails OPEN on a forged/drifted classic
v2 persists only (mapId, version), reconstitutes terrain from the registry on load. A `MapDefinition(map_id="classic", version=1, rivers=..., spawn_regions=...)` (forged classic, `test_gm09b_river.py:160`) has a registered identity; a resolvability-only guard passes → serializes as classic/1 → load `resolve_map("classic",1)` returns terrain-free CLASSIC → river band + spawn regions SILENTLY DROPPED. Exactly the GM-09b fail-open. Fix: STRUCTURAL `mediator.map_definition == resolve_map(id, version)`; `test_forged_classic_with_terrain_is_rejected` must stay GREEN; only registered-non-classic flips.

## BLOCKER 2 — incomplete test blast radius (6+ hard-fails across 4 unlisted files)
1. test_gm07b_save_schema.py:156-157 SAVE_SCHEMA_VERSION==1, SUPPORTED=={1}. 2. :164 schemaVersion==1 on serialize. 3. :202 exact TOP_LEVEL_KEYS. 4. :175 forward-2 rejection (now supported). 5. test_gm07b_save_determinism.py:271 _WORKER resave==v1 bytes. 6. test_gm09b_river:175 / test_gm09d_delta:217 / test_gm09e_lake:238 "not serializable". Split "flip" (registered non-classic now serializes) vs "preserve" (forged still rejected).

## MAJOR 3 — validate_save ordering: read+support-check version BEFORE key selection; missing/malformed schemaVersion → named ValueError not KeyError. Negative corpus stays clean.
## MAJOR 4 — no scalar validators for mapId/mapDefinitionVersion; mirror rl/manifest_schema._validate_map_identity (non-empty ASCII id, positive non-bool int) so "validates but won't load" can't happen.
## MAJOR 5 — docs deltas omitted (README:222-230, PROGRESS, ARCHITECTURE); docs are part of the change.
## MAJOR 6 — cross-process determinism test (test_distinct_hash_seed_processes_agree_byte_for_byte:271) left un-repointed; the v1→v2 upgrade bytes unpinned. Repoint the byte anchor to save-v2-classic.json (v2→v2), keep a v1→v2 upgrade check (cross-process agreement + valid v2 mapId=classic, no absolute v1 byte pin), confirm the replay half still pins time_ms.

## MINOR 7 — stateContract/rulesVersion stay stable across v1/v2 (test expects "mini-metro-save-v2" REJECTED). State it.
## MINOR 8 — add a RIVER-save tunnel-state round-trip test (derived, not persisted — verified via mediator.py:250-284).
## MINOR 9 — main.load_autosave (main.py:162-163) doesn't wrap load_game → a v2 autosave with a removed map raises into Continue; flag for the menu unit. Add mapId/version to the field-drop corpus.
## NIT 10 — D-026 citation inexact (README:230 is config-divergence). NIT 11 — canonical_checkpoint is map-blind (out of scope flag).

## Verified sound
Q1 split (save-schema verifiable via programmatic path, env.py has no map param, _WORKER overrides env.mediator). Q4 v1-load byte-identity (Mediator(map_definition=CLASSIC) ≡ Mediator(); deserialize overwrites RNG + discards construction pool). Q6 blast radius contained (RL manifest separate + already map-versioned v3; recursive checkpoint separate CHECKPOINT_SCHEMA_VERSION; high-scores separate; SAVE_SCHEMA_VERSION one non-test consumer).

## VERDICT: REVISE
Riskiest requirement: STRUCTURAL equality to the resolved registry definition, not mere resolvability — and test_forged_classic_with_terrain_is_rejected must survive the flip.

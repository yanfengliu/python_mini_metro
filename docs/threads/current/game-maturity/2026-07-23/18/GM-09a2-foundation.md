# GM-09a2 verified foundation (descriptor-version switch)

The load-bearing legacy-byte-compat mechanism is IMPLEMENTED AND VERIFIED (uncommitted WIP, to resume). Both review lanes' predicted hashes are reproduced exactly:
- map-ABSENT reference `TaskSpec(fast,6,deliveries,4)` → `c2ef342f9cedfc3b…` (the exact pre-map legacy fingerprint — PRESERVED).
- map-BOUND `TaskSpec(..., map_id="classic", map_definition_version=1)` → `efec72daa45f3421…` (the exact hash Codex predicted).

## The verified change (src/rl/protocol.py)
- `TaskSpec` gains `map_id: str | None = None` and `map_definition_version: int | None = None`, APPENDED after `max_episode_steps` (so every positional call site is unchanged). `__post_init__` validates via `_validate_map_identity`: exactly `(None, None)` [legacy] or `(non-empty ASCII id, positive non-bool version)` [map-bound]; a partial pair / empty / non-ASCII / non-positive / bool version raises a specific message (Codex-5).
- `task_descriptor` builds the current 9-key dict, then adds `mapId`/`mapDefinitionVersion`/`descriptorVersion:2` ONLY when `map_id is not None`. Because `canonical_json` sorts keys per-descriptor independently, a map-absent spec is byte-identical to the pre-map code → legacy hash preserved; presence of the keys IS the version signal (no key added to the legacy descriptor). Verified: `test/test_gm09a2_task_identity.py` (10 tests) green, incl. the pinned `c2ef342f` legacy lock and map-id/version sensitivity.

## Remaining GM-09a2 layers (per PLAN.md v2 "GM-09a2" bullet)
1. COMMIT the git-ignored real legacy manifest bytes to `scripts/fixtures/` (Codex-2: `output/rl/recurrent-final-smoke-20260711/training-manifest.json`, schema v1, `taskFingerprint c2ef342f…`, 24 keys) — the CI-runnable legacy regression.
2. Manifest v3 (`src/rl/manifest_schema.py`): explicit `V1`/`V2`/`V3` constants; `_V3_KEYS = _V2_KEYS | {mapId, mapDefinitionVersion}`; widen the history emit/parse conditionals to `{v2, v3}` (harness MAJOR-2); add a v3 `to_dict` map block + `from_dict` v3 branch + `expected_keys=_V3_KEYS`; add v3 to `SUPPORTED_TRAINING_MANIFEST_SCHEMAS`; `__post_init__` requires v1/v2 mapless + v3 map-bound; the factory derives schema/task/map/fingerprint from ONE `TaskSpec`.
3. `create_training_manifest` (`manifest.py`): optional `map_id`/`map_definition_version`, select v3 only when map-bound (else keep writing v2, map-free).
4. `task_spec_from_manifest` (`training.py`): read map fields when present (v3) → map-bound spec; absent (v1/v2) → map-LESS spec (`map_id=None`) → legacy hash. Drive the committed fixture through it and assert `c2ef342f…` reconstructs.
5. `PlayerEnvThunk`/`make_env_thunks` (`training.py`): carry `map_id`/`map_definition_version` to subprocess workers; validate the `(id, version)` pair (Codex-4).
6. CLI (`scripts/train_rl.py`, `evaluate_rl.py`): `--map` defaulting to `classic` for FRESH training; on RESUME/EVALUATE INHERIT map identity from the manifest, not the `--map` default (harness/Codex MAJOR-1 — else a legacy resume fails the fingerprint check), mirroring `_resolve_algorithm_and_history`.
7. `player_env.py`: keep `PlayerPixelEnv()` map-absent by default so `test_player_env.py:284` (`PlayerPixelEnv().task_spec == TaskSpec()`) holds.

Deferred to GM-09f: high-score `mapDefinitionVersion` + the save-schema map field. The core risks (legacy hash preserved for the descriptor AND for v1/v2 manifest reconstruction) are EMPIRICALLY provable exactly as GM-09a's determinism was, so the harness lane + a pinned-fixture proof adequately review the legacy-compat even if the external Codex lane declines again; the NEW behavior (map-bound manifest/CLI) is additive and directly testable.

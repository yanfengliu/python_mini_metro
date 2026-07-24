# GM-09a2 versioned task-descriptor identity diff ledger

Status: implemented and locally green; ready for the CI-gated `[GM-09a2:A]` commit after review + rebase onto `origin/main`.

## Production surface
- `src/rl/protocol.py`: `TaskSpec` map_id/map_definition_version (appended, default None) + `_validate_map_identity`; `task_descriptor` map-bound branch (byte-identical legacy path).
- `src/rl/manifest_schema.py`: `TRAINING_MANIFEST_SCHEMA_V3`, `_V3_KEYS`, `TrainingManifest` map fields + `_validate_map_identity`, `to_dict` (history v2+v3, map v3), `from_dict` (v3 keys + map read).
- `src/rl/manifest.py`: `create_training_manifest` map params + v3 selection.
- `src/rl/training.py`: `task_spec_from_manifest` map read; `PlayerEnvThunk`/`make_env_thunks` map threading.
- `src/rl/player_env.py`: `PlayerPixelEnv` map params + `resolve_map` + `Mediator(map_definition=)`.
- `src/maps.py`: `map_by_id`, `KNOWN_MAP_IDS`.
- `scripts/train_rl.py`: `--map` arg; `_resolve_map_identity` (resume-inherit); resume-manifest parsed before spec; `persist_manifest` map fields.

## Evidence surface
- `scripts/fixtures/legacy-training-manifest-v1.json` (new): committed sanitized real pre-map manifest (reconstructs to `c2ef342f…`).
- `test/test_gm09a2_task_identity.py`, `test/test_gm09a2_manifest.py` (new): legacy byte-lock, real-fixture reconstruction, map-bound descriptor, invariants, v3 round-trip, CLI resume-inherit.
- `test/test_gm06b_fleet_player_pixels.py`: `EXPECTED_LF_TRAINING` re-pinned (`4f4b8f32…`) — training sources legitimately changed.
- Docs: README (`--map`), ARCHITECTURE (manifest v3 + task-descriptor identity), PROGRESS, DECISIONS D-033.

Local gates: full py313 suite 1357/0 (12 skips); ruff/format/per-file pre-commit clean; `train_rl.py` 498, `protocol.py` 406, `manifest_schema.py` 365 (all < 500).

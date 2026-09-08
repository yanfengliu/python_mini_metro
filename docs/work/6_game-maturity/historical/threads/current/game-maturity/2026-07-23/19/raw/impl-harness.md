# GM-09a2 implementation review — harness lane (verbatim), verdict CLEAN

Read every changed file; independently verified all hashes by running py313 Python.

## 1. LEGACY BYTE-COMPAT — VERIFIED SOUND
- `TaskSpec(render_profile="fast",fixed_ticks=6,reward_mode="deliveries",max_episode_steps=4).fingerprint()` == `c2ef342f9cedfc3b7292ec2517ec7ccca7b2dcf9b49811c6dec529c25e73933e` (exact), `map_id is None`, descriptor has exactly the 9 legacy keys, no `mapId`.
- The committed fixture (schema v1) round-trips through `from_dict` + `task_spec_from_manifest` back to `c2ef342f…` with `map_id is None`.
- `TaskSpec()`, the 4-positional form, and `PlayerPixelEnv().task_spec` are all map-absent and equal the legacy default fingerprint.
- Map keys added only under `if selected.map_id is not None` (protocol.py:377-380); `map_id` defaults None on every surface. protocol_fingerprint untouched (69c604ac…). Shared map-less pins in test_gm05b/05c/06b unchanged. Cannot refute; holds.

## 2. MANIFEST v3 INVARIANTS — VERIFIED SOUND
v1/v2 exact-key + map-free; `_V3_KEYS = _V2_KEYS | {mapId, mapDefinitionVersion}`. v2+mapId rejected; v3 without mapId rejected; direct v2 object + map identity rejected by `_validate_map_identity`. `to_dict` emits history for v2 AND v3 (the MAJOR-2 widening is byte-safe — for v2, `schema in (v2,v3)` == old `== v2`). v3 cannot drop history. schema/map lockstep held.

## 3. RESUME-INHERIT (MAJOR-1) — VERIFIED SOUND
Resume manifest parsed BEFORE the spec (train_rl.py:272-284); map inherited via `_resolve_map_identity` (`getattr(...,"map_id",None)`); a pre-map resume reconstructs a map-less spec whose fingerprint matches, so validation passes. Conflicting explicit `--map` rejected. No double-read; `--map` defaults None.

## 4. THUNK THREADING — VERIFIED SOUND
`PlayerEnvThunk` carries + passes the map fields; `make_env_thunks` threads them; `PlayerPixelEnv()` default keeps `task_spec == TaskSpec()` and `_map_definition is None`. Unknown map id fails closed (`unknown map id 'ghostmap'; known maps: ['classic']`).

## 5. FINGERPRINT PIN — VERIFIED LEGITIMATE
`maps.py` NOT in `TRAINING_SOURCE_PATHS` but captured by `compute_content_fingerprint` (src/** glob). `EXPECTED_LF_TRAINING` legitimately changed because TRAINING_SOURCE_PATHS files changed. protocol.py/player_env.py captured by content fingerprint. Correct separation.

## 6. REGRESSIONS — NONE
Full suite 1357 OK (12 skips); ruff clean; evaluate_rl reconstructs correctly.

## NITs (do not block)
- test_gm09a2_task_identity.py:76 `json.load(open(...))` leaks a handle (ResourceWarning). Fix: context manager.
- map_id validation accepts whitespace/control ASCII (" ","\t","a b","classic\n") — unreachable via CLI (choices), fails closed at resolve_map. Optional: reject whitespace to match `_require_nonempty().strip()`.

## Verdict: CLEAN — the two findings are NIT-level.

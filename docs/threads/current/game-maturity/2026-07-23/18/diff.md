# GM-09a Classic map abstraction — diff ledger

Status: implemented and locally green; behavior-preserving (byte-identical construction + trajectory). Ready for the CI-gated `[GM-09a:A]` commit. The map-ABSTRACTION half of the dual-reviewed re-scope; GM-09a2 (versioned task identity) follows.

## Implemented production surface

- `src/maps.py` (new, 81): data-only `MapDefinition` (frozen; `map_id`, `map_definition_version`, station-shape palette coerced to tuples in `__post_init__`), `CLASSIC` capturing today's config values, and version-aware `resolve_map(map_id, version)` with clear named errors. Imports only `config` + `geometry.type` — no `pygame`/`entity`/`mediator`, so import-safe and cycle-free.
- `src/entity/get_entity.py`: `get_random_stations` gained keyword-only palette params (`shape_types`/`unique_shape_types`/`unique_spawn_start_index`/`unique_spawn_chance`), each None-sentinel → the config global, so existing callers draw byte-identically.
- `src/mediator.py`: `__init__` gained optional `map_definition` (default `CLASSIC`); `get_initial_station_pool` threads the map palette one-way into `get_random_stations`.
- `src/save_game.py`: fail-closed `_require_classic_map` guard in `serialize_game` — only `classic@1` (or a `map_definition`-less Mediator) serializes; adds no save bytes.

## Behavior-preservation proof

- `test/test_gm09a_maps.py` (new): pinned pre-change fingerprints (construction = stations + path colors + both RNG states; trajectory = 300 steps) for seeds 0/1 reproduce exactly; a fingerprinted seed reaches the unique-shape path (durable coverage); default-vs-explicit palette equivalence; import-safety (subprocess, no pygame/mediator leak); immutability; version-aware lookup errors; save-guard rejection.
- Empirical: a 60-seed list-vs-tuple equivalence check (0 mismatches, RNG states included); in review, an independent pre-change-code reconstruction reproduced the pinned fingerprints (non-circular lock) plus a 20,000-seed `choice(list)` vs `choice(tuple)` stress (0 mismatches).

## Docs

- `DECISIONS.md` D-032; `ARCHITECTURE.md` (module tree + a `maps.py` boundary entry); `PROGRESS.md` (2026-07-23). No README/GAME_RULES change (behavior-preserving, no user-facing control).

Local gates: full py313 suite 1336/0 (12 skips); GM-09a module 12/0; Ruff check + format clean; pre-commit hooks pass; `maps.py` 81 lines, `mediator.py` 843 (< 1000). No schema/observation/checkpoint/frozen-artifact change; `save-v1.json` byte-frozen.

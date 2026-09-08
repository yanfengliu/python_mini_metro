# GM-09b river map + terrain/station regions diff ledger

Status: delivered as Commit A `44dfecc` (clean fast-forward onto `origin/main` at `6ed1d6c`), exact [run 30062439741](https://github.com/yanfengliu/python_mini_metro/actions/runs/30062439741) green (`build` `89386601248`, `rl-smoke` `89386601196`); evidence-only Commit B `[GM-09b:B]` active.

## Production surface
- `src/maps.py`: `MapDefinition` additive `spawn_regions`/`rivers` rect tuples (`__post_init__` tuple-coerce + positive-area validation); `RIVER` (central river, two station_size-eroded banks) registered; `KNOWN_MAP_IDS == ("classic","river")`.
- `src/entity/get_entity.py`: `_sample_position` bounded rejection-sample (falsy no-region fast path); `spawn_regions` threaded through `get_random_stations → get_random_station → get_station_spawn_position`; `get_random_position` UNTOUCHED.
- `src/mediator.py`: `get_initial_station_pool` threads `self.map_definition.spawn_regions`.
- `src/rendering/terrain_renderer.py` (new, 31): `draw_terrain` paints river bands (`pygame.draw.rect`), RNG-free.
- `src/rendering/game_renderer.py`: `draw_terrain` at the top of `draw` (before the network); +6 lines (484 < 500).
- `src/save_game.py`: `_require_classic_map` hardened to STRUCTURAL equality against `CLASSIC` (rejects forged classic-with-terrain).

## Evidence surface
- `test/test_gm09b_river.py` (new): RIVER definition + resolve; region spawn (all on banks, none in/touching the river, deterministic); CLASSIC byte-identity; structural guard (forged classic + river rejected); terrain render (CLASSIC no-op, RIVER paints); import-safety (no shapely/geometry.polygon).
- Docs: README (`--map river`), ARCHITECTURE (terrain layer + regions), GAME_RULES (river no-spawn/render rule), PROGRESS, DECISIONS D-034 + the hardened save-guard comment.

## Deferred to GM-09f (dual-plan-review-confirmed sound)
The save-schema/high-score map fields + in-game menu selection; the fail-closed guard holds until then. GM-09c adds crossing/tunnel mechanics.

Local gates: CLASSIC determinism locks (`test_gm09a_maps` fingerprints + `save-v1.json` frozen) unmoved; full py313 suite 1372/0 (12 skips); ruff/format/pre-commit clean; budgets held.

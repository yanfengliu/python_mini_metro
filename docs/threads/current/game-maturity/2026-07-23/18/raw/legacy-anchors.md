# GM-09a load-bearing legacy anchors (verified pre-plan-review)

Two invariants the implementation must preserve byte-for-byte. Verified against the live pre-change code:

## 1. RL legacy fingerprint (task-descriptor byte-compat)
The reference `TaskSpec(render_profile="fast", fixed_ticks=6, reward_mode="deliveries", max_episode_steps=4)` — matching the real fixture `output/rl/recurrent-final-smoke-20260711/training-manifest.json` — produces:
- descriptor keys (sorted, 9): `action_space, episode, fixed_ticks, observation_space, protocol_fingerprint, protocol_id, protocol_version, render_profile, reward_mode`
- `task_fingerprint` = `c2ef342f9cedfc3b7292ec2517ec7ccca7b2dcf9b49811c6dec529c25e73933e` (EXACT match to the fixture).

So the legacy-compat mechanism is feasible: a map-ABSENT spec must keep exactly these 9 keys (no map/version keys added) → identical canonical bytes → this exact hash. The map-BOUND branch adds `mapId`/`mapDefinitionVersion`/`descriptorVersion` only. The red test pins this hash for the map-absent path and reconstructs the real fixture through `task_spec_from_manifest`.

## 2. Classic station-spawn determinism
`Mediator(seed=N)` today (which the Classic map definition must reproduce byte-identically):
- seed=0: `[(Triangle,1232,318), (Rect,1132,474), (Rect,1213,375)]`
- seed=42: `[(Triangle,910,148), (Rect,1475,180), (Cross,1074,384)]`
- seed=123: `[(Cross,1041,305), (Cross,1337,156), (Triangle,1240,191)]`

The Classic map's generator must preserve the exact RNG draw order (the distinct-shape retry loop in `get_initial_station_pool` + `get_random_stations`/`get_station_spawn_position`) so these are unchanged. The red test pins these against `Mediator(seed=N)` under Classic.

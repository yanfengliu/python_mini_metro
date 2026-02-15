## 2026-02-08

- Added Gym-like programmatic play interface in `src/env.py` with structured and numpy observations.
- Added high-level programmatic actions in `src/mediator.py` (create/remove paths, pause/resume, step time).
- Expanded programmatic-play tests in `test/test_env.py` for loops, invalid actions, limits, reward delivery, and observations.
- Added agent playthrough framework in `src/agent_play.py` with action logging and replay helpers.
- Added unit tests for agent playthrough recording and determinism in `test/test_agent_play.py`.
- Added game-over rules for excessive long-waiting passengers, wired to env/manual play.
- Added passenger wait tracking plus tests for game-over behavior.
- Added game-over overlay rendering with final score display and main loop freeze on game-over.
- Added mediator test coverage for game-over overlay rendering.
- Added clickable restart/exit buttons on game-over screen with click handling and keyboard shortcuts.

Tests:
- `python -m unittest -v`

## 2026-02-14

- Added progressive metro line unlock milestones tied to cumulative travels handled: 1 line at start, then 2/3/4 at 100/250/500 travels.
- Switched line colors to runtime-randomized color allocation so each run can produce a different line color set.
- Updated mediator and environment tests to account for progressive line unlocking and added dedicated milestone progression coverage.
- Added game rules documentation in `GAME_RULES.md` describing unlock thresholds and randomized line color behavior.
- Added targeted tests to verify `total_travels_handled` increments correctly on passenger delivery in both mediator and environment flows.
- Expanded `GAME_RULES.md` into a full implementation-aligned rules reference covering objective, stations/passengers, lines/metros, progression, routing, spawning, game-over, controls, and programmatic actions.
- Updated locked path button visuals to draw as empty ring outlines (edge-only) instead of filled circles, and synchronized lock state updates with unlock progression.
- Added station progression tied to cumulative travels: start with 3 stations, then unlock additional stations at 30, 80, 150, 240, ... travels (increment +20 each unlock) up to 10 stations.
- Added mediator logic to spawn newly unlocked stations from a pre-generated station pool while preserving existing station/path state.
- Updated gameplay/environment tests for dynamic station counts and added mediator coverage for station unlock milestones.
- Updated `GAME_RULES.md` with station unlock progression details.
- Fixed path button color regression so unlocked line buttons keep the assigned metro line color instead of being reset to default gray on lock-state refresh.
- Added regression coverage in `test/test_coverage_utils.py` to verify assigned path button color persists when unlocked.
- Fixed path rendering order centering so active paths are offset around zero based on current path count, preventing single-path geometry from self-crossing due to forced negative offsets.
- Added mediator rendering regression tests to verify centered path offsets for one-path and three-path cases.
- Switched passenger spawning from one global cadence to per-station rhythms by tracking station-specific spawn intervals/timers and spawning passengers independently per station.
- Updated mediator/env tests for the new spawning model and added dedicated coverage asserting independent station spawn rhythms.
- Changed station unlock baseline to 10 travels as the intended behavior, and updated mediator unlock-threshold tests plus `GAME_RULES.md` milestones accordingly.
- Added keyboard speed controls (1x/2x/4x via keys `1`/`2`/`3`) and wired simulation timing, metro movement, spawn-step progression, and wait-time updates to respect the selected speed.
- Added gameplay and mediator test coverage for speed key handling and time-scaling behavior; updated docs controls in `README.md` and `GAME_RULES.md`.
- Fixed passenger route selection to prefer the shortest reachable destination route (with transfer-aware tie-breaking) so riders board eligible metros instead of waiting for longer alternatives.
- Added mediator regression coverage to verify a passenger chooses the shortest destination route and boards an available metro with matching path capacity.
- Updated boarding behavior so waiting passengers can board the first arriving metro with space when that metro can still lead to a valid destination route, even if their prior plan targeted another line.
- Added mediator regression coverage for first-arriving eligible metro boarding and travel-plan reassignment to the arriving line.

Tests:
- `python -m unittest -v`

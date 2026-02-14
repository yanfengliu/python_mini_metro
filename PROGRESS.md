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

Tests:
- `python -m unittest -v`

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

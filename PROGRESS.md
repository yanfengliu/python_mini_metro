## 2026-02-08

- Added Gym-like programmatic play interface in `src/env.py` with structured and numpy observations.
- Added high-level programmatic actions in `src/mediator.py` (create/remove paths, pause/resume, step time).
- Expanded programmatic-play tests in `test/test_env.py` for loops, invalid actions, limits, reward delivery, and observations.

Tests:
- `python -m unittest -v test.test_env`

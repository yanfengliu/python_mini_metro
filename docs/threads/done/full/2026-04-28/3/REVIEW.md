# Full Codebase Review - 2026-04-28 Iteration 3

## Scope

Iteration 3 reviewed the iteration-2 fixes for action validation, game-over behavior, looped-line routing and creation, passenger travel-plan invalidation, test isolation, review artifact placement, and the updated AGENTS.md review commands.

## Reviewers

- Claude Opus: unavailable due quota exhaustion. Raw quota output is saved in `raw/opus.md`.
- Codex reviewer 1: `raw/codex-1.md`.
- Codex reviewer 2: `raw/codex-2.md`.
- Codex reviewer 3: `raw/codex-3.md`.

Because Claude remained unavailable, three independent Codex reviewers were used as fallback reviewers.

## Summary

Reviewers found no important remaining issues in the runtime fixes. They confirmed that rejected actions no longer advance time, malformed action schemas are rejected more strictly, programmatic loop creation preserves the requested station sequence before closing the loop, looped routing includes the closing edge, and removed downstream lines no longer strand onboard passengers on surviving metros.

The remaining findings were low-severity cleanup issues in test isolation, docs wording, and review artifacts.

## Findings

### Low - Path-button draw test still patched pygame globally

Codex reviewers 1 and 3 found that `test/test_coverage_utils.py` still assigned `pygame.draw.circle = MagicMock()` directly in `test_path_button_draws_cross_when_visible`. This could leak global pygame draw state into later tests and made the iteration-2 synthesis slightly overstate the scoped-patch cleanup.

Disposition: Accepted and fixed by replacing the direct assignment with a scoped `patch("pygame.draw.circle")` context around the draw call. The same cleanup was applied to similar direct draw-method patches in the geometry, path, and station tests.

### Low - GAME_RULES overstated travel-plan invalidation

Codex reviewer 1 found that `GAME_RULES.md` said removing a line invalidates any travel plan that used it, while the implementation intentionally preserves an onboard passenger's immediate surviving-line transfer plan until the passenger leaves that line and replans against the updated network.

Disposition: Accepted and fixed by updating `GAME_RULES.md` to distinguish waiting-passenger invalidation from onboard transfer-plan preservation.

### Low - Transient reviewer PID file in review artifacts

Codex reviewer 2 found that `docs/threads/done/full/2026-04-28/2/reviewer-pids.tsv` was a local process-tracking artifact, not review evidence.

Disposition: Accepted and fixed by removing the transient PID file. The same transient file and optional stdout/stderr logs were also removed from iteration 3.

## Validation

- `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed: 174 tests.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff check src\env.py src\graph\graph_algo.py src\graph\node.py src\mediator.py test\test_coverage_utils.py test\test_env.py test\test_gameplay.py test\test_geometry.py test\test_graph.py test\test_mediator.py test\test_path.py test\test_station.py` passed.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff format --check src\env.py src\graph\graph_algo.py src\graph\node.py src\mediator.py test\test_coverage_utils.py test\test_env.py test\test_gameplay.py test\test_geometry.py test\test_graph.py test\test_mediator.py test\test_path.py test\test_station.py` passed.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files <changed-files>` passed after hooks normalized review artifact whitespace/newlines.
- `git diff --check` passed.

An initial full-suite rerun failed after the path-button mock leak was fixed because several later tests had been relying on leaked `pygame.draw` mocks. Those tests now patch their own draw methods with cleanup, and the targeted `test.test_path test.test_station` rerun passed before the final full-suite rerun.

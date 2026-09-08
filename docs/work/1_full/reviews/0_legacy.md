# Full-Codebase Review: Iteration 1

## Reviewer Coverage

- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit · resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
- Per the fallback rule, three independent Codex reviewers were run with `gpt-5.5` and `xhigh` reasoning. Raw outputs are preserved in `raw/codex-1.md`, `raw/codex-2.md`, and `raw/codex-3.md`.
- The Codex read-only sandbox blocked direct test execution inside the reviewer subprocesses, so reviewer validation was static. Local verification will run outside the reviewer sandbox before completion.

## Confirmed Findings

### High: programmatic steps mutate state after game over

- Reported by: Codex 1, Codex 2, Codex 3.
- Evidence: `MiniMetroEnv.step()` always calls `mediator.apply_action()` and `mediator.step_time()`; `Mediator.increment_time()` only checks pause state. `GAME_RULES.md` says simulation time and gameplay updates stop on game over.
- Disposition: accepted. Freeze programmatic time progression after `is_game_over`, and cover repeated `step()` calls after `done=True`.

### Medium: malformed public actions can raise or report false success

- Reported by: Codex 1, Codex 2, Codex 3.
- Evidence: `Mediator.apply_action()` assumes `action` is a dict; `create_path_from_station_indices()` assumes a list of ints; `remove_path_by_index()` compares unvalidated values; aborted programmatic path creation returns `self.paths[-1]`, which can be an existing path.
- Disposition: accepted. Validate action schemas before dispatch and return a newly completed path only when creation actually succeeds.

### Medium: looped-line routing omits the closing edge

- Reported by: Codex 1, Codex 3.
- Evidence: `Path.update_segments()` creates a last-to-first segment when looped, but `build_station_nodes_dict()` only connects adjacent entries in `path.stations`.
- Disposition: accepted. Add the last-to-first neighbor relationship for completed looped paths and cover it in graph tests.

### Medium: path removal leaves stale travel plans

- Reported by: Codex 2, Codex 3.
- Evidence: `remove_path()` removes metros and onboard passengers from global lists, but leaves removed passengers in `travel_plans` and does not clear waiting-passenger plans that reference the removed path.
- Disposition: accepted. Remove plans for deleted passengers and invalidate/recompute plans that reference the removed path.

### Medium: `Node` equality and hash disagree

- Reported by: Codex 3.
- Evidence: `Node.__eq__` compares by station, while `Node.__hash__` hashes the node id. Nodes are stored in sets, so equal nodes must have equal hashes.
- Disposition: accepted. Hash by the same station identity used for equality and cover set behavior.

### Low: moved historical review artifact still mentions old `docs/threads/done/` path

- Reported by: Codex 2.
- Evidence: `docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `docs/threads/README.md` and validating `docs/threads/done/...` paths after the artifact was moved under `docs/threads/done/`.
- Disposition: accepted. Update the moved artifact so it remains accurate after the docs-path change.

### Low: two tests mutate `sys.path` after project imports

- Reported by: Codex 2.
- Evidence: `test/test_graph.py` and `test/test_mediator.py` import project modules before appending `../src`.
- Disposition: accepted. Move the path setup before project imports.

### Low: pinned Ruff pre-commit hook cannot parse `py313`

- Reported by: local validation after applying fixes.
- Evidence: `pre-commit run --files ...` failed because `astral-sh/ruff-pre-commit` at `v0.4.2` does not recognize `target-version = "py313"` in `pyproject.toml`, while the active local Ruff is `0.15.12`.
- Disposition: accepted. Update the Ruff pre-commit hook pin to `v0.15.12`, matching the local Ruff version and current upstream tag.

## Deferred Finding

### Medium: coarse `dt_ms` is not equivalent to repeated small ticks

- Reported by: Codex 1 only.
- Evidence: metro movement consumes at most one segment endpoint per call and spawn counters are step-based.
- Disposition: deferred. This is a broader simulation-contract decision rather than a narrow defect fix. It should be handled in a separate task that decides whether `dt_ms` is a frame-sized tick contract or whether the engine should substep/carry remainders.

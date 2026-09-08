# GM-03d implementation review: tests, typing, and dependency boundary

Baseline: `5e6186d8b331207d2a6ec583b7a82f80533f5203`

Scope: live production/test diff, with emphasis on equivalence coverage, direct-versus-facade contracts, import/type boundaries, file-size constraints, and false-green validation.

## Findings

### RESOLVED MEDIUM - The accepted closed-loop input form was not characterized, and the full suite admitted a visible behavior mutation

Evidence:

- The baseline and live implementation deliberately special-case `loop=True` with a station sequence whose last index repeats its first: `src/path_lifecycle.py:156-159` reduces `[start, middle..., start]` to the middle indices before dispatching the public add hooks.
- The new direct loop case at `test/test_path_lifecycle.py:290-298` and existing environment loop case at `test/test_env.py:300-315` cover only `[0, 1, 2]`, not the separately accepted `[0, 1, 2, 0]` representation. No test invokes `create_path_from_station_indices(..., loop=True)` with a repeated terminal start.
- Full-suite branch coverage was 96% for `src/path_lifecycle.py` and explicitly reported line 159 as unexecuted. Focused coverage of the 26 new facade/direct tests likewise reported line 159 missing.
- I monkeypatched only that de-duplication branch away in memory, without editing the worktree, then ran the complete core suite. All 535 tests still passed with the same 12 optional-RL skips. This is therefore a demonstrated false green, not a hypothetical coverage percentage concern.
- The mutation is observably wrong even though final topology looks the same: without line 159, the public add hook receives the repeated starting station, `add_station_to_path` calls `start_snap_blip`, and `Station.start_snap_blip` appends another active visual effect at `src/entity/station.py:61-62`. The later end hook still loops and finishes the path, so topology-only assertions conceal the extra player-visible state and callback.

Fix:

- Add a direct lifecycle case for `[0, 1, 2, 0]` with `loop=True` that asserts the resulting station order is exactly `[0, 1, 2]`, the path is looped, add-hook/blip events occur only for the two middle stations, and the repeated start is handled only by the end hook.
- Add or extend a real `Mediator`/`MiniMetroEnv` facade case that asserts the starting station receives no snap blip for this programmatic encoding while the middle stations retain their expected blips. Include this encoding in the seeded baseline/current differential, so the equivalence proof covers both accepted loop representations.

Disposition:

- Resolved in the live test diff. The existing direct programmatic-creation test now exercises `[0, 1, 2, 0]` with `loop=True` and freezes final station order, loop state, exact add-hook targets, exact blip targets, and the single end-hook target.
- The existing real-Mediator hook/transition test now exercises the same encoding and freezes exact add-hook identities, final path identity/order, loop state, no start-station snap blip, and one snap blip on each middle station.
- Both files remain below 500 physical lines: `test/test_path_lifecycle.py` 484 and `test/test_mediator_path_contract.py` 450.
- The focused direct/facade suite passes 20/20. Re-running the original in-memory branch-deletion mutation now produces exactly two assertion failures, one in each layer, so the demonstrated false green is closed.

## Verified non-findings

- After normalizing only `self -> host` plus `Path(...) -> get_path_factory()(...)` and `Metro() -> get_metro_factory()()`, AST comparison found all 12 extracted bodies exactly equal to baseline.
- All 12 public `Mediator` signatures remain exact, and the focused 26 direct/facade/failure tests pass.
- The fresh import check loads local `src/path_lifecycle.py` without pygame, mediator, entity, graph, route-planner, progression, simulation-context, or travel-plan modules. `PathLifecycle.__slots__ == ()`; it has no instance dictionary or retained host.
- Runtime type-hint resolution succeeds for `PathLifecycleHost`, the path-factory getter, and the metro-factory getter. The repository has no configured static type-check gate, so the Protocol is a dependency-light structural/documentation boundary rather than a separately enforced compile-time gate.
- Changed-file Ruff check and format check pass.
- Physical line counts satisfy GM-03d's frozen limits: `src/mediator.py` 984 (target at most 990; hard limit below 1,000), `src/path_lifecycle.py` 235, and every new test/support file is below 500. Mediator remains above the repository's preferred 500-line soft target, but this bounded extraction materially reduces it and meets the explicit increment acceptance boundary.

## Verification run

- `python -m unittest -v test.test_path_lifecycle test.test_mediator_path_contract test.test_mediator_path_failure_contract`: 26 passed.
- `python -m unittest` under branch coverage: 535 passed, 12 skipped; `src/path_lifecycle.py` 96%, with line 159 unexecuted.
- In-memory branch-deletion mutation plus full core suite: 535 passed, 12 skipped, confirming the false-green gap.
- After the fix, `python -m unittest -v test.test_path_lifecycle test.test_mediator_path_contract`: 20 passed.
- After the fix, the same in-memory branch-deletion mutation is rejected by both layers: 2 failures, 0 errors.
- Ruff check/format: clean for all seven changed Python files.

VERDICT: CLEAN after resolving the one MEDIUM finding.

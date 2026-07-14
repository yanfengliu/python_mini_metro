# GM-03a mediator test-suite split plan

## Intent

Split the 1,158-line `test/test_mediator.py` characterization suite into one shared fixture module and six behavior-focused test modules without changing production code, test logic, discovery count, or runtime behavior. This work unit addresses test ownership only; the 1,112-line production `src/mediator.py` remains explicitly owned by GM-03b through GM-03f.

## Frozen baseline

- Remote baseline: GM-02e Commit B `60b4174b2bbe2f92ae3abac4a44991f03caa518b`, which passed workflow run `29302064550` (`build` 36 seconds, `rl-smoke` 3 minutes 58 seconds).
- `test/test_mediator.py`: 1,158 physical lines, Git blob `a52b410258b513ded74e71a58bbea40cb1555506`, 57 unique `test_*` methods plus `setUp`, `connect_stations`, and `_build_two_station_mediator`.
- Local py313 baseline: `python -m unittest -v test.test_mediator` passed 57/57; the full suite passed 437 tests with 12 expected optional-RL skips.
- `src/mediator.py`: 1,112 physical lines. No `src/` edit is permitted in GM-03a.

## Exact partition

- `test/mediator_test_support.py`: `MediatorTestCase` containing the three existing fixture/helper methods and their required imports/path bootstrap.
- `test/test_mediator_interaction.py`: 12 tests covering input, render-resource lifecycle, layout, hover, game-over click, colors, and speed buttons.
- `test/test_mediator_routing.py`: 8 tests covering route availability, station lookup, path sharing, travel planning, and boarding-route choice.
- `test/test_mediator_paths.py`: 8 tests covering line removal, route cleanup/replanning, duplicate/loop handling, snap feedback, and path completion.
- `test/test_mediator_simulation.py`: 10 tests covering passenger/station spawning, time progression, and station-overcrowding game over.
- `test/test_mediator_passenger_flow.py`: 8 tests covering transfers, delivery counting, metro dwell/skip behavior, padding segments, and paced loading/unloading.
- `test/test_mediator_progression.py`: 11 tests covering compatibility counters, line purchases/locks, station unlocks, prices, and blink feedback.
- Delete `test/test_mediator.py`; do not leave an aggregator.

The exact 57-method allocation is the reviewed mapping captured in `raw/in-process-partition.md`. Every test appears exactly once.

## Import and discovery contract

- Each discovered module imports support only as `from test import mediator_test_support as support` and subclasses `support.MediatorTestCase`. Do not bind the base `TestCase` subclass as a module-global imported class; Python 3.13 `unittest` would inspect it as another candidate.
- `mediator_test_support.py` is intentionally outside the default `test*.py` discovery pattern.
- Each behavior module directly imports every global referenced by its moved method bodies. Imports owned only by the support fixture stay in the support module.
- Import support before production modules so the existing `src` path bootstrap remains valid in a fresh process.
- Run each new test module independently as well as together to expose hidden import/order dependencies. Do not introduce parallel execution; the fixture temporarily replaces global `pygame.draw` and restores it through `addCleanup`.

## Mechanical preservation contract

Use the frozen baseline commit, not mutable `HEAD`, as the source of truth. A verifier must compare all 60 class functions by name and attribute-free AST against `60b4174b2bbe2f92ae3abac4a44991f03caa518b:test/test_mediator.py`, require 60 unique names, require exactly the original 57 `test_*` names, and require exactly 57 unique discovered test IDs across the six modules. Preserve the six explanatory comments inside baseline test methods as documentation: compare each dedented function source segment after normalizing only the class-level indentation, in addition to AST equality.

The transformation may change only module imports, class names, inheritance expressions, and method placement. It must leave every method definition/body AST unchanged.

## Documentation and evidence

- Update `ARCHITECTURE.md` to replace the single test file with the support module and six behavior modules, and replace the stale singular oversized-test wording with the split ownership boundary.
- Add one concise completion bullet to `PROGRESS.md` after all validation passes.
- Advance the parent `STATE.md` and `EVIDENCE.md` with GM-02e B remote evidence, exact GM-03a baseline/proofs, review disposition, and A/B transaction cursor.
- Preserve all prompt and reviewer outputs under this thread. Historical artifacts that name the former file remain unchanged.
- Do not update `README.md` or `GAME_RULES.md`; player behavior and mechanics do not change.

## Validation gates

1. Before editing, pass the 57-test targeted baseline and 437-test/12-skip full baseline in py313.
2. After editing, run all six modules individually, all six explicitly together, and full `python -m unittest -v`; require 57 targeted tests and the same full-suite total/skips.
3. Run the frozen-baseline AST/name/count verifier and a unique-discovery-ID audit.
4. Require `git diff --exit-code 60b4174b2bbe2f92ae3abac4a44991f03caa518b -- src`, explicit ordinary and cached `src/` diff checks, and empty `git status --short -- src`, so staged, unstaged, and untracked production changes cannot escape the guard.
5. Require every new handwritten Python file below 500 physical lines.
6. Run Ruff check and format check on the seven new Python files, then pre-commit on the deletion, new files, changed docs, and thread artifacts.
7. Run `git diff --check`, cached-diff review, cached stat, and staged secret-pattern scan.
8. Attempt the required Codex plus Claude multi-CLI review when repository-context export is authorized and preserve exact failure evidence otherwise. In either case, perform independent in-process finder/refuter review, verify every claimed finding against live code, fix real findings, and re-review to substantive convergence. Never claim an external reviewer ran when it did not.
9. Commit A contains the split files, documentation, review artifacts, and `[GM-03a:A]` cursor. Push A and wait for exact `build` plus `rl-smoke`. Commit B records A's exact SHA/green run and advances the cursor; push B and observe its own exact CI green. Because B cannot record its future result, GM-03b's opening transaction must persist B's exact SHA/run before changing production code.

## Multi-CLI mechanics and limitation handling

- Follow the canonical runbook and repository stub. Attempt the global Codex CLI refresh first; if machine-level modification is denied, preserve the denial, record the installed version, and proceed only if it satisfies the pinned model minimum. This iteration recorded `codex-cli 0.144.3`, which satisfies the `gpt-5.6-sol` minimum.
- The pinned Codex reviewer is `gpt-5.6-sol` with `model_reasoning_effort=ultra`; the pinned Claude reviewer is `claude-fable-5[1m]` with maximum effort and `opus[1m]` fallback only when Fable is unavailable.
- Final-diff attempts write verbatim outcomes to `raw/codex.md` and `raw/opus.md`. If repository-context export remains unauthorized, those files record the exact non-launch boundary and the in-process finder/refuter becomes the completion authority.
- If Claude runs, audit `git status` immediately afterward because its allowed tools are not a hard read-only sandbox.
- Every external attempt and unavailable-reviewer fallback remains retryable in the next iteration; it never becomes evidence that the reviewer approved.

## Review directive

Every reviewer must verify each claim in this plan/diff against the live codebase by grepping symbols, function signatures, test IDs, and file paths rather than approving from prompt text. Reviewers must flag correctness defects, discovery/fixture/import regressions, body drift, duplicate or missing tests, process regressions, stale documentation, missing validation, file-size violations, and accidental behavior changes.

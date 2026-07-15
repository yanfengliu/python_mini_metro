# GM-03d - Extract topology and path lifecycle

Status: production extraction, reproducible local proofs, fresh commit-readiness re-review, changed-path hooks, and exact staged audit are complete; Commit A and remote CI remain pending

Baseline: GM-03c Commit B `5e6186d8b331207d2a6ec583b7a82f80533f5203` (`docs: finalize route planning extraction [GM-03c:B]`), remotely green in [run 29352432028](https://github.com/yanfengliu/python_mini_metro/actions/runs/29352432028). API timestamps show `build` passed in 44 seconds and `rl-smoke` in 3 minutes 44 seconds.

## Goal and acceptance boundary

Extract the 12 existing path-lifecycle transition algorithms into a stateless, non-retaining `PathLifecycle` in `src/path_lifecycle.py`. `Mediator` remains the sole canonical owner of the directly writable lists, maps, flags, entities, RNG, and public API. Every existing lifecycle method remains a real explicit `Mediator` method with its exact signature and delegates through a call-scoped `PathLifecycleHost` protocol.

GM-03d is behavior-neutral. It must finish with `src/mediator.py` below 1,000 physical lines and targets at most 990. The new lifecycle module and every new test file must remain below 500 lines. No proxy properties, `__getattr__`, inheritance mixin, retained Mediator backreference, duplicated collection, cache, proposal generator, or hidden state synchronization is allowed.

## Exact extraction set and line budget

The extraction owns only these 12 method bodies:

1. `assign_paths_to_buttons`
2. `remove_path`
3. `invalidate_travel_plans_for_path`
4. `remove_path_by_id`
5. `remove_path_by_index`
6. `start_path_on_station`
7. `create_path_from_station_indices`
8. `add_station_to_path`
9. `abort_path_creation`
10. `release_color_for_path`
11. `finish_path_creation`
12. `end_path_on_station`

At the frozen baseline their replacement envelope is 168 physical lines: `assign_paths_to_buttons` is 9, `remove_path` through the separator after `finish_path_creation` are 137, and `end_path_on_station` is 22. All replacement wrappers plus the lifecycle import and constructor installation have a 57-line hard ceiling, which yields at most 999 lines from the 1,110-line baseline. The implementation targets 45 or fewer replacement/wiring lines, projecting 987. No adjacent responsibility may be pulled into scope merely to meet the number.

Palette generation remains in Mediator because it consumes the isolated RNG and exposes the existing `mediator.hue_to_rgb` patch seam. Station-pool/progression effects remain with their current owner. Mouse/action dispatch and temporary-pointer interaction remain GM-03f. General spawning, passenger/metro flow, and game-over behavior remain GM-03e. Route planning stays in `RoutePlanner`.

## Ownership and dependency contract

`PathLifecycle` stores nothing between calls and has `__slots__ = ()`. Each call receives the current Mediator through a topology-limited structural host protocol; the component re-reads host attributes at the same expression points as the baseline. It must not retain or pre-bind `paths`, `metros`, `passengers`, `travel_plans`, path maps, path buttons, creation state, factories, or public callbacks.

The canonical directly writable objects remain on Mediator: `paths`, `metros`, `path_to_button`, `path_colors`, `path_to_color`, `is_creating_path`, and `path_being_created`. This preserves tests, checkpoints, renderers, environments, routing, passenger flow, and external code that read or replace those objects directly.

The new module has no runtime import of pygame, Mediator, entity modules, graph, route planner, progression, or simulation context. The facade passes resolver thunks for the `mediator` module-global `Path` and `Metro` factories. The lifecycle invokes each getter only at the original construction point using direct getter-call composition, so earlier mapping/entity effects can rebind the factory and the temporary callable is not retained beyond construction.

Nested lifecycle operations continue through public Mediator methods at their original points. Programmatic creation dynamically resolves public start/add/end hooks; ending dynamically resolves finish/abort; finish dynamically resolves button assignment; removal dynamically resolves invalidation, color release, button assignment, and global replanning. The lifecycle never bypasses those hooks with private component-to-component calls.

## Compatibility invariants

1. Button assignment clears every live button first, then replaces `path_to_button` with a new dict rather than clearing the old object, then assigns each zipped live path/button pair before inserting that mapping entry, and refreshes lock state last.
2. Removal is non-transactional and ordered: assigned-button removal; snapshots of `path.metros` and each `metro.passengers`; global passenger/plan cleanup; global metro cleanup; public invalidation; public color release; live path removal; public button reassignment; public global replanning.
3. Removed `Path` and `Metro` objects intentionally retain their own `path.metros` and `metro.passengers` relationships. Only the mediator-global collections and plans are cleaned.
4. Invalidation snapshots `travel_plans.items()` after building the onboard set from the then-current global metros. An onboard passenger whose immediate `next_path` survives is skipped even if a later node mentions the removed path. Existing plan objects retain identity unless the baseline deletes them.
5. Removal by ID scans the live ordered path collection and removes the first matching current `path.id`. Removal by index accepts exact `int` only, rejects `bool` and subclasses, and re-reads the live path collection between the bounds and index expressions exactly as baseline.
6. Start sets `is_creating_path` before color selection or `Path` construction. It uses the first free color within the unlocked prefix, falls back to black when none is free, creates exactly one path, installs color identity, adds the first station, marks the draft, sets the facade pointer, and appends the same path last.
7. A draft is immediately present in `paths` and retains exact station/path identity, while graph construction excludes it through `is_being_created`. Finishing flips that same object into graph visibility; no replacement path is created.
8. Programmatic creation preserves validation and public-hook ordering. The returned object is the exact path captured immediately after the public start hook, and success still depends on that object remaining in the then-current paths collection with its draft flag cleared.
9. Station comparisons use `==`, retaining ID-based station equality. Only the current last station is ignored. Returning to the first station creates a loop; adding a later non-first station removes an existing loop and appends; other non-adjacent duplicates remain appendable.
10. Snap-blip timing and count remain exact: motion onto the first station sets a loop and snaps; release onto the already-current endpoint finishes without another snap; a new release endpoint is added and snapped before finish; releasing a one-station path on its start aborts.
11. Abort sets the facade creation flag false before public color release, removes the then-current draft from the then-current paths collection, and clears `path_being_created` last. The detached path's own draft/temp/entity state is not normalized.
12. Finish clears facade/draft/temp state before resolving the `Metro` factory. Below the metro cap it creates exactly one metro, adds that identical object to the path and global list, clears `path_being_created`, then dynamically calls public button assignment. At the cap it still completes the path without a metro.
13. Partial state and exception timing remain baseline behavior. No rollback, defensive copy beyond the two existing removal snapshots, broad validation, or exception translation is introduced.
14. Protocol, task, reward, history, and training semantics remain unchanged. The new runtime module intentionally changes only the strict content fingerprint under the existing artifact drift rules.

## TDD sequence

1. Persist GM-03c Commit B's exact SHA/run and the GM-03d planning cursor before any production/test edit.
2. Run the existing topology-facing baseline. The frozen 102-test slice covers mediator paths/interaction, gameplay, environment, routing/passenger flow, recursive checkpoints/oracles, and render purity and passes at `5e6186d`.
3. Add baseline-green facade characterizations against untouched production. Freeze all 12 signatures; public callback order and mid-call rebinding; button-map replacement identity; removal snapshot/live collection semantics and detached graphs; invalidation short-circuit identity; late Path/Metro factory resolution and partial state; exact start/add/loop/end/abort/finish snapshots; same-object Path/Metro installation; bool/subclass index rejection; first-ID match; and draft graph/checkpoint visibility.
4. Add direct `PathLifecycle` host/fake tests and observe an isolated expected `ModuleNotFoundError: No module named 'path_lifecycle'` before production exists.
5. Implement the dependency-light stateless lifecycle by moving each body nearly verbatim and replacing it with the explicit public wrapper. Use fresh host reads, public hook dispatch, and factory resolver thunks at the frozen points.
6. Update `ARCHITECTURE.md`, add one concise `PROGRESS.md` bullet, append D-013 and parent state/evidence, and complete this iteration's diff/review artifacts. README and GAME_RULES remain unchanged because mechanics, controls, and public API do not change.

## Verification

- Direct lifecycle tests plus mediator path/facade characterizations and all topology/interaction/environment/routing/passenger/checkpoint/oracle/render consumers.
- Exact AST signature comparison for all 12 public lifecycle methods against `5e6186d`.
- A topology-specific seeded baseline/current differential covering non-loop creation, loop creation, abort, removal by ID and index, waiting-plan invalidation, onboard cleanup, path-button rebinding, RNG state, structured observations, and canonical checkpoints.
- `scripts/verify_path_lifecycle_differential.py` must make that seven-action/nine-record differential independently reproducible from `5e6186d` through a non-mutating `git archive`, isolated child processes, source-tree drift guards, one canonical committed result, and a machine-readable equality summary.
- Full core suite with `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
- Full exact-RL suite with `output\venv-rl\Scripts\python.exe -m unittest -v`.
- Ruff check/format on every changed Python file and pre-commit on every changed path.
- Fresh-process import proof that `import path_lifecycle` loads none of pygame, Mediator, entity, graph, route-planner, progression, or simulation-context modules.
- Protocol/task/training/content fingerprints, exact source line counts, and proof every new handwritten file remains below 500 while Mediator is at most 990 target and below 1,000 hard.
- `git diff --check`, complete ordinary/cached diff review, high-confidence staged secret scan, dependency-declaration scan, and explicit exclusion of the separate modified `AGENTS.md`, the pre-existing `.agents/` tree, and ignored `output/`.
- Three independent in-process implementation-review lanes, refutation of every finding against live baseline/current code, fixes, and clean re-review. After the user explicitly authorized review, pinned external Codex and Claude were attempted; both returned HTTP 401 authentication failures, produced no approval, and remain recorded as unavailable under the runbook fallback.

## Current execution status

- TDD reached the intended sequence: the untouched 102-test topology baseline was green; 16 mediator-facade distinctions were baseline-green; the direct contract produced only the expected missing-module loader error before production; and the first production direct/facade slice passed 26/26.
- The stateless lifecycle is implemented. `src/mediator.py` is 984 physical lines from the 1,110-line baseline, `src/path_lifecycle.py` is 235, and every changed test/support file remains below 500. All 12 public facade AST signatures match the baseline, and a fresh import loads none of the prohibited runtime modules.
- The topology-focused slice passed 156/156 before the review corrections. After the final palette coverage and durable verifier landed, the py313 core suite passes 536 tests with 12 expected optional-RL skips and the exact-RL suite passes 539/539 with no skips. Ruff check and format pass across all eight changed Python files. Protocol, task, and training fingerprints remain unchanged; the content fingerprint intentionally changed with the source boundary.
- Semantic implementation review is clean. Test review found and then closed one real gap: explicit closed-loop input `[0, 1, 2, 0]` is now frozen in direct and real-facade tests, the focused pair passes 20/20, and deleting the de-duplication branch produces exactly two assertion failures. The strengthened 10,490-byte baseline/current differential is byte-identical at SHA-256 `d6fb9dd21730f381776959c48dab8a9c87f82c7e3387646bf4ce30fd691c978d`.
- A fresh user-requested commit-readiness review accepted the semantic extraction as `CLEAN` and found two additional test/evidence gaps. Direct and real-Mediator tests now exhaust the unlocked palette while leaving a later locked color free, freezing black fallback and prefix selection; the focused direct/facade/failure slice passes 27/27 and both changed tests remain below 500 lines at 495 and 221.
- The earlier 10,490-byte digest was not independently reproducible and is superseded. The commit-bound `gm03d-path-lifecycle-v1` runner now replays exactly seven actions and nine full canonical checkpoints against archived baseline and current source in isolated processes. The single identical 135,371-byte result has SHA-256 `4ceaf17d638f932df6c3ce31cdba8789f56c0ea82748b4b2b6dcbc111d47c668`; its summary records distinct source-tree digests, result equality, and a successful `--expected` replay.
- The fresh process lane found stale external-review status, incomplete scope exclusions, and an ordinary-diff claim that could not cover untracked files. The raw 401 failures are preserved, the separate modified `AGENTS.md` and `.agents/` tree are explicit exclusions, and the exact 42-path staged cached-diff/check/secret/dependency/exclusion audit is now clean. Test/evidence and process re-reviews are `CLEAN`; implementation review is re-converged. Changed-path hooks pass all 41 hook-safe paths while preserving both UTF-16LE raw captures by digest; Commit A and both remote CI transactions remain pending.

## Remote transaction

Commit A contains lifecycle production/tests, architecture/progress, parent state/evidence/decision, and this iteration's plan/review artifacts. Suggested message: `refactor: extract path lifecycle [GM-03d:A]`. Push A and wait for the exact pinned `build` and `rl-smoke` jobs.

Commit B is evidence-only: record A's exact SHA/run/durations, finalize GM-03d, and advance the cursor. Suggested message: `docs: finalize path lifecycle extraction [GM-03d:B]`. Push B and wait for its exact CI before GM-03e. GM-03e's opening transaction records B's exact SHA/run.

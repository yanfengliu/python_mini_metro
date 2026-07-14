# GM-03b - Extract network progression ownership

Status: implemented and locally verified; Commit A pending

Baseline: `fbcb31d0321d690da56d4d7299c9720248881059` (`docs: finalize mediator test split [GM-03a:B]`), remotely green in [run 29304181859](https://github.com/yanfengliu/python_mini_metro/actions/runs/29304181859).

## Objective

Extract current line/station/economy progression state and pure policy from `Mediator` into one dependency-free `NetworkProgression` aggregate without changing game mechanics, public `Mediator` names or signatures, deterministic RNG order, checkpoint values, reward semantics, entity identity, or UI timing. `Mediator` remains the compatibility and orchestration facade.

This substep owns only the GM-03 roadmap item "progression and purchase ownership." Route planning remains GM-03c, topology/path lifecycle remains GM-03d, passenger spawning/flow remains GM-03e, and input/layout coordination remains GM-03f.

## Frozen baseline

- `src/mediator.py` has 1,112 physical lines and Git blob `73eb42b9970418b8edc7b465fda76eaa8fdaf4e1`.
- `test/test_mediator_progression.py` has 11 tests and 159 physical lines.
- The focused baseline command covering progression, passenger delivery, structured actions, and checkpoint state passed 56/56 tests.
- The only pre-existing untracked path is `.agents/`; it is outside this work unit.
- `main` and `origin/main` are equal at the baseline commit before this plan/provenance transaction.

## Reviewed ownership boundary

Add `src/progression.py` with `NetworkProgression`, which is the sole owner of:

- `num_paths`, `path_unlock_milestones`, and the mutable cached `path_purchase_prices` list;
- `num_stations`, `initial_num_stations`, and `station_unlock_milestones`;
- `deliveries`, `line_credits`, and `purchased_num_paths`;
- the mutable cached `unlocked_num_paths` and `unlocked_num_stations` values;
- pure price, affordability, sequential-purchase, unlock-count, delivery-award, and purchase-mutation policy.

`NetworkProgression` must not import pygame, `Mediator`, `Station`, `PathButton`, or any entity/UI module; hold a mediator backreference; capture station/button collections; consume RNG; or use wall-clock time.

Keep on `Mediator`:

- explicit read/write properties for every moved public field; no `__getattr__`, `__setattr__`, generated magic facade, or duplicate scalar/config storage;
- all existing public progression method signatures as real wrappers;
- `all_stations`, `stations`, `path_buttons`, `buttons`, `path_to_button`, and every other entity/UI collection;
- live button membership/lock validation, active-station slicing, button lock application, unlock blinks, and exact `time_ms` use;
- delivery detection/removal and the existing per-passenger sequence: award delivery and credit, call public `update_unlocked_num_paths()`, then call public `update_unlocked_num_stations()`.

## Compatibility invariants

1. `_progression` is installed before the first forwarded property read in `Mediator.__init__`. Construction performs only copies/sorts/arithmetic and preserves station-generation then path-color RNG order.
2. Moved lists remain live mutable component-owned list objects. Property getters return those same objects; setters perform raw assignment without copying, validation, coercion, recomputation, or eager synchronization.
3. Initialization preserves current one-time behavior: milestone inputs become sorted copies, cached prices are calculated once, and cached unlock counts initialize through the public facade methods so hypothetical subclass overrides retain the current constructor seam.
4. Direct writes remain stale until explicit updates: changing `deliveries` does not immediately update station unlocks; changing `purchased_num_paths` does not immediately update line unlocks; changing milestones does not automatically rebuild cached prices.
5. Lowering deliveries may lower cached `unlocked_num_stations` but must not shrink the active station list. Replacing a short active list may restore the prefix without blinking when the cached count does not increase.
6. Path lock states refresh on every explicit path-unlock update, including no-change and decreasing-count calls; only increasing counts blink newly unlocked buttons.
7. Purchases remain sequential; reject unlocked, foreign, skipped, negative, out-of-range, and unaffordable targets without mutation. A purchase subtracts only credits, increments purchased-line count, then calls the public path-unlock wrapper.
8. `deliveries`, `line_credits`, `total_travels_handled`, `score`, moved config/caches, public methods, structured observations, renderer duck typing, checkpoint shape, and pixel/structured rewards remain behaviorally identical.
9. Adding `src/progression.py` intentionally changes the strict RL content fingerprint. Historical artifacts continue to fail closed unless the existing explicit content-drift override is supplied; protocol, task, history, and reward fingerprints do not change.
10. No speculative save schema is introduced. GM-07 will serialize an explicit versioned snapshot through stable fields rather than pickle private object layout; GM-10 may evolve the private component while retaining the facade.

## TDD and implementation sequence

1. Persist GM-03a Commit B's exact SHA/run and this reviewed GM-03b resume cursor before production edits.
2. Add baseline-green facade characterizations for foreign/unlocked/invalid purchase non-mutation, multi-slot button/station unlocks, same-time blinks, direct-write stale caches, delivery rewind/non-shrinking station lists, live mutable config-list semantics, constructor RNG/pool identity, repeated lock refresh, and per-delivery public-hook order.
3. Add direct `NetworkProgression` contract tests. Confirm the expected red import failure before creating the module.
4. Implement the dependency-free aggregate and explicit facade properties/wrappers. Preserve public-to-public dispatch where the live facade currently provides an extension/monkeypatch seam, especially delivery update hooks and purchase orchestration.
5. Leave `env.py`, rendering, checkpoints, agent play, and RL consumers unchanged so their existing suites prove facade compatibility.
6. Update `ARCHITECTURE.md` for the new ownership boundary and tree, and add one concise `PROGRESS.md` bullet. Leave `README.md` and `GAME_RULES.md` unchanged because mechanics and public API do not change.

## Verification

- Focused direct progression and all six mediator behavior modules.
- Coupling suites: `test_env`, `test_gameplay`, `test_graph`, `test_game_renderer`, `test_recursive_checkpoint`, and `test_player_env`.
- Differential/checkpoint evidence against seeded baseline scenarios, including purchases, multi-threshold unlocks, and delivery-hook ordering.
- Full core suite with `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
- Full exact-RL suite with `output\venv-rl\Scripts\python.exe -m unittest -v`.
- Ruff check/format on every changed Python file and pre-commit on every changed path.
- Report every changed handwritten file's line count; the new module targets fewer than 500 lines. The explicit facade settles at 1,193 lines, a temporary 81-line increase over baseline: GM-03c must reverse the trajectory and finish below 1,112, GM-03d must cross below 1,000, and later clusters continue toward the practical under-500 target without opaque delegation.
- `git diff --check`, ordinary/cached diff review, staged secret scan, and explicit proof that `.agents/`, ignored `output/`, and unrelated paths are excluded.
- Three independent in-process implementation-review lanes plus independent refutation and clean re-review. External pinned reviewers remain recorded as unavailable because repository-context export was not separately authorized after disclosure; no bypass or reroute is permitted.

## Remote transaction

Commit A contains the aggregate, facade, tests, architecture/progress updates, parent state/evidence, and this iteration's plan/review artifacts. Suggested message: `refactor: extract mediator progression [GM-03b:A]`. Push A and wait for the exact pinned `build` and `rl-smoke` jobs.

Commit B is evidence-only: record A's exact SHA/run/durations, finalize GM-03b, and advance the cursor. Suggested message: `docs: finalize mediator progression extraction [GM-03b:B]`. Push B and wait for its exact CI before GM-03c. GM-03c's opening transaction records B's exact SHA/run.

# GM-03c - Extract pure route planning

Status: Commit A remotely green; evidence-only Commit B pending

Baseline: `00ea38c2dbee3fd51985ae9c52377ae404502e29` (`docs: finalize mediator progression extraction [GM-03b:B]`), remotely green in [run 29311017088](https://github.com/yanfengliu/python_mini_metro/actions/runs/29311017088).

## Objective

Extract deterministic route search, route compression, constrained first-line selection, and lazy boarding/bulk route proposals from `Mediator` into one stateless `RoutePlanner` without changing game mechanics, public `Mediator` names or signatures, Python RNG consumption, graph/BFS order, object identity, travel-plan mutation timing, checkpoint values, reward sequences, or passenger delivery behavior. `Mediator` remains the compatibility and side-effect facade.

This substep owns only pure/query planning plus the planning portion of boarding-candidate discovery. Topology/path lifecycle remains GM-03d; passenger ownership, arrival/removal, loading/unloading, dwell, and transfers remain GM-03e; input/layout remains GM-03f.

## Frozen baseline

- `src/mediator.py` has 1,193 physical lines and Git blob `c6a2f5db97db955fd42e8a58a26b73ed70d89a70` at baseline. GM-03c must finish at no more than 1,111 lines and targets no more than 1,110.
- The public tail cluster begins at `get_stations_for_shape_type()` on line 1,049 and ends at line 1,193. The planning portion of `get_boarding_candidates_for_metro()` spans lines 828-860.
- `test/test_mediator_routing.py` has eight tests and 270 physical lines.
- Routing, passenger-flow, path-lifecycle, simulation, graph, recursive-checkpoint, and structured-environment coverage passes 80/80 tests in 0.409 seconds.
- `main` and `origin/main` equal the baseline commit. The only pre-existing untracked path is `.agents/`; it is outside this unit.

The two in-scope mediator regions total 178 baseline lines. All replacement wrappers, retained mutation orchestration, the planner import, and planner initialization together may consume at most 96 physical lines for the 1,111 hard gate and target at most 95 for 1,110. The code-shaped ceiling is: at most two lines for import/installation, 21 for lazy boarding facade/application, 43 for seven query/constrained-plan wrappers, and 30 for lazy bulk-plan facade/application. The planner wires newly factory-created constrained plans while they are still unowned and handles next-hop field logic through resolver thunks; bulk plans remain installed by Mediator before the public next-hop wrapper runs. Both boarding and bulk planning use lazy proposal iterators from the first implementation. GM-03c does not commit above 1,111 or take unrelated GM-03d/e ownership to reach the number.

## Reviewed ownership boundary

Add `src/route_planner.py` with a stateless `RoutePlanner`. It receives explicit collections, already ordered destination candidates, a freshly built station-node graph, and live callbacks. It owns no collection, entity, RNG, clock, graph, route plan, or cache between calls and never imports `Mediator`.

Extract into the planner:

- station filtering by destination shape, before the facade performs the shuffle;
- ordered first-shared-path and path-ID queries;
- cached-plan eligibility query;
- in-place same-line node compression that returns the exact input list;
- unconstrained best-node-path selection with immediate-arrival signaling;
- required-first-path best-node-path selection;
- lazy boarding-candidate proposal over a live passenger iterable, yielding the passenger plus either an existing-plan marker or the one newly computed `TravelPlan` before the next passenger is requested;
- lazy bulk route proposal over live station/passenger iterables, yielding immediate-arrival, reachable-node-path, or unreachable results while leaving every result mutation to the facade before the generator resumes.

Keep on `Mediator`:

- `context.python_random.shuffle()` and its exact call count/order;
- all three `build_station_nodes_dict()` call sites and fresh ephemeral `Node` identity;
- real public wrappers for all current route-planning methods and public-to-public dispatch through those wrappers;
- `travel_plans` ownership and every assignment/deletion, arrival flag, station/global passenger removal, transfer cursor update, unreachable `TravelPlan([])` insertion, and boarding proposal application;
- path invalidation/removal, topology ownership, metro motion/dwell, loading/unloading, station capacity, and delivery/progression effects.

## Planned component contract

`RoutePlanner` uses explicit inputs and resolver thunks rather than a host protocol or mediator backreference. Dispatch callbacks such as `lambda start, end: bfs(start, end)` perform the module-global lookup inside their body on every invocation; bound callables use getters such as `lambda: self.skip_stations_on_same_path`, `lambda: self.find_shared_path`, and `lambda: TravelPlan`. The planner directly composes each getter result with its call so resolution occurs before argument evaluation (`list(raw)`, `reduced[1]`, or `selected[1:]`) and the temporary callable is released immediately after the call. Passing a captured `bfs` function, bound method, mutable path ID, or travel-plan mapping is forbidden because baseline re-resolves those values at each original comparison/read point and can observe callback, finalizer, or mapping operations rebinding the next value. Concrete domain imports may be under `TYPE_CHECKING`; runtime behavior stays dependency-light and pygame-free.

The unconstrained selector returns:

- the exact one-node BFS list for immediate arrival;
- the selected reduced list containing the exact supplied `Node` objects for a reachable route;
- `None` when unreachable.

The required-first selector receives a Mediator-supplied `TravelPlan` factory and a required-path-ID resolver. It invokes the ID resolver only after each non-`None` shared-path callback, at the baseline short-circuited comparison point. After selecting a node path, the planner invokes the factory once, wires the newly created unowned plan through its `get_next_station()` method and a freshly resolved public shared-path callback, and returns it. This preserves constrained baseline order without importing the domain class. Bulk plans are different: Mediator constructs and installs each reachable plan in `travel_plans` before calling the public next-hop wrapper, because baseline hooks can observe the installed mapping entry.

The lazy boarding iterator yields `tuple[Passenger, TravelPlan | None]`: `None` means the passenger's existing plan already matches the freshly resolved `metro.path_id`; a non-`None` value is the one plan constructed by the facade callback for the canonical `metro_path` returned by public `get_path_by_id()`; ineligible passengers produce no yield. The path-ID resolver runs only after a current plan and its next path pass the baseline short-circuit checks. The facade consumes the iterator directly, never materializes it, and applies a yielded new plan inside the loop body before the next `next()`. It never recomputes a yielded plan.

The lazy bulk iterator reads the live station/passenger iterables and freshly resolves the public cached-plan and destination callbacks for each visited passenger, but never mutates them. It yields explicit `(station, passenger, node_path, kind)` proposals where `kind` is `arrival`, `route`, or `fallback`. Raw one-node BFS output alone produces `arrival`; a raw multi-node path reduced to one node remains `route` and is never reclassified by the facade. Arrival is two-phase: the iterator yields `arrival` while the destination iterator is suspended, Mediator applies station/global removal, the destination flag, and plan deletion, then resumption finalizes the destination iterator before the same-passenger `fallback` proposal evaluates the original guard. The bulk selection loop stays in the proposal generator frame so the destination container/item, raw/reduced paths, nodes, and costs remain live through the facade effect exactly as in the monolithic baseline. For a reachable result, Mediator constructs and installs the plan first, then calls public `find_next_path_for_passenger_at_station()`; the wrapper delegates field updates to the planner using fresh plan-map and shared-path resolver thunks, preserving hook visibility and replacement semantics. For a fallback result Mediator inserts `TravelPlan([])` only under `not passenger.is_at_destination and passenger not in self.travel_plans`; retries preserve the exact existing empty-plan object. Because each result is applied before the generator resumes against the same live list, baseline adjacent-arrival skip timing is retained.

## Compatibility invariants

1. Destination filtering preserves active-station order and returns a new list. The facade shuffles it exactly once per current planning attempt. Equal-cost candidates use strict `<`, so the first shuffled candidate wins.
2. Unreachable passengers retain `TravelPlan([])`, are treated as unplanned, and consume another destination shuffle on every retry.
3. Bulk planning continues to mutate the live `station.passengers` list while iterating it. The explicit arrival then fallback phases occur before the outer iterator advances, so the current adjacent-arrival skip-until-next-call behavior is characterized and preserved; no defensive copy is introduced.
4. An unreachable retry preserves the exact existing `TravelPlan([])` object. The facade inserts a new empty sentinel only when the passenger is not at destination and is absent from `travel_plans`.
5. Boarding lookahead with `mutate_travel_plans=False` still performs constrained planning and consumes RNG but does not mutate the map. With `True`, the mediator applies each yielded plan before the planner requests the next passenger.
6. An absent `metro.path_id` short-circuits immediately after the public `get_path_by_id()` lookup: it does not inspect passengers, invoke constrained planning, consume RNG, or mutate `travel_plans`.
7. Raw BFS length is the primary cost and reduced-node length is the secondary cost. Only a raw one-node path is arrival; compression cannot create an arrival. Required-first routing rejects raw paths of length at most one, reduced paths of length at most one, missing shared paths, and first-path ID mismatches.
8. `skip_stations_on_same_path()` mutates and returns the caller's exact list. It retains exact `Node`, `Station`, and `Path` objects and path-set membership.
9. Graph construction remains fresh and uncached. No station/path IDs replace object identity, and no graph, route, destination, or plan cache is added.
10. `find_shared_path()` retains first `self.paths` match semantics, including non-adjacent stations and current in-progress-path behavior. GM-03c does not reconcile that query with graph construction's in-progress-path exclusion.
11. `TravelPlan.get_next_station()` retains its `next_station` cache mutation. Constrained plans are wired while unowned; reachable bulk plans are inserted in `travel_plans` before the public next-hop hook, and that hook freshly resolves the current map entry for each baseline read/write. `next_station_idx` advances only through the existing transfer method.
12. Every current public route method keeps its exact signature and remains a real method. Calls from simulation, boarding, transfers, removal, tests, and monkeypatches continue through the public facade.
13. Resolver thunks freshly look up the `mediator` module-global `bfs`, public facade methods, mutable path IDs, and the `travel_plans` attribute on every baseline read. Callable getters resolve before their argument expressions and their results are not retained beyond the call, preserving destructor side effects as well as rebinding. A first destination/passenger callback or mapping operation that rebinds one of those values changes the next read exactly as at baseline; station/path iteration, invocation, first-match lookup, exception/short-circuit order, destination-iterator finalization, and selection-local lifetime remain unchanged.
14. Constrained planning shuffles destinations first, then resolves `station_nodes_dict[station]` exactly once even when the destination sequence is empty. Bulk planning resolves that start-node mapping inside each destination iteration and performs no lookup when the sequence is empty. Custom-mapping access and exception order remain observable.
15. Protocol, task, training, history, and reward semantics remain unchanged. Adding `src/route_planner.py` intentionally changes only the strict content fingerprint and therefore remains subject to the existing explicit content-drift rules for historical RL artifacts.

## TDD and implementation sequence

1. Persist GM-03b Commit B's exact SHA/run and this reviewed GM-03c resume cursor before production edits.
2. Add baseline-green facade characterizations for public helper overrides/call order, callback and plan-map rebinding between iterations/hooks, constrained-versus-bulk station-node lookup/exception order including empty destinations, same-list compression identity, equal-cost first-candidate ties, raw-before-reduced ranking, required-first path ID/identity, retry RNG consumption and empty-sentinel identity preservation, read-only boarding lookahead RNG/non-mutation, existing-plan reuse, absent-path no-inspection/no-RNG short-circuit, one-plan-per-yield/no-recomputation, constrained-unowned versus bulk-installed hook visibility, lazy apply-before-resume, arrival mutation timing, and exact `Node`/`Station`/`Path` identity.
3. Add direct `RoutePlanner` contract tests and observe the expected missing-module red failure before creating the module.
4. Implement the stateless planner, install it without RNG or collection capture, and replace each public method body with an explicit wrapper. Keep live mutation in the facade.
5. Extract the two reviewed lazy proposal iterators needed for the size gate. Leave candidate/result application, passenger flow, capacity, dwell, arrival/removal, TravelPlan map mutation, and metro effects on `Mediator`.
6. Update `ARCHITECTURE.md` for the new module/boundary and add one concise `PROGRESS.md` bullet. Leave README and GAME_RULES unchanged because mechanics and public API do not change.

## Verification

- Direct planner tests plus every mediator behavior module, graph, gameplay, environment, recursive checkpoint, recursive oracles, renderer, and pixel-environment consumers.
- Seeded differential evidence against `00ea38c`: destination/BFS call trace, RNG state, exact route node/path identities, reward sequence, and canonical checkpoint bytes.
- Exact AST signature comparison for every public route-planning facade method.
- Full core suite with `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
- Full exact-RL suite with `output\venv-rl\Scripts\python.exe -m unittest -v`.
- Ruff check/format on every changed Python file and pre-commit on every changed path.
- A fresh-process import assertion proves `import route_planner` does not load pygame; concrete `Path`, `Station`, `Passenger`, `Node`, and `TravelPlan` imports remain type-checking-only.
- `src/mediator.py` must be at most 1,111 physical lines and targets at most 1,110; `src/route_planner.py` and every changed test file must remain below 500.
- `git diff --check`, complete ordinary/cached diff review, staged secret scan, and explicit proof that `.agents/`, ignored `output/`, and unrelated paths are excluded.
- Three independent in-process implementation-review lanes plus refutation and clean re-review. External pinned reviewers remain unlaunched because the user's Git/CI authorization did not authorize repository-context export after the platform disclosure; no reroute is permitted.

## Remote transaction

Commit A contains the planner, facade, tests, architecture/progress updates, parent state/evidence, and this iteration's plan/review artifacts. Suggested message: `refactor: extract route planning [GM-03c:A]`. Push A and wait for the exact pinned `build` and `rl-smoke` jobs.

Commit B is evidence-only: record A's exact SHA/run/durations, finalize GM-03c, and advance the cursor. Suggested message: `docs: finalize route planning extraction [GM-03c:B]`. Push B and wait for its exact CI before GM-03d. GM-03d's opening transaction records B's exact SHA/run.

# GM-03e passenger-flow extraction plan

Status: Commit A `7ac89cf` and exact run `29719845761` are green; evidence-only Commit B is active

Transaction marker: `[GM-03e:A]`

## Baseline and intent

GM-03d is remotely finalized at Commit B `b1e419e21080fd5bd43e1ac6a4eef7e264f732ec`, whose exact workflow run `29386306430` passed. The actual repository baseline is the later policy-only HEAD `2c4cd4fe484222549fd177455dd413859983ad50`, whose exact workflow run `29411000340` passed; the intervening commits do not change runtime, tests, dependencies, or gameplay.

Extract passenger spawning, simulation tick coordination, metro stop/exchange decisions, passenger movement, delivery effects, and waiting/game-over evaluation from `Mediator` without changing mechanics, public signatures, directly writable state, object identity, ordering, exception behavior, deterministic RNG, observations, checkpoints, rendering, recursive evidence, or RL contracts.

## Frozen boundary

Add dependency-light `src/passenger_flow.py` with a stateless, non-retaining `PassengerFlow` using `__slots__ = ()` and one call-scoped structural host. Extract exactly these 16 public algorithm bodies from the live `Mediator`: the contiguous passenger/simulation envelope `get_station_shape_types`, `is_passenger_spawn_time`, `initialize_station_spawning_state`, `get_station_spawn_interval_step`, `should_spawn_passenger_at_station`, `spawn_passengers`, `increment_time`, `get_next_station_for_metro`, `get_boarding_candidates_for_metro`, `get_unloading_candidates_for_metro`, `should_stop_at_next_station`, `start_station_stop_if_needed`, `can_board_at_station`, `move_passengers`, and `update_waiting_and_game_over`, plus the later passenger-effect loop `find_travel_plan_for_passengers`. GM-03c keeps route queries and proposal generation in `RoutePlanner`; GM-03e moves the passenger-owned application of those proposals while leaving the intervening route facade methods in place.

`Mediator` keeps a real method with the exact existing signature for every extracted method. It remains the canonical owner of `stations`, `paths`, `metros`, `passengers`, `travel_plans`, spawn maps and configuration, RNG context, clocks and counters, pause/speed/game-over flags, overload configuration, progression, routing, factories, entities, and every public compatibility hook. Each component call receives the current facade only for that call; the component stores no facade, collection, callback, RNG, graph, entity, or cache across calls.

Late module-global construction and collaborator dependencies remain facade-owned. The `spawn_passengers` wrapper supplies getter thunks for the current `Passenger`, `get_shape_from_type`, `passenger_color`, and `passenger_size` objects; graph/search/plan wrappers supply getter thunks for the current `build_station_nodes_dict`, `bfs`, and `TravelPlan` objects. Boarding and bulk planning receive thunks that resolve the current `_router.iter_boarding_candidates` and `_router.iter_bulk_route_proposals` bound methods once at their original iterator-construction points. Passenger movement receives a thunk that re-resolves the current `_progression.record_delivery` bound method for each delivered passenger at the original award point. No wrapper or component captures those values, collaborators, or bound methods earlier or retains them after the call.

## Non-scope reserved for GM-03f

Do not move or redesign layout, renderer compatibility, game-over click handling, mouse/keyboard/event dispatch, hit testing, pause/speed/action input methods, `step_time`, path-button purchase/UI effects, or their canonical fields. GM-03e may read `is_paused`, `game_speed_multiplier`, and `is_game_over` exactly as the current tick does, and may set terminal state only through the existing waiting-threshold algorithm.

Do not change progression, route planning, path lifecycle, spawning constants, station/metro/passenger mechanics, reward meaning, action schemas, checkpoints, manifests, training defaults, renderer output, or the local `civ-engine` pin.

## Compatibility invariants

1. Paused or terminal ticks return before reading speed, advancing clocks, initializing spawn state, pruning effects, building graphs, moving metros, drawing RNG, planning routes, moving passengers, or changing waiting time.
2. An active tick reads the speed multiplier once, derives one scaled delta, advances `time_ms` then `steps`, initializes active-station spawn state, increments each live station counter, and prunes that station before any graph build or metro effect.
3. The tick builds the pre-move graph once, iterates the live path and metro collections without snapshots, invokes the public stop hook before movement when needed, invokes the public stop-decision hook, moves the metro, and invokes the public stop hook again after a qualifying arrival.
4. One active tick performs three distinct fresh graph builds in order: pre-metro movement, bulk travel-plan application, then passenger exchange. No graph or builder result is cached or shared across those phases; each phase resolves the current facade-supplied builder at its original call point so topology and callback rebinding between phases remain observable.
5. Spawn probing retains `any(...)` short-circuit behavior and uses public `should_spawn_passenger_at_station` dispatch. Spawning preserves active-station order, public shape-type and due checks, destination filtering, RNG draw counts/order, late per-due-station shape-factory/color/size/passenger lookups, and full-station construction-and-discard behavior. The due counter resets only after the entire attempt returns without exception, including a full-station discard; an exception from destination choice, any late global/factory, room/add/append effect, or counter write preserves the exact partial state and may leave the counter unchanged.
6. Spawn-state initialization samples exactly once per missing interval, initializes a missing counter from the then-current interval, preserves existing entries, and resolves the public interval hook separately for each new station.
7. Boarding returns immediately when the live metro path lookup fails, without resolving the proposal iterator, inspecting station passengers, or consuming RNG. Otherwise it resolves the current iterator method once after the empty candidates list is created, preserves lazy proposal order, re-reads `metro.path_id`, dynamically resolves the public constrained-plan callback for each passenger, installs each proposed plan before the iterator resumes when mutation is enabled, and returns exact passenger objects in order.
8. Stop decisions and dwell setup preserve destination/transfer classification, capacity release rules, public hook ordering, no-plan behavior, and the existing graph object passed into boarding checks.
9. Passenger exchange consumes one action slot per `boarding_time_per_passenger_ms` in exact priority order: destination unload, transferable unload when the station has room, then boarding when the metro has room. Fractional progress, overshoot, speed zeroing, and remaining dwell time retain exact arithmetic and mutation timing.
10. Delivery marks the exact rider arrived, removes it from metro/global passenger collections and the live plan map, re-resolves and calls the current progression delivery hook for that rider, then dynamically invokes public path-unlock and station-unlock hooks in that order. No rollback or exception translation is added.
11. Transfer moves the exact rider from metro to station before resetting wait, advances the existing plan, then dynamically invokes the public next-path hook. Boarding moves the exact rider from station to metro before resetting wait.
12. When unused action slots cannot make progress because transfer space or metro capacity is unavailable, stop time and boarding progress clear at the exact existing condition; metros do not acquire a new parking state.
13. Waiting updates only station-held passengers in live station/passenger order, increments every one before evaluating the threshold, counts the inclusive maximum-wait boundary, and sets game over only after the full scan.
14. Bulk planning resolves the current proposal iterator once after the fresh graph is built and before its arguments are evaluated. Proposal application preserves generator suspension and finalization timing: arrival removes the exact rider from the station and global collection, marks arrival, and deletes the live plan entry before the iterator resumes; route re-resolves and constructs one plan before dynamically invoking the public next-path hook; fallback re-resolves and constructs a fresh empty sentinel only after the iterator's same-rider arrival/finalizer effects and live guards complete.
15. Public method signatures, dynamic public-to-public dispatch, direct writable collection replacement, partial-state exceptions, entity identity, list/map identity, and callable lifetime remain baseline behavior. Baseline-green characterization explicitly covers rebinding and exception/destructor timing for late factories, globals, proposal iterators, graph/search functions, plan construction, and delivery progression.
16. The new module imports no pygame, mediator, entity, graph, progression, route-planner, simulation-context, travel-plan, rendering, or UI module at runtime.
17. Protocol, task, reward, history, trainer, and manifest semantics remain unchanged. The new runtime module intentionally changes only content/source identity under existing drift rules.

## Size contract

The frozen production envelope is lines 591-914 plus 963-984 of the 984-line baseline `src/mediator.py`. An explicit line-for-line wrapper model removes 346 lines and adds 97 wrapper/import/install lines, projecting `984 - 346 + 97 = 735` before formatting variance. The implementation must target `src/mediator.py` at or below 740 physical lines with a 750-line hard ceiling, target `src/passenger_flow.py` at or below 480 and require it below 500, keep every new handwritten support/test/script file below 500, and avoid consuming GM-03f scope merely to improve the number.

## TDD and implementation sequence

1. Reconcile `STATE.md` and `EVIDENCE.md` in the GM-03e working tree with GM-03d Commit B, its exact green CI, and actual green HEAD. Retain those edits for GM-03e Commit A rather than creating a third GM-03d metadata commit.
2. Freeze the untouched-production baseline: the 110-test passenger/simulation/route/path/overload/environment/checkpoint/oracle/render slice passes at `2c4cd4f`.
3. Add baseline-green facade characterizations for all 16 signatures plus public hook rebinding, short-circuit reads, late factories/graph/search/plan construction, generator suspension/finalization, live collection iteration, RNG order, exchange/delivery/transfer/arrival/route/fallback ordering, partial failures, and exact tick ordering.
4. Add direct `PassengerFlow` host tests while production remains untouched. The isolated first run must fail only with `ModuleNotFoundError: No module named 'passenger_flow'`.
5. Implement the stateless component by moving algorithm bodies nearly verbatim, replacing self-state with call-scoped host reads, preserving public dispatch, and using facade-supplied resolver thunks only at original lookup points.
6. Run focused direct/facade/consumer tests, an AST signature comparison against `2c4cd4f`, import-isolation proof, line-budget proof, and `scripts/verify_passenger_flow_differential.py`. The verifier must non-mutatingly materialize exact baseline `2c4cd4f` through `git archive`, run baseline and candidate scenarios in isolated bytecode-disabled child processes, guard each runtime source tree against before/after drift, cover seeded spawn plus metro stop/board/transfer/delivery plus pause/speed plus waiting/game over plus all three graph phases, and emit one canonical committed result containing RNG, structured observations, canonical checkpoints, and mutation-sensitive event traces. Those traces must explicitly distinguish arrival, route, and fallback proposal effects; destination-iterator finalization; adjacent live-list skipping; and reducer/plan-factory callable release order. A digest summary and required `--expected` replay must reproduce the committed bytes exactly.
7. Update `ARCHITECTURE.md`, add one concise `PROGRESS.md` bullet, add reviewed decision D-014, finalize this iteration's `REVIEW.md` and `diff.md`, and keep README/GAME_RULES unchanged because behavior and public API do not change.

## Verification and review

- Focused passenger-flow/direct/facade plus every simulation, routing, environment, recursive-checkpoint/oracle, rendering-purity, and spawn-cadence consumer.
- Full core suite in py313 and full exact-RL suite in `output/venv-rl`.
- Ruff check and format on every changed Python file; pre-commit on every changed path, followed by inspection and rerun if hooks modify anything.
- Exact public-signature comparison, fresh import isolation, source line counts, protocol/task/training fingerprint checks, and the non-mutating archived-baseline differential with committed canonical result, digest summary, drift guards, and `--expected` replay.
- Ordinary and staged cached diff/check, secret scan, dependency-declaration scan, and explicit exclusion of the pre-existing untracked `.agents/` tree and ignored `output/` evidence.
- Independent in-process plan/implementation refuters plus pinned Codex and Claude review under the current fleet runbook. Reviewers must read live code; every finding is verified before changes; substantive findings are fixed and re-reviewed.

## Remote transaction

Commit A contains production, tests, reproducible evidence, architecture/progress, parent state/evidence/decision updates, and this iteration's plan/review artifacts. Suggested message: `refactor: extract passenger flow [GM-03e:A]`. Push A and wait for its exact `build` and `rl-smoke` jobs.

Commit B is evidence-only: record A's exact SHA/run/durations, finalize GM-03e, and leave GM-03f's opening transaction to record B's exact green result. Suggested message: `docs: finalize passenger flow extraction [GM-03e:B]`. Push B and wait for its exact CI before GM-03f implementation begins.

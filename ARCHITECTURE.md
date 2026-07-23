python_mini_metro/
|- .gitattributes
|- .npmrc
|- .github/
|  \- workflows/
|     \- test.yml
|- .vscode/
|  \- settings.json
|- docs/
|  |- rl-model-selection.md
|  \- threads/
|     |- README.md
|     |- current/
|     |  |- README.md
|     |  \- game-maturity/
|     \- done/
|        |- README.md
|        |- agents-repo-fit/
|        |- full/
|        |- rendering/
|        \- rl-framework/
|- scripts/
|  |- evaluate_rl.py
|  |- fixtures/
|  |  |- checkpoint-v1.json
|  |  |- checkpoint-v2.json
|  |  |- checkpoint-v3.json
|  |  |- gm06b-legacy-outcomes.json
|  |  |- gm06c-pre-carriage-outcomes.json
|  |  |- recursive-playtest-v1.json
|  |  |- recursive-playtest-v2.json
|  |  |- recursive-playtest-v3.json
|  |  |- recursive-playtest-v4.json
|  |  |- recursive-playtest.json
|  |  \- save-v1.json
|  |- playtest-recursive.mjs
|  |- playtest-verify.mjs
|  |- input_coordinator_differential_actions.py
|  |- input_coordinator_differential_input.py
|  |- input_coordinator_differential_support.py
|  |- passenger_flow_differential_support.py
|  |- profile_rl_history.py
|  |- profile_rl_history_worker.py
|  |- recursive-ledger.mjs
|  |- recursive-ledger-lock.mjs
|  |- recursive-args.mjs
|  |- recursive-pass.mjs
|  |- civ-engine-guard.mjs
|  |- civ-engine-pin.json
|  |- civ-engine-pin.mjs
|  |- civ-engine-runtime.mjs
|  |- civ-engine-setup.mjs
|  |- civ-engine-setup-build.mjs
|  |- civ-engine-setup-clone.mjs
|  |- civ-engine-setup-content.mjs
|  |- civ-engine-setup-git-config.mjs
|  |- civ-engine-setup-operations.mjs
|  |- civ-engine-setup-process.mjs
|  |- civ-engine-setup-promotion.mjs
|  |- civ-engine-setup-root-contract.mjs
|  |- civ-engine-setup-safety.mjs
|  |- node-startup-contract.mjs
|  |- source-provenance-content.mjs
|  |- source-provenance-engine-safety.mjs
|  |- source-provenance-engine.mjs
|  |- source-provenance-git-safety.mjs
|  |- source-provenance.mjs
|  |- train_rl.py
|  |- verify_input_coordinator_differential.py
|  |- verify_passenger_flow_differential.py
|  \- verify_path_lifecycle_differential.py
|- src/
|  |- __init__.py
|  |- agent_play.py
|  |- app_controller.py
|  |- carriage_management.py
|  |- carriage_transaction_snapshot.py
|  |- config.py
|  |- env.py
|  |- fleet_input.py
|  |- fleet_management.py
|  |- fleet_validation.py
|  |- game_clock.py
|  |- game_session.py
|  |- highscores.py
|  |- input_coordinator.py
|  |- input_coordinator_host.py
|  |- main.py
|  |- mediator.py
|  |- passenger_capacity.py
|  |- passenger_flow.py
|  |- path_handle_geometry.py
|  |- path_handle_input.py
|  |- path_handles.py
|  |- path_lifecycle.py
|  |- path_redraw.py
|  |- path_removal_snapshot.py
|  |- path_replacement.py
|  |- path_replacement_geometry.py
|  |- path_replacement_snapshot.py
|  |- progression.py
|  |- route_planner.py
|  |- recursive_checkpoint.py
|  |- recursive_checkpoint_carriages.py
|  |- recursive_checkpoint_schema.py
|  |- recursive_contract.py
|  |- recursive_oracles.py
|  |- recursive_playtest.py
|  |- save_game.py
|  |- save_load.py
|  |- save_schema.py
|  |- save_schema_records.py
|  |- simulation_context.py
|  |- travel_plan.py
|  |- type.py
|  |- utils.py
|  |- entity/
|  |  |- carriage.py
|  |  |- get_entity.py
|  |  |- holder.py
|  |  |- metro.py
|  |  |- padding_segment.py
|  |  |- passenger.py
|  |  |- path.py
|  |  |- path_segment.py
|  |  |- segment.py
|  |  \- station.py
|  |- event/
|  |  |- convert.py
|  |  |- event.py
|  |  |- keyboard.py
|  |  |- mouse.py
|  |  \- type.py
|  |- geometry/
|  |  |- circle.py
|  |  |- cross.py
|  |  |- diamond.py
|  |  |- line.py
|  |  |- pentagon.py
|  |  |- point.py
|  |  |- polygon.py
|  |  |- rect.py
|  |  |- shape.py
|  |  |- star.py
|  |  |- triangle.py
|  |  |- type.py
|  |  \- utils.py
|  |- graph/
|  |  |- graph_algo.py
|  |  \- node.py
|  |- rendering/
|  |  |- __init__.py
|  |  |- consist_layout.py
|  |  |- game_renderer.py
|  |  |- interpolation.py
|  |  |- layout.py
|  |  |- network_renderer.py
|  |  |- path_handle_renderer.py
|  |  \- turnaround.py
|  |- rl/
|  |  |- __init__.py
|  |  |- artifacts.py
|  |  |- dependencies.py
|  |  |- demonstrator.py
|  |  |- evaluation.py
|  |  |- history.py
|  |  |- manifest.py
|  |  |- manifest_schema.py
|  |  |- model.py
|  |  |- player_env.py
|  |  |- policy.py
|  |  |- privileged_oracle.py
|  |  |- provenance.py
|  |  |- protocol.py
|  |  |- profile_supervisor.py
|  |  |- profile_validation.py
|  |  |- resource_profile.py
|  |  |- temporal_history.py
|  |  |- windows_api.py
|  |  |- windows_resources.py
|  |  \- training.py
|  \- ui/
|     |- button.py
|     |- carriage_button.py
|     |- fleet_button.py
|     |- menu_screens.py
|     |- path_button.py
|     |- speed_button.py
|     \- viewport.py
|- test/
|  |- __init__.py
|  |- civ-engine-guard.test.mjs
|  |- civ-engine-pin.test.mjs
|  |- civ-engine-provenance-immutability.test.mjs
|  |- civ-engine-provenance.test.mjs
|  |- civ-engine-setup-contract.test.mjs
|  |- civ-engine-setup-build.test.mjs
|  |- civ-engine-setup-clone-isolation.test.mjs
|  |- civ-engine-setup-content-auth.test.mjs
|  |- civ-engine-setup-fixtures.mjs
|  |- civ-engine-setup-git-fixtures.mjs
|  |- civ-engine-setup-git-safety.test.mjs
|  |- civ-engine-setup-lease.test.mjs
|  |- civ-engine-setup-operations.test.mjs
|  |- civ-engine-setup-promotion-cleanup.test.mjs
|  |- civ-engine-setup-promotion.test.mjs
|  |- civ-engine-setup-process.test.mjs
|  |- civ-engine-setup-safety.test.mjs
|  |- gm06c-checkpoint-replay.test.mjs
|  |- gm06c-historical-compatibility.test.mjs
|  |- playtest-recursive.test.mjs
|  |- playtest-verify.test.mjs
|  |- recursive-ledger.test.mjs
|  |- recursive-pass.test.mjs
|  |- recursive-args.test.mjs
|  |- recursive-fixtures.mjs
|  |- source-provenance-fixtures.mjs
|  |- source-provenance-content.test.mjs
|  |- source-provenance-git-safety.test.mjs
|  |- source-provenance.test.mjs
|  |- input_coordinator_direct_support.py
|  |- gm06c_consist_test_support.py
|  |- gm06c_render_state_support.py
|  |- gm06c_simulation_ui_support.py
|  |- mediator_test_support.py
|  |- passenger_flow_direct_support.py
|  |- path_lifecycle_direct_support.py
|  |- path_lifecycle_test_support.py
|  |- route_planner_test_support.py
|  |- test_agent_play.py
|  |- test_agent_play_threshold.py
|  |- test_coverage_utils.py
|  |- test_env.py
|  |- test_gameplay.py
|  |- test_game_clock.py
|  |- test_game_renderer.py
|  |- test_geometry.py
|  |- test_graph.py
|  |- test_headless_render.py
|  |- test_input_coordinator.py
|  |- test_input_coordinator_edge_contract.py
|  |- test_main.py
|  |- test_mediator_input_contract.py
|  |- test_mediator_interaction.py
|  |- test_mediator_passenger_flow.py
|  |- test_mediator_passenger_flow_effect_contract.py
|  |- test_mediator_passenger_flow_facade_contract.py
|  |- test_mediator_path_contract.py
|  |- test_mediator_path_failure_contract.py
|  |- test_mediator_paths.py
|  |- test_mediator_progression.py
|  |- test_mediator_route_contract.py
|  |- test_mediator_route_observability.py
|  |- test_mediator_routing.py
|  |- test_mediator_simulation.py
|  |- test_network_progression.py
|  |- test_overdue_threshold.py
|  |- test_path.py
|  |- test_path_lifecycle.py
|  |- test_passenger_flow.py
|  |- test_gm05a_api_replay.py
|  |- test_gm05a_metro_continuity.py
|  |- test_gm05a_passenger_transitions.py
|  |- test_gm05a_rollback.py
|  |- test_gm05a_transaction_edges.py
|  |- test_gm05b_button_feedback.py
|  |- test_gm05b_mouse_redraw.py
|  |- test_gm05b_pixel_equivalence.py
|  |- test_gm05b_preview_rendering.py
|  |- test_gm05b_render_continuity.py
|  |- test_gm05b_state_equivalence.py
|  |- test_gm05c_handle_input.py
|  |- test_gm05c_handle_rendering.py
|  |- test_gm05c_pixel_equivalence.py
|  |- test_gm05c_state_equivalence.py
|  |- test_gm06c_carriage_controls.py
|  |- test_gm06c_carriage_fault_callbacks.py
|  |- test_gm06c_carriage_inventory.py
|  |- test_gm06c_carriage_lifecycle.py
|  |- test_gm06c_carriage_lifecycle_adversarial.py
|  |- test_gm06c_carriage_pixel_states.py
|  |- test_gm06c_carriage_pixels.py
|  |- test_gm06c_carriage_reconciliation_postconditions.py
|  |- test_gm06c_carriage_rendering.py
|  |- test_gm06c_carriage_rendering_integration.py
|  |- test_gm06c_carriage_selection_purity.py
|  |- test_gm06c_carriage_transaction_seams.py
|  |- test_gm06c_carriage_transactions.py
|  |- test_gm06c_checkpoint_contract.py
|  |- test_gm06c_checkpoint_validation.py
|  |- test_gm06c_consist_layout.py
|  |- test_gm06c_consist_turnaround_clearance.py
|  |- test_gm06c_consist_turnaround_hairpin.py
|  |- test_gm06c_consist_turnaround_rebase.py
|  |- test_gm06c_consist_turnaround_solver.py
|  |- test_gm06c_control_boundaries.py
|  |- test_gm06c_historical_compatibility.py
|  |- test_gm06c_replay_contract.py
|  |- test_gm06c_replay_fresh_process.py
|  |- test_gm06c_replay_preflight.py
|  |- test_gm06c_station_service.py
|  |- test_gm06c_station_service_integration.py
|  |- test_gm06d_cancel_unassignment.py
|  |- test_gm06d_line_removal.py
|  |- test_gm06d_occupied_return.py
|  |- test_gm06d_reconcile.py
|  |- test_gm07b_load_reconstruction.py
|  |- test_gm07b_save_determinism.py
|  |- test_gm07b_save_roundtrip.py
|  |- test_gm07b_save_schema.py
|  |- test_player_env.py
|  |- test_path_handles.py
|  |- test_path_redraw.py
|  |- test_recursive_checkpoint.py
|  |- test_recursive_oracles.py
|  |- test_recursive_playtest.py
|  |- test_recursive_threshold_schema.py
|  |- test_render_layout.py
|  |- test_render_purity.py
|  |- test_rl_artifacts.py
|  |- test_rl_cli.py
|  |- test_rl_demonstrator.py
|  |- test_rl_evaluation.py
|  |- test_rl_history.py
|  |- test_rl_history_cli.py
|  |- test_rl_history_integration.py
|  |- test_rl_legacy_compat.py
|  |- test_rl_manifest.py
|  |- test_rl_protocol.py
|  |- test_rl_resource_profile.py
|  |- test_rl_resource_profile_cli.py
|  |- test_rl_resource_profile_integration.py
|  |- test_rl_temporal_history.py
|  |- test_rl_training.py
|  |- test_rl_windows_api.py
|  |- test_rl_windows_resources.py
|  |- test_route_planner_iterators.py
|  |- test_route_planner_queries.py
|  |- test_route_planner_resolution_order.py
|  |- test_route_planner_selection.py
|  |- test_simulation_context.py
|  |- test_station.py
|  \- test_viewport.py
|- .gitignore
|- .pre-commit-config.yaml
|- AGENTS.md
|- ARCHITECTURE.md
|- CLAUDE.md
|- environment.yml
|- GAME_RULES.md
|- package-lock.json
|- package.json
|- PROGRESS.md
|- pyproject.toml
|- README.md
|- requirements-locked.txt
|- requirements-rl-locked.txt
|- requirements-rl.txt
\- requirements.txt

## Runtime boundaries

- `src/env.py` remains the public Gym-like drive surface over `Mediator`; its default reward is the delta in lifetime passenger `deliveries`, while explicit `line_credits_delta` mode reconstructs the legacy spendable-credit reward. Structured observations name both values, retain `score` as a line-credit compatibility alias, expose queue state and derived capacity on each assigned Metro, flatten attached Carriages in global-Metro then attachment order, and expose labeled locomotive plus carriage total/assigned/available counts without changing entity arrays. `Mediator.available_locomotives` and `Mediator.available_carriages` are read-only late-derived clamped differences over canonical global ownership; queued locomotives remain assigned until detachment. `Mediator.overdue_passenger_threshold` is the canonical overload field with repository default `2`; the writable `max_waiting_passengers` compatibility property addresses the same value. Ordinary `MiniMetroEnv.step` uses explicit fleet/carriage actions, while one shared legacy transition adapter reconstructs pre-GM-06b create-and-auto-assign semantics for validated historical recursive and agent evidence before advancing the original tick.
- `src/simulation_context.py` gives every `Mediator` independent Python and NumPy random streams. Interactive, structured, and pixel environments share the same gameplay code without sharing host-global RNG state, so gameplay mechanics, normalized checkpoints, array views, and pixels are reproducible when same-process or spawned environments are interleaved. Opaque shortuuid entity IDs remain session-unique and are intentionally excluded from deterministic checkpoint comparison.
- `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
- `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
- `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
- `src/passenger_capacity.py` owns the pure next-executable station-service oracle, identity-aware cache reconciliation with destination, executable transfer, then boarding priority, and the queued-return drain that force-alights exitless riders in one holder-order batch only when that oracle is quiet, leaving the service cache untouched. `src/passenger_flow.py` owns spawning, tick coordination, stop/exchange, delivery, waiting/game-over, scoped replanning, and proposal application; it executes one service identity per 500-millisecond interval, recomputes after every effect, preserves residual large-step progress, and creates no dwell interval for blocked work. Each call receives the current structural `PassengerFlowHost`; `Mediator` retains the public signatures, canonical collections, RNG, clocks, progression, router, factories, hooks, and identity-bound cache.
- `src/input_coordinator.py` owns path-button UI, layout, compatibility-render, mouse/keyboard, pause/speed, structured-action, and transient route-edit coordination as a dependency-light stateless component; `src/fleet_input.py` owns strict path index/id locomotive and carriage action selection plus release dispatch through the same public facade methods. `src/ui/fleet_button.py` and `src/ui/carriage_button.py` bind four controls only to stable path-button slots and resolve the live path at use time. Layout validation runs before mutation and reserves a quantization-safe bottom control band. `src/input_coordinator_host.py` holds only its structural facade typing contract. Assigned-button redraws remain immutable `src/path_redraw.py` values, while `src/path_handle_input.py` owns two-phase selection/gesture cleanup, `src/path_handles.py` owns weak idle selection plus immutable strong active edits, and `src/path_handle_geometry.py` builds collision-resolved descriptors shared by input and rendering. `Mediator` retains canonical UI, renderer, progression, topology, fleet, clock, and input state; false-to-true game over clears active pointer/edit references at the passenger-flow facade boundary.
- `scripts/verify_path_lifecycle_differential.py` materializes an exact committed baseline through `git archive`, runs baseline and candidate lifecycle scenarios in isolated bytecode-disabled child processes, guards each source tree against drift, and emits one canonical seven-action/nine-record equality artifact plus its digest summary without checking out or mutating either source tree.
- `scripts/verify_passenger_flow_differential.py` and its dependency-light support module apply the same non-mutating archived-baseline discipline to seeded spawning, pause/speed/waiting behavior, three fresh graph phases, metro delivery-transfer-boarding order, lazy arrival/route/fallback proposal effects, live-list mutation, and callable finalization timing. Exact-path `.gitattributes` rules keep the canonical artifact and summary LF-stable across Windows `core.autocrlf=true` checkouts so byte-level `--expected` replay remains portable.
- `scripts/verify_input_coordinator_differential.py` and its three split case/support modules guard the GM-03f input-coordinator extraction against its archived pre-extraction GM-03e baseline (`7ff9d9c`) in isolated bytecode-disabled children, assert source origins and pre/post runtime/verifier hashes, freeze nonzero case/record/event cardinalities, and cover hit-test, mouse/keyboard, purchase, pause/speed, and structured-action order. The layout/render case was retired at scenario version `v2` because GM-06c's pre-mutation `validate_resource_control_layout` reserved-band check, which the frozen baseline predates, makes that case's small-surface `prepare_layout` probes no longer comparable across the baseline boundary. Exact-path LF attributes plus external-output `core.autocrlf=true` replay make the canonical artifact byte-portable.
- `src/game_clock.py` owns the bounded deterministic `17, 17, 16` millisecond cadence, while `src/game_session.py` provides the shared player-event and fixed-update driver. The pygame window handles input before updates and uses one `Clock.tick(60)` pacing authority.
- `src/app_controller.py` owns the human entry path's explicit screen-state machine (`TITLE`, `PLAYING`, `PAUSE_MENU`, `GAME_OVER`): it consumes already-converted virtual-coordinate events, decides which reach `GameSession.dispatch`, absorbs the historical loop-inline game-over branch, and owns the one shared reconstruction path through the construction callable `main.run_game` supplies, so the controller never constructs the triple or touches the display and headless/programmatic entries (`env.py`, `rl/player_env.py`, `recursive_playtest.py`, `agent_play.py`) never meet it. `src/ui/menu_screens.py` provides the deterministic title/pause-menu layouts (exposed hit-test rects, now the three-button title stack with a `continue` slot) and byte-stable draw functions the loop paints above or instead of the gameplay frame; `draw_title_screen(surface, continue_available=...)` paints Continue only when available and `draw_notice` renders the load-failure banner. `Mediator` keeps pause ownership behind the retained `is_paused` bool facade over an internal per-instance lazily created pause-reason store (`user`, `menu`): the property setter, `set_paused`, structured `pause`/`resume`, speed actions, and the Space toggle touch only the `user` reason, while `hold_pause_reason`/`release_pause_reason` are the controller-only `menu` entry points, so a menu hold can never be cleared by gameplay input and reasons stay process-local runtime state outside checkpoints and observations. GM-07c wires GM-07b persistence into this shell only: `AppController` takes optional inert `build_from`/`autosave` seams and, per D-027, autosaves on pause-menu entry and Exit to Title (before releasing the menu hold), deletes the autosave at the `PLAYING`->`GAME_OVER` promotion and the game-over exits, and resumes a proven-loadable save via title Continue while surfacing a `notice` on load failure; `main.run_game` supplies that seam bound to the single `saves/autosave.json` slot behind a patchable module-level `AUTOSAVE_PATH` and applies the state-gated window-close save/delete, so autosave and Continue live only in `main` plus `app_controller` and no headless, agent, recursive, or RL surface imports the save modules. GM-07d adds a second optional inert seam beside it (D-028): `AppController` takes a `highscores` recorder that it invokes exactly once at the `PLAYING`->`GAME_OVER` promotion — reading `mediator.deliveries` only when the seam is present, so a seam-less controller reads nothing — and stores the result in public `last_highscore_result`; `main.run_game` binds the seam and the patchable `HIGHSCORES_PATH`/`record_highscore` to `src/highscores.py`, applies the same window-close game-over record (mutually exclusive with the promotion), and draws the best indicator with `menu_screens.draw_best_indicator` after the renderer's game-over frame so the near-ceiling `game_renderer` stays untouched. GM-07e makes that promotion frame-deterministic: the block is a public idempotent `AppController.reconcile_game_over()` (a no-op unless `PLAYING` and game over) that `handle_event` calls at its top and `main.run_game` calls once per frame after `session.advance` (re-reading the render state), so a tick-driven game over records, deletes the autosave, and shows the indicator the frame it ends independent of any incidental event; the state-gated window-close record stays mutually exclusive, now firing only for a game over still un-promoted at the QUIT.
- `src/entity/path.py` owns logical centerline segments used by metro movement. `src/rendering/layout.py` derives immutable, symmetric visual lanes without rebuilding or re-identifying those simulation segments.
- `src/rendering/network_renderer.py` owns separate bounded antialiased caches for the live network and one immutable selected-line preview, including arbitrary-slot temporary insertion, while sharing centered-lane geometry and the halo/color rasterizer. The cache-free `src/rendering/path_handle_renderer.py` draws primitive leader, marker, hit-envelope, and non-erasing removal feedback; `src/rendering/game_renderer.py` places leaders below entities, markers above stations/metros and below controls, projects endpoint-removal feedback onto the selected production lane, slices passengers locomotive-first across ordered bodies, outlines an entire queued consist, and renders available locomotives/carriages as the third/fourth HUD lines. The config-owned `(0, 0, 840, 250)` HUD exclusion keeps every route-handle descriptor and registered-profile action round trip outside all four lines. `src/rendering/consist_layout.py` samples route arclength with loop wrapping and terminal extrapolation from coherent endpoint poses. `src/rendering/interpolation.py` tracks exact live segment/station identity and rebase-safe previous/current snapshots, while `src/rendering/turnaround.py` supplies a continuous body-clearance-constrained terminal reversal for folded consists; ambiguous stale topology falls back to the live pose. Fonts and surfaces are renderer-owned and lazy so state-only and headless sessions do not require a display.
- `Mediator.prepare_layout(width, height)` prepares all player hitboxes before input. Rendering consumes those prepared rectangles; drawing primitives never establish or move hitboxes.
- `src/rl/protocol.py` is the dependency-free, fingerprinted player contract: registered pixel profiles, low-level `MultiDiscrete` action semantics, exact coordinate mapping, cursor pixels, reward modes, fixed ticks, and episode horizon. `src/rl/player_env.py` implements that contract with Gymnasium over the same `GameSession`, player event converter, and `GameRenderer` as the window.
- `PlayerPixelEnv` exposes live game state only as pixels. Its implementation reads canonical deliveries and line credits, while terminal-metrics v1 deliberately retains the serialized `display_score` key for old manifests. Terminal episode metrics are emitted after the final action; `src/rl/privileged_oracle.py` is an explicitly separate validation/curriculum surface and adds carriage-control positions/counts only for tests and demonstration. `src/rl/demonstrator.py` uses that oracle to create a route, assign a locomotive, attach one carriage through real controls, and reach a positive delivery; neither privileged surface is passed to a learning policy, and the PlayerPixel info/protocol remains unchanged.
- `src/rl/dependencies.py` owns lazy imports for the optional RL stack. `src/rl/policy.py` owns recurrent/feed-forward hyperparameter contracts plus model construction and loading; fresh runs use SB3-Contrib RecurrentPPO, recurrent minibatches of 64, `src/rl/model.py`'s bounded adaptive-pooling `MiniMetroCNN`, and separate one-layer, 256-unit actor and critic LSTMs, while feed-forward Stable-Baselines3 PPO remains an explicit ablation. `src/rl/history.py` owns dependency-light immutable temporal descriptors and fingerprints plus the single profiled default factory for exact offsets `[128, 64, 7, 6, 5, 4, 3, 2, 1, 0]`; `src/rl/temporal_history.py` owns the optional-dependency bounded vector ring, terminal-copy, and fail-closed reset lifecycle. `src/rl/training.py` owns spawn-safe `base -> VecMonitor -> VecTemporalHistory` construction, default-factory consumption, environment/trainer source hashing (including both dependency lockfiles and history/manifest/temporal modules), and checkpoint callbacks while retaining `DEFAULT_FRAME_STACK = 8` and the former public training imports for explicit contiguous/PPO compatibility. `src/rl/evaluation.py` carries recurrent state across decisions and resets it at episode boundaries. `scripts/train_rl.py` resolves fresh recurrent omission to the promoted ten-frame descriptor, fresh explicit PPO omission to contiguous eight, `--frame-stack` to an explicit contiguous control, and reviewed `--history-layout` names to one descriptor shared by train/eval/persistence; resume and `scripts/evaluate_rl.py` reconstruct only the authenticated saved descriptor. Manifests bind algorithm and exact history identity across resume/evaluation, and evaluation separates final game-over totals from right-censored horizon totals. Core installs include Gymnasium; `requirements-rl.txt` adds Stable-Baselines3, SB3-Contrib, PyTorch transitively, and TensorBoard, while the universal hashed locks resolve platform-specific wheels reproducibly.
- `src/rl/resource_profile.py` owns dependency-light candidate, storage, MAC, cyclic-order, and promotion-gate contracts; `src/rl/profile_validation.py` independently recomputes the exact task/trainer/history/tensor/rate contract before a worker can count as valid. `src/rl/windows_api.py` isolates the pinned `ctypes` Toolhelp32/PSAPI ABI, while `src/rl/windows_resources.py` owns retained process identities, descendant discovery, full-tree current-working-set samples, system commit/physical metadata, cadence failures, and scoped cleanup. `src/rl/profile_supervisor.py` owns pre/post clean-source attestation, bounded handshake and log draining, launcher/worker supervision, raw sample hashing, and bounded summary metadata. The stdlib-only top of `scripts/profile_rl_history_worker.py` blocks at a pre-import handshake; after release it constructs the real temporal wrapper and RecurrentPPO, drives two explicit production-horizon collect/train iterations, and measures actual padded recurrent batches. `scripts/profile_rl_history.py` counterbalances fresh workers and applies the preregistered engineering-safety gates. Raw profile evidence is ignored under `output/`; compact committed evidence records its digests when GM-02d2 runs.
- `src/rl/artifacts.py` atomically writes versioned artifact indexes, hashes and parses one exact authenticated index snapshot, and captures one exact model byte sequence for SB3 rather than reopening the verified path. Training writes a zero-step recovery model/manifest before learning, refreshes provenance after periodic checkpoints, and uses unique index files so interruption cannot invalidate the previous recovery pair.
- `src/rl/provenance.py` captures immutable runtime package/Python metadata, including Shapely and shortuuid because they affect player transitions and identity-bearing state, plus Git revision/dirty paths. `src/rl/manifest_schema.py` owns the immutable v1/v2 record and strict JSON key migration; `src/rl/manifest.py` owns atomic I/O and compatibility validation. Manifest v2 records the descriptor plus an independently recomputed `historyFingerprint`, while genuine v1 bytes normalize their positive `frameStack` to contiguous offsets and reserialize without v2 keys. Fresh, resumed, and evaluated environments now consume that exact descriptor through the temporal ring; an explicit equal-channel but semantically different request is rejected by history fingerprint before artifact access, and SB3 separately rejects observation-shape mismatches before learning or evaluation. Evaluation reconstructs the manifest-declared task, defaults to the saved evaluation seed, and refuses silent protocol, task, history, content, trainer, runtime, or model-byte drift; every supported override is explicit and tagged.
- `src/agent_play.py` writes v5 playthrough records with explicit per-step/final deliveries, line credits, reward/threshold identity, and exact locomotive plus carriage action contracts; persisted v4/v5 fleet actions and v5 carriage actions are replay-safe and index-only. Its legacy return and `score`/`final_score` fields continue to mean line credits. Schema-less/v1 and literal v2 records reconstruct historical threshold `1`, v3 validates its threshold, v1-v3 create operations use the shared legacy assignment adapter, v4 uses explicit locomotive transitions, and v1-v4 reject carriage actions before stepping.
- `src/recursive_contract.py` owns strict immutable v1-v5 scenario and recorded-input validation plus reward/threshold/fleet/carriage reconstruction. V1 reconstructs `line_credits_delta` and threshold `1`; v2 preserves `deliveries` and threshold `1`; v3 requires deliveries plus a positive non-boolean threshold; v4 requires the locomotive contract and index-only fleet actions; v5 additionally requires the carriage contract and index-only carriage actions. `src/recursive_playtest.py` executes every ordered operation and writes strict inputs, transcript rows, findings, and result. Historical v1-v3 create operations use the legacy adapter, v4/v5 use ordinary explicit transitions, and scenario versions map v1 to checkpoint v1, v2/v3 to checkpoint v2, v4 to checkpoint v3, and v5 to checkpoint v4.
- `src/save_schema.py` owns the versioned save-document contract (v1 constants, strict fail-closed `validate_save`, pinned ASCII `canonical_save_bytes`) with per-record and reference validation split into `src/save_schema_records.py`; `src/save_game.py` owns pure attribute-only serialization plus the save-local atomic writer, and `src/save_load.py` owns the strict JSON-to-`Mediator` loader (`deserialize_game`/`load_game`, re-exported through `save_game`). Unlike the UUID-free checkpoint family, save documents deliberately retain real entity ID strings so pre-save path IDs stay valid as post-load structured-action selectors while station/metro/carriage/passenger IDs remain stable observation/reference identity; the checkpoint therefore remains a one-way verifier and state-equality oracle — the save modules reuse only its safe value coercion, and no checkpoint or runtime surface (`env.py`, `agent_play.py`, `recursive_playtest.py`, `recursive_checkpoint.py`, `src/rl/`) imports the save modules. Loads rebuild derived structure (segments, button assignment, metro shape color) instead of trusting persisted copies, but each metro's bound station-service action persists as a nullable `serviceAction` record and restores VERBATIM — never re-derived at load — because a cache that disagrees with the re-derivable action at the save boundary is real reachable game state (a later metro can consume the bound passenger inside the same tick) whose next-tick reconcile semantics must replay exactly.
- `src/highscores.py` (GM-07d, D-028) owns the persistent high-score leaderboard, reusing `save_schema.canonical_save_bytes` and the scalar validators plus its own copy of the save-local atomic writer (`main` owns the `SAVE_RULES_VERSION` identity) — so it joins the save-module isolation set but imports no gameplay. The document is a strict versioned `{schemaVersion, stateContract, entries}` shape whose entries carry a `map`/`rulesVersion`/`deliveries` triple; `validate_highscores` checks exact keys before field access and rejects forward versions, bad types, and non-ASCII string content, `record_score` requires an explicit map/rulesVersion and validates its inputs, then returns a NEW board (pure) with the score inserted, all entries stored in the canonical map-asc/rulesVersion-asc/deliveries-desc order with stable tie-breaking and the recorded key capped at ten (other keys are never dropped), and a `RecordResult` carrying the new entry's rank and best flag. Unlike `load_game`, `load_highscores` is START-EMPTY tolerant: any failure — missing, non-ASCII, malformed, duplicate-key, forward-version, or pathologically nested (RecursionError) — yields the empty board and never raises, because a cosmetic leaderboard must never block play; `save_highscores` validates the board before writing and still RAISES on failure, and the best-effort swallow lives at `main`'s single patchable `record_highscore` recorder that both game-over surfaces funnel through.

- `src/recursive_checkpoint.py` converts observations and latent simulation state into UUID-free canonical JSON; `src/recursive_checkpoint_schema.py` owns version validation/normalization and `src/recursive_checkpoint_carriages.py` owns strict composition/topology correspondence so every module remains below 500 lines. Checkpoint v4 records exact locomotive/carriage inventory, queue booleans, derived capacities, ordered attachment references, and the exhaustive global-plus-path motion/owner bijection without entity UUIDs. Generation validates the live ownership graph, exact entity types, service cache, capacity equations, and caller observation before serialization. Genuine v1-v3 generation rejects any forward carriage surface; normalization deep-copies and synthesizes only historically valid missing state while preserving frozen bytes/projections. Checkpoints also cover reward identity, topology, passengers/plans, progression/unlocks, spawning, dwell/service state, and Python/NumPy RNG state.
- `src/recursive_oracles.py` checks reference integrity and non-finite values; `src/recursive_playtest.py` combines those checks with action-result, selected-contract reward, rejected-action, pause, terminal-state, topology, and transcript-cardinality oracles. Findings are born unverified and carry a stable class in `data.class`.

## Recursive pass data flow

`scripts/node-startup-contract.mjs` owns the shared post-start assertion used by the actual setup and guard mains: `NODE_OPTIONS` must be unset or empty and `process.execArgv` must be empty before either entry point performs its own work. The tracked package scripts and `.npmrc`, selected top-level npm and Node executables, and their pre-start environment/configuration are therefore a trusted bootstrap boundary. Node applies environment and CLI startup options before loading these modules, so this assertion can stop later setup/guard effects but cannot undo a preload that already ran; caller-selected bootstrap overrides outside the boundary are not attested.

Setup is an explicit boundary before recursive execution once that clean startup assertion passes. `scripts/civ-engine-setup.mjs` accepts only setup, strict `--verify-only`, or the recursive canary's `--verify-only --allow-dirty` mode; setup takes an exclusive repository-local lock and creates an ownership-marked transaction, while standalone verification is read-only and refuses any active lock. The same module exports an opaque verification lease that takes that exclusive lock, ownership-checks it immediately before and after read-only verification, and releases it only through token/identity-safe setup operations. `scripts/civ-engine-setup-git-config.mjs` owns the strict pin-local Git-config parser, and `scripts/civ-engine-setup-safety.mjs` classifies the missing/exact/suspicious pin and exact/repairable/shadowed root slot, audits physical Git metadata before sanitized read-only Git commands, permits only recursively contained generated-tree links, rejects external reparse escapes, and deletes transactions and locks only after their applicable path, marker, token, and filesystem-identity checks prove ownership. `scripts/civ-engine-setup-clone.mjs` performs the descriptor-fixed clone inside the owned transaction with controlled Git home/temp, an empty template, repository discovery ceiling, and metadata audit before detached checkout. `scripts/civ-engine-setup-content.mjs` authenticates every physical non-generated working-tree file to its exact detached-`HEAD` blob identity modulo LF/CRLF normalization allowed only by the independently authenticated repository-wide `* text=auto` policy before installation or direct build, rejecting index concealment, noncanonical attributes, pin-local npm config, active info-exclude patterns, unsupported entries, missing content, and unexpected files while separately auditing ignored generated trees. `scripts/civ-engine-setup-process.mjs` launches Git without a shell, validates the npm launcher and CLI within the active Node distribution on both Windows and POSIX, and always launches the physical `npm-cli.js` through exact `process.execPath`; ordinary read-only provenance uses the OS null device for HOME, USERPROFILE, global config, and hooks, disables system config and attributes, and drops inherited HOME/XDG/config controls, while setup Git receives only its authenticated transaction home. Every setup child receives a small scrubbed allowlisted environment that disables ambient Git redirects and optional locks, removes inherited Node/npm behavior controls, and supplies controlled npm configuration and temporary directories. This child environment begins only after the trusted setup bootstrap and does not sanitize the already-started top-level process. `scripts/civ-engine-setup-build.mjs` similarly executes only the physical pin-local TypeScript CLI through `process.execPath`, never an npm lifecycle or caller `PATH`. `scripts/civ-engine-setup-root-contract.mjs` authenticates the complete root package/lock graph through the descriptor-pinned canonical parsed-lock digest and exact `install-links=false` plus `loglevel=silent` npm configuration before root linking. `scripts/civ-engine-setup-promotion.mjs` atomically claims a still-missing final pin directory, records its physical identity and token in the owned transaction, and recursively publishes authenticated directories, files, and contained links only through exclusive `mkdir`, `COPYFILE_EXCL`, and remapped symlink primitives. It compares complete source/destination bytes, modes, types, and link targets before success, performs no shared-inode hard linking, rename, rollback, or deletion at the final path, and tags every post-claim failure so `scripts/civ-engine-setup.mjs` retains both the partial pin and its matching transaction while releasing only the owned setup lock. The setup orchestrator then reauthenticates the complete detached Git/content/generated-tree contract at the final path before root linking; successful publication leaves an exact marker-free pin and the source transaction for ordinary ownership-checked cleanup. `scripts/civ-engine-setup-operations.mjs` delegates that no-clobber publication, rebuilds only ignored dependency and `dist/` output after source identity is authenticated, exclusively creates only a missing exact root symlink/junction below a physical container whose bigint device/inode identity is checked before and after atomic creation, refuses stale or foreign root entries without deleting them, revalidates the complete root contract after linking, and finishes with provenance verification without consulting or mutating a sibling checkout. An intervening slot winner is preserved; a path-level parent-container swap is detected after atomic creation with both containers and the link wherever creation landed retained for inspection. `scripts/source-provenance-git-safety.mjs` audits the root repository's physical local Git metadata and rejects command-bearing, redirecting, or status-cache-weakening config before source provenance invokes Git; `scripts/source-provenance-content.mjs` independently reconciles every relevant working byte snapshot against the authenticated `HEAD` blob OID with deterministic add/delete/rename evidence and safe LF/CRLF equivalence, while `scripts/source-provenance-engine-safety.mjs` authenticates the engine's fixed root attributes policy before every engine Git call.

After clean module startup, `scripts/civ-engine-guard.mjs` is the canonical Node-command body for `npm test`, `npm run playtest:verify`, and `npm run playtest:recursive`. The test command rejects every forwarded package-script argument before guard effects and always spawns exactly `node --test`, preventing those post-start arguments from becoming child Node CLI options or file operands; focused development tests invoke `node --test <files>` directly. The guard validates recursive arguments before its effects, acquires the exclusive verification lease, verifies provenance and recaptures lock ownership under that lease, spawns only the selected fixed script through the current Node executable with `shell: false`, and releases the lease after child completion or any later failure. The token lock coordinates cooperating setup/guard processes but remains advisory against out-of-band filesystem tampering during child execution because it is not continuously monitored. A primary verification/spawn error and lease-release error are preserved together with the primary as cause/code while the guard diagnostic remains categorical. `scripts/recursive-args.mjs` is the dependency-free parser shared with `scripts/playtest-recursive.mjs`, so only an option-position `--allow-dirty` selects canary verification; consumed values cannot, and tests/standalone verification stay strict when lifecycle prehooks alone are skipped under the trusted bootstrap.

1. `scripts/source-provenance.mjs` inventories relevant runtime source with per-file and tree SHA-256 digests, records relevant Git status, and enforces the clean-by-default policy. `scripts/civ-engine-pin.json` and its strict dependency-light loader define the credential-free repository, ignored repo-local checkout, package version, Git commit, and complete runtime-tree digest. `scripts/source-provenance-engine.mjs` resolves package metadata and the ESM runtime without executing them, proves both belong to the exact physical `/.civ-engine-pin/` checkout, and inventories its `package.json` plus `dist/`, including ignored build output. Both capture modules reject accessor-backed records and recursively freeze registered capture graphs before returning them, so later policy, serialization, and recapture comparisons operate on immutable evidence. `--allow-dirty` is an explicit canary/development escape hatch for attributable detached content, commit, version, digest, and status mismatches inside that root; remote, attachment, location, dependency-slot, runtime-identity, and availability failures are never overridable.
2. `scripts/playtest-recursive.mjs` captures and writes that provenance before driving, creates a unique append-only directory under `output/recursive/`, launches the Python driver with the checked-in deterministic fixture by default, and captures the drive logs and artifacts.
3. `scripts/playtest-verify.mjs` launches a fresh Python process against the recorded `inputs.json`, compares exact replayable input metadata, transcript results, canonical checkpoint vectors, and authored finding semantics, then writes verification evidence and strict replay-verified findings. Standalone verification attempts use unique subdirectories under `<run-id>/verification-attempts/`.
4. Before finalization, the driver recaptures both source trees and turns any mid-run drift into an attributable `source-changed` failure with final-state evidence. `scripts/recursive-pass.mjs` selects the highest-severity verified open finding, builds civ-engine run/pass manifests, and validates their repository-level completeness including source-state summaries. New manifests use `source-state-v2`; immutable `source-state-v1` rows from earlier harness revisions remain readable during reconciliation. `scripts/recursive-ledger.mjs` and `scripts/recursive-ledger-lock.mjs` own write-ahead paired persistence, atomic manifest creation, repair of an unterminated final JSONL fragment, token-checked heartbeat locks, dead-owner recovery, and one-pass intent reconciliation.
5. Each run keeps `run-manifest.json` and `pass-manifest.json`; aggregate run rows append to `output/recursive/ledger.jsonl` and pass rows append to `output/recursive/passes.jsonl`. Pending intents are deleted only after both rows are durably confirmed. Outcomes are `verified` or `run-failed` for run manifests and `no-fix-candidate`, `proposal-only`, or `run-failed` for pass manifests.

The post-bootstrap Node boundary depends on the retained ignored checkout at `/.civ-engine-pin/` through `file:.civ-engine-pin`; the exact root `.npmrc` fixes link semantics and keeps the standard canonical npm prelude silent, and `package-lock.json` records the same root and engine 2.2.0 inside the descriptor-digested install graph. Both Ubuntu and Windows CI use trusted clean runners, full-history credential-persistence-disabled root checkouts, Node 22, and canonical `npm run setup:civ-engine`; Ubuntu then runs the guarded Node contracts, a clean recursive pass, and the Python suite, while Windows performs an additional strict verify-only invocation before its RL tests and smoke runs. Setup obtains the descriptor commit, authenticates complete non-generated checkout identity against `HEAD` with only the authenticated `* text=auto` LF/CRLF normalization, installs its development graph through the Node-distribution npm CLI, builds directly through the pin-local TypeScript CLI, exclusively creates the missing root runtime link without root package extraction, and verifies path/version/commit/clean-status/runtime-digest provenance without importing engine code. The pass is scripted and proposal-only: no model provider, automatic source edit, apply arm, or auto-merge boundary is present.

## Recursive-loop tests

- `test/test_recursive_playtest.py` covers strict scenario/input validation, one transcript row per operation, and recorded-input replay; `test/test_recursive_threshold_schema.py` pins immutable v1/v2/v3 threshold reconstruction and checkpoint mapping plus the explicit v4/v5 fleet contracts; `test/test_recursive_checkpoint.py` covers UUID-free checkpoint construction, schema normalization, alias agreement, reward identity, fleet/queue state, and latent observability. The GM-06c checkpoint/replay/historical suites add exhaustive carriage ownership/type/capacity/service validation, direct legacy-forward rejection, immutable v1-v4 projections, nonempty v5 fresh-process redrive, and exact LF fixture bytes; the two Node GM-06c files independently bind v5 projection and historical compatibility.
- `test/test_recursive_oracles.py` covers cross-view topology and the remaining environment-contract oracle classes.
- `test/civ-engine-guard.test.mjs`, `test/recursive-args.test.mjs`, the setup build/clone/content/contract/Git-safety/lease/operations/process/promotion/promotion-cleanup/safety suites, and `test/source-provenance-git-safety.test.mjs` cover shared categorical startup-taint detection before setup/guard effects, the fixed post-start zero-argument full-test body, shared parser-aware strict/canary selection, categorical argument rejection without reflection, pre/post-verification ownership checks under asynchronous token mutation, child-lifetime lease ordering and concurrent-setup exclusion, combined primary/release failure preservation, exact setup sequencing, checkout-content authentication, isolated pre-checkout clone trust, root Git-config refusal, sanitized installation/build boundaries, trusted executable identity, exclusive lock and transaction ownership, no-destructive-operation final-path publication, missing/exact/suspicious pin handling, exact-slot repair versus nested/external slot refusal, pre-launch generated-tree revalidation, and preservation of external sentinels. The setup fixture modules provide hermetic repositories and detached checkouts without registering extra test entry points.
- `test/civ-engine-pin.test.mjs`, `test/civ-engine-provenance.test.mjs`, `test/civ-engine-provenance-immutability.test.mjs`, `test/source-provenance.test.mjs`, `test/recursive-ledger.test.mjs`, `test/playtest-verify.test.mjs`, `test/recursive-pass.test.mjs`, and `test/playtest-recursive.test.mjs` cover descriptor/package/lock/workflow parity, preservation of the 44-test pre-GM04 surface, physical package/runtime identity, recursively immutable fresh-capture integrity, local and engine inventory, ignored-runtime mismatch rejection, start/end recapture, token-safe concurrent/crash reconciliation, torn-tail repair, exact fresh-process verification, strict evidence promotion, manifest contracts, public verifier retries, and end-to-end success/failure outcomes. `test/source-provenance-fixtures.mjs` and `test/recursive-fixtures.mjs` supply shared hermetic repositories and strict manifest fixtures without registering extra test entry points.

## Mediator characterization tests

- `test/mediator_test_support.py` owns the shared per-test mediator fixture, pygame draw cleanup, interaction helper, and two-station network builder without matching unittest's default discovery pattern.
- Ten original mediator-facing discovered modules partition behavior by ownership: interaction/layout, routing decisions, route-facade contracts, route observability, path lifecycle, path-facade and failure contracts, simulation/spawning/game over, passenger/metro flow, and progression/purchases. They preserve the former monolithic suite's exact 57 test bodies while adding focused characterization for extracted boundaries. `test/test_network_progression.py` directly covers dependency-free progression policy and cached-state semantics; four direct route-planner modules cover dependency-free queries, selection, resolver and callable-lifetime timing, and lazy proposal iteration; `test/test_path_lifecycle.py` plus its two non-discovered support modules cover the stateless host boundary, transition ordering, rebinding, factory lifetime and failures, and import isolation. `test/test_passenger_flow.py` plus its non-discovered support module cover the dependency-light stateless host boundary directly; two additional facade/effect contract modules pin all 16 public signatures, late dependency resolution, partial failures, live iteration, graph freshness, and exact passenger-effect ordering. `test/test_input_coordinator.py`, `test/test_input_coordinator_edge_contract.py`, and their non-discovered support module directly cover the final dependency-light stateless boundary, while `test/test_mediator_input_contract.py` is replayable against both the archived baseline and candidate and freezes all 19 real facade signatures plus late dependencies, subclass precedence, collection replacement, partial effects, and Python bound-method evaluation order. The five GM-05a modules add 40 focused structured-action/replay, metro continuity, passenger transition, rollback, and adversarial transaction-edge methods for atomic path replacement. The seven GM-05b modules add 52 pure-draft, real-event, player-pixel, canonical-state, button-feedback, preview, and no-tick continuity methods. GM-05c adds 45 focused pure-handle, converted-input, rendering/cache, fast/fidelity pixel, canonical-state, and live letterbox methods. GM-06a adds 34 focused runtime/failure, observation/checkpoint, HUD/geometry, and actual fast/fidelity low-level pixel methods. GM-06b adds 73 focused Python methods plus four Node replay tests for assignment transactions, canonical geometry preflight, queued movement/settlement, gesture/render/Pixel parity, canonical-LF training-source preservation, checkpoint v3, and recursive/agent v4 compatibility. GM-06c adds 172 focused Python methods plus four new Node tests for carriage conservation, capacity-aware service, controls/pixels, consist geometry, checkpoint v4, recursive/agent v5, and frozen v1-v4 behavior. `InputCoordinator` is 498 lines, its structural host is 104, `GameRenderer` is 494, the three recursive checkpoint modules are 497/499/243, and the explicit `Mediator` facade is 757 lines; every other changed handwritten production file remains below 500 lines.

## Rendering tests

- `test/test_game_clock.py` covers fixed cadence, clamp/drop behavior, pause/terminal consumption, and interpolation observer ordering.
- `test/test_render_layout.py` covers centered lanes, reverse-pair geometry, corner/loop metro projection, antialiased pixels, and cache invalidation/bounds.
- `test/test_game_renderer.py` covers lazy resources, layer order, metro interpolation, cached button fonts, the four-value HUD, and prepared game-over controls.
- `test/test_render_purity.py` renders real software surfaces and proves repeatable RGBA bytes, complete render-facing state and canonical-checkpoint purity, cache reuse, and rendered-versus-never-rendered trajectory equivalence.
- `test/test_gm05b_preview_rendering.py` covers selected/invalid feedback, immutable preview/live parity, shared-lane ordering, overlay layering, deterministic clipped cache behavior, and render-only reference bounds; `test/test_gm05b_render_continuity.py` covers exact-segment freshness, retained-edge and padding rebasing, loop/reversal direction, safe live-pose fallback, next-step recovery, and old-segment release.
- `test/test_path_handles.py` and the four GM-05c modules cover weak/strong reference boundaries, deterministic collision relocation, loop and endpoint edit derivation, converted two-phase input, arbitrary-slot and removal rendering, cache-free byte stability, actual downscaled fast/fidelity observations, checkpoint/structured-array invisibility, and game-over cleanup; the three GM-06a modules bind every inventory transition and failure seam to runtime, structured observation, genuine checkpoint v1/v2 reconstruction, exact HUD fallback and geometry, and genuine low-level inventory glyphs. The GM-06b control/render/Pixel modules cover quantized locomotive hits, queue pixels, synthetic-padding avoidance, explicit player actions, and a real-coordinate positive-delivery demonstrator. The GM-06c controls/render/Pixel/consist modules cover the four-control band, enabled/disabled states, body/passenger slicing, whole-consist queue outlines, coherent route sampling, topology rebasing, feasibility-checked terminal radial expansion, and dense two/four/six/seven-body terminal-turn clearance through real `Path.move_metro` arrivals; `test/test_main.py` retains live letterbox mouse-up coverage.

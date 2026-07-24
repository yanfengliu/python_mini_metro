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
|  |  |- save-v1.json
|  |  \- save-v2-classic.json
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
|  |- audio.py
|  |- carriage_management.py
|  |- carriage_transaction_snapshot.py
|  |- config.py
|  |- crossings.py
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
|  |- maps.py
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
|  |- settings.py
|  |- simulation_context.py
|  |- travel_plan.py
|  |- tutorial.py
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
|  |  |- flexible_draw.py
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
- `src/maps.py` (GM-09a, D-032) owns the versioned map layer as DATA ONLY — importing solely `config` + `geometry.type` (never `pygame`/`entity`/`mediator`), so it stays import-safe for every headless/RL path with no cycle. An immutable frozen `MapDefinition` carries `map_id`/`map_definition_version` and the station-shape palette (`shape_types`/`unique_shape_types`/`unique_spawn_start_index`/`unique_spawn_chance`, coerced to tuples in `__post_init__`); `CLASSIC` captures today's config values; `resolve_map(map_id, version)` is a version-aware lookup that raises a clear named error rather than return the wrong map. `Mediator` takes an optional `map_definition` (default `CLASSIC`) and threads its palette ONE-WAY into `get_random_stations` (which gained keyword-only palette params defaulting via None-sentinel to the config globals, so every existing caller draws byte-identically). The abstraction is behavior-preserving — Classic reproduces pre-change station/color/RNG construction and a stepped trajectory byte-for-byte — and `save_game.serialize_game`'s fail-closed `_require_classic_map` guard permits only `classic@1` (or a `map_definition`-less Mediator) to serialize, adding no save bytes so `save-v1.json` stays frozen. Station counts stay global; the save-schema/high-score map fields (GM-09f) are deferred.
- GM-09b (D-034) adds the first alternate map — `RIVER` — plus terrain/station regions. `MapDefinition` gains additive, deeply-immutable `spawn_regions` (land rects) and `rivers` (obstacle bands to render), tuple-coerced + positive-area-validated in `__post_init__`; `RIVER` is a central vertical river splitting the map into two `station_size`-eroded banks, registered so `KNOWN_MAP_IDS == ("classic", "river")`. Region-aware spawning is STRICTLY ADDITIVE: `spawn_regions` threads keyword-only through `get_random_stations → get_random_station → get_station_spawn_position`, where `_sample_position` REJECTION-samples a candidate outside every region (bounded, named error on exhaustion) — the FALSY no-region fast path (`if not spawn_regions`) means the empty tuple CLASSIC passes returns the first draw, so CLASSIC's RNG stream and `save-v1.json` stay byte-identical (`get_random_position` is untouched). A new small `src/rendering/terrain_renderer.py` (`draw_terrain`) paints the river bands at the TOP of `GameRenderer.draw` (before the network), so the human loop, the RL pixel observation, and tests all see it; CLASSIC (empty `rivers`) paints nothing. `_require_classic_map` is hardened to STRUCTURAL equality against canonical `CLASSIC`, rejecting a forged classic-with-terrain. No `geometry.Polygon` (shapely/uuid/broken `contains`) — plain tuples + `pygame.draw.rect` + a pure point-in-rect test; `maps.py` stays import-safe. The crossing/tunnel mechanics that make the river a real obstacle are GM-09c.
- GM-09a2 (D-033) makes the RL task descriptor MAP-VERSIONED with strict legacy-byte-compatibility. `rl.protocol.TaskSpec` gains optional `map_id`/`map_definition_version` (appended last, default `None`); `task_descriptor` adds `mapId`/`mapDefinitionVersion`/`descriptorVersion:2` ONLY for a map-bound spec, so a map-absent descriptor stays byte-identical and keeps its exact legacy fingerprint (the presence of the keys IS the version signal). The training manifest gains an explicit v3 (`rl.manifest_schema`: `_V3_KEYS = _V2_KEYS | {mapId, mapDefinitionVersion}`); v1/v2 stay map-free and exact-key-valid, and `__post_init__` keeps the schema version and map keys in lockstep. `create_training_manifest` writes v3 only for a map-bound task; `task_spec_from_manifest` reconstructs the map identity (None for v1/v2 → legacy hash), and the spawn-safe `PlayerEnvThunk` carries it to subprocess workers. `scripts/train_rl.py` gains `--map` (fresh omitted → map-free v2; a resumed run INHERITS the map from its manifest, so a genuine pre-map run still resumes). The real pre-map manifest is committed sanitized at `scripts/fixtures/legacy-training-manifest-v1.json` so CI runs the legacy-hash regression. `maps.py` stays out of `TRAINING_SOURCE_PATHS` but is captured by `compute_content_fingerprint`'s `src/**` glob. The save-schema/high-score map fields remain deferred to GM-09f.
- GM-09c (D-035) makes the river a real obstacle via a finite tunnel budget. A new dependency-light `src/crossings.py` — importing ONLY `geometry.point`, reading duck-typed hosts by `getattr` — owns the pure geometry (`segment_crosses_band` Liang-Barsky slab returning the entry point, with a zero-length grazing touch deliberately NOT counted; `path_crossings` counts one entry per band on a path's CENTERLINE of consecutive `station.position` pairs plus the loop closure, where a 2-station loop's closure is skipped so it cannot double-charge) AND the single route-edit gate `within_tunnel_budget(host, stations, is_looped, *, exclude=)` shared by both edit paths. `MapDefinition` gains an additive `tunnel_budget: int | None` (validated non-negative-int-or-None in `__post_init__`); `RIVER` sets `3`, `CLASSIC` leaves `None` (unbounded). `Mediator` exposes `num_tunnels`, `consumed_tunnels`, and `available_tunnels` as three DERIVED properties — `num_tunnels` reads `map_definition.tunnel_budget`, `consumed_tunnels` sums `path_crossings` over every committed line, `available_tunnels` is `max(0, num_tunnels - consumed)` or `None` when unbounded. None is cached, so a swapped map stays consistent and a stale copy can never fail open, and removal/reroute refund for free with NO snapshot field (the `available_locomotives` pattern). The read-only gate `within_tunnel_budget` reads the budget and rivers from `map_definition` and counts the REAL resolved draft (`creating.stations`/`is_looped`), never a route predicted from raw indices — the construction dedups an explicit-closure `[X,Y,X]` to the 2-station loop `[X,Y]` and can loop-form on a repeated station, so a raw-index pre-check both false-rejects a valid loop and false-accepts a mid-repeat. It gates where the final draft is known, BEFORE any extend/loop mutation: `path_lifecycle.end_path_on_station` on release and `finish_path_creation` at the commit boundary (catching a direct `start/add/finish` bypass). An over-budget release adds no station and commits no crossing; the rejection is count-, path-, and RNG-inert. GM-09c left the shared `abort_path_creation`/`assign_paths_to_buttons` UNCHANGED (so CLASSIC, whose gates always pass, stayed byte-identical) — a re-review showed that folding a snap-blip rollback or a draft-skipping button pass into them broke CLASSIC's bytes and mis-owned a reclaimed-color blip — deferring the pre-existing transient-blip-on-abort and ghost-button-after-mid-draft-removal to a follow-up (`task_384488d0`), since landed: `abort_path_creation` now drops the draft's OWN transient blips (each recorded as it is painted and removed by last-recorded value, so a reclaimed color's surviving blip is kept) and detaches any button a mid-draft `remove_path` bound to the draft, leaving `assign_paths_to_buttons` untouched; committed-line and CLASSIC checkpoint bytes are unmoved (only a cancelled drag's own transient blips differ, and the button detach is checkpoint-invisible). `path_replacement.replace_path` calls it in preflight (excluding the rerouted line) before `build_candidate`. `env.observe` adds a `tunnels` block (`total`/`consumed`/`available`) as a SIBLING of `fleet`, never a fleet key, so the canonical checkpoint's exact fleet-key whitelist and every save fixture stay valid. `rendering/terrain_renderer.draw_crossings` paints a tunnel-portal marker at each crossing ON TOP of the network (lazy-importing `crossings` inside the function, as `network_renderer` does with `config`, so `src.rendering` stays importable during test discovery); CLASSIC (no rivers) draws nothing, so its frame stays byte-identical. `crossings.py` stays import-safe (no pygame/mediator/shapely). `path_replacement.py` is 501 lines — one over the soft guideline on a pre-existing ~500-line file, far under the 1000 hard ceiling.
- GM-09d (D-036) adds the SECOND alternate map, `DELTA`, with NO new machinery — it is a pure `MapDefinition` addition proving the GM-09b/GM-09c layer generalizes. Two vertical channels (`rivers` = 2 bands) split the play area into THREE `station_size`-eroded banks (`spawn_regions` = 3 rects), with `tunnel_budget=4`; a line spanning both channels consumes two tunnels, exercising the multi-band `path_crossings` count and the finite budget more than the single-river `RIVER`. Registered so `KNOWN_MAP_IDS == ("classic", "delta", "river")`. The addition is purely additive — the region-aware spawn (`_sample_position` accepts a candidate inside any of the three regions), the terrain/crossing renderers (loop over all bands), the derived tunnel count, and the fail-closed save guard all already handle N regions/rivers, so CLASSIC and RIVER stay byte-identical (the `test_gm09a_maps` fingerprints and `save-v1.json` are unmoved). The GM-09b exact-`KNOWN_MAP_IDS` test was loosened to membership so later maps do not break it.
- GM-09e (D-037) adds the THIRD alternate map, `LAKE`, again with NO new machinery, but exercising a generality dimension the RIVER/DELTA channels never did: a PARTIAL band. `LAKE.rivers` is a single BOUNDED rect (a central lake spanning no screen edge), so `crossings.segment_crosses_band` is tested on a rect bounded in both x and y — a line's centerline that passes through the lake counts one crossing, and a line routed AROUND it counts none. `spawn_regions` is a FRAME of four overlapping strips (top/bottom full-width, left/right full-height, each eroded from the lake by `station_size`) whose union is the whole screen minus the lake; the region-accept spawn (`_point_in_rects`, any-region) needs no change. Because the lake is bounded, a line can OFTEN be routed around it (a line bends only at stations, so a dry detour needs an intermediate station beside the lake) instead of tunnelling through — so `tunnel_budget=3` mostly caps shortcuts, but still limits TOTAL crossings and a station whose only routes cross the lake is gated until a tunnel is freed, as on the channels (a re-review corrected an over-claim that the lake "never gates connectivity"). GM-09e also promoted `crossings.segment_crosses_band` to STRICT-interior semantics: a segment collinear with a band EDGE now counts zero — reachable on LAKE (integer vertical edges with no x-erosion of the top/bottom banks), which supersedes GM-09c's deferral; RIVER/DELTA never place a centerline on an edge, so their counts are unmoved. `KNOWN_MAP_IDS == ("classic", "delta", "lake", "river")`; CLASSIC/RIVER/DELTA stay byte-identical.
- GM-09f (D-038) begins the map/save integration (SPLIT into save-schema / high-score / menu) with the SAVE-SCHEMA v2 map field. `save_schema` gains `SAVE_SCHEMA_VERSION_V2 = 2` (`SUPPORTED = {1, 2}`, current = 2) with two additive top-level keys `mapId`/`mapDefinitionVersion`; `validate_save` is TWO-PHASE (read + support-check `schemaVersion` with a named error BEFORE choosing the version-aware exact-key set `_TOP_LEVEL_KEYS_V1`/`_V2`, so a v1-doc-with-map-keys and a v2-doc-without both fail closed), and the v2 identity is scalar-validated (`_validate_map_identity`). `save_game.serialize_game` replaces `_require_classic_map` with a fail-closed pair: STRUCTURAL `map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`, since a v2 save records only the identity and rebuilds terrain from the registry on load) and `save_load._require_legal_map_state` (every station on the map's `spawn_regions`; `consumed_tunnels <= num_tunnels`) — the latter shared by serialize and post-load so a forged illegal state (a Classic state relabeled `river@1`) is refused both ways. `save_load.deserialize_game` reads the map identity for v2 / synthesizes `classic@1` for v1, resolves via `resolve_map` (fail-closed on unknown id / unsupported version), and threads `map_definition` into the `Mediator`; tunnel counts stay derived. The byte-frozen `scripts/fixtures/save-v1.json` is unchanged and still loads as Classic; the deterministic v1→v2 header-only upgrade is pinned by a new frozen `scripts/fixtures/save-v2-classic.json` (15485 bytes) that the idempotence + cross-process determinism tests target. `stateContract`/`rulesVersion` unchanged; the RL manifest and recursive checkpoint are separate schemas. The high-score `mapDefinitionVersion` and the in-game map menu follow as the next two sub-units (menu last, so it cannot feed an alternate map to the still-classic-hardcoded score recorder).
- GM-09f2 (D-039) is the second GM-09f sub-unit: the high-score leaderboard records the MAP identity. Both game-over surfaces now hand the recorder the LIVE mediator (the controller seam passes `self.mediator`, and `main.run_game`'s promotion closure drops its old `SimpleNamespace(deliveries=...)` wrapper), so `main.record_highscore` reads `mediator.map_definition.{map_id, map_definition_version}` (direct, fail-SAFE: a missing map records nothing rather than mislabelling — no `or classic`) instead of hardcoding `classic`. `highscores` bumps to schema **v2** keyed by the full `(map, mapDefinitionVersion, rulesVersion)` identity via one shared `_identity` helper (sort + cap + rank), with the `map` grammar tightened to the save's mapId. A legacy v1 board is NOT migrated — it starts empty — because its classic labels are not provably accurate. This lands BEFORE the in-game menu (GM-09f3) so the recorder is already map-aware when non-Classic maps become selectable; `highscores` stays gameplay-free (no `maps` import) and in the persistence isolation set.
- GM-09f3 (D-040) COMPLETES GM-09f with the in-game MAP MENU. `AppController` gains `current_map_id` (default `classic`), cycled by an appended title control `map` (`title_layout` appends the `"map"` key so the prior title rects stay byte-identical; `draw_title_screen` gains a `current_map_id` param and paints a `Map: {Name}` button; `main.run_game` threads `controller.current_map_id` into it). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]`: `main.run_game`'s `build_game(map_id)` resolves `maps.map_by_id(map_id)` into `Mediator(map_definition=…)` (every downstream layer was already map-aware, GM-09a–f2). NEW GAME / ENTER build `current_map_id`; RESTART (pause + game-over) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id` via `_restart_current_game` (so restarting a Continued River game gives River even when the picker sits on Lake); Continue installs the SAVED map and never consults the picker; the tutorial stays Classic. Only `main`+`app_controller`+`menu_screens` change; the headless/agent/recursive/RL entries construct `Mediator(map_definition=…)` directly and never meet the title picker.
- GM-10a (D-041) opens GM-10 with the simulation CALENDAR. `config.WEEK_LENGTH_STEPS` defines a "week" in sim steps; `Mediator.increment_time`, after the COMPLETE tick (post queued-return settlement), holds a new `"week"` pause reason when `mediator.week_calendar` is on, the tick crossed a new boundary, and the run is not game over. `"week"` joins `_PAUSE_REASONS` (frozen by the existing gate; never cleared by Space/speed); `week_index` is a `steps`-derived property and `resolve_week_boundary()` releases the pause. The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it, so RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, and frame-limited/headless runs never pause — the calendar branch is never taken off the human path, so no `env.py`/checkpoint/save change and no determinism risk. The human shell adds `AppScreen.OFFER`: `AppController.reconcile_week_boundary()` (per-frame AFTER `reconcile_game_over`, so a terminal tick wins; cancelling any armed gesture via the pinned letterbox-cancel before switching) promotes a pending boundary to a modal whose armed Continue (`menu_screens.offer_menu_layout`/`draw_offer_screen`) resolves the week; `main` renders it over the frozen frame, resolves-then-autosaves on a mid-offer window close, and consumes the offer frame's audio silently; `save_game._require_quiescent` blocks saving while a boundary is pending. Persistence + the RL observation/offer are deferred to GM-10h/GM-10b.
- GM-10b (D-042) adds the weekly OFFER GENERATOR. A new dependency-light `src/offers.py` (stdlib-only — `enum`/`dataclasses`/`random`, no pygame/mediator, so it is import-safe on every headless/RL path) owns the data model (`OfferKind`, frozen `Offer`, `describe`) and a PURE `generate_offers(rng, *, count, tunnels_bounded)` that draws `count` DISTINCT kinds via `rng.sample` from an explicitly-ordered pool — the four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map. `config.OFFERS_PER_WEEK` (2) sets the count. When `Mediator._maybe_hold_week_boundary` fires (same calendar/crossing/not-game-over gate as the hold), it stores `self.current_offers` from `generate_offers`; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel (byte-stable on repeat). The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr, cross-process stable) — a deliberate design choice (dual-plan-reviewed): reading the state consumes no gameplay draws (station spawns stay byte-identical) AND, because that gameplay RNG state is already restored exactly on Continue, the same week's offers reproduce byte-exact after save/load with NO new persisted state. So GM-10b adds ZERO save/checkpoint/observation bytes (the `rng` block, exact-key save validation, checkpoint schema, and every frozen fixture are untouched) and never runs off the human path. Applying a choice is GM-10c, per-kind effects GM-10d–g, and applied-offer/replay persistence GM-10h (which must not trail GM-10c). (Adding `offers.py` and editing the runtime `src` files rotates the LIVE RL content fingerprint — `compute_content_fingerprint` hashes all of `src/**` — so a pre-GM-10b manifest fails strict resume/eval by default; EXPECTED and correct for fresh runs, no frozen fixture is repinned since `EXPECTED_LF_TRAINING` pins only `TRAINING_SOURCE_PATHS`, which excludes these files.)
- GM-10c (D-043) makes the offers SELECTABLE. `menu_screens.offer_menu_layout(width, height, count)` now returns one button rect per offer (keys `offer_0..offer_{count-1}`); `draw_offer_screen` paints each offer as a button. `AppController._handle_offer` arms a button on mouse-down and, on a matching mouse-up (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to `Mediator._apply_offer(offer)` (a `match offer.kind` over `OfferKind`, raising a named `ValueError` on an unknown kind) then clears `current_offers` and releases the pause; `None` is a forced resolve with no choice (the `main.run_game` window-close path, unchanged). The per-kind arms are NO-OP stubs in GM-10c — choosing changes NO game state, so it is Continue-safe with ZERO new persisted bytes (the state-inertness is test-locked against the full `serialize_game` doc). The real effects are GM-10d–g: a NEW_LINE grant can flow through the already-persisted `purchased_num_paths` (Continue-safe standalone), while the LOCOMOTIVE/CARRIAGE grants hit `save_load._require_running_config` (which pins `numMetros`/`numCarriages` to config) and the TUNNEL grant needs a persisted bonus, so those must land with GM-10h.
- GM-10d (D-044) fills the FIRST per-kind offer effect: `OfferKind.NEW_LINE` grants a free line. `NetworkProgression.grant_free_path()` bumps `purchased_num_paths` by one (capped at `num_paths`, returning whether it granted) — `record_path_purchase` MINUS the `line_credits` spend; `Mediator._grant_free_line` calls it and, on a grant, `update_unlocked_num_paths()` to refresh the derived `unlocked_num_paths` + path-button lock states (the exact purchase-flow cache refresh). The `_apply_offer` NEW_LINE arm now calls it (the locomotive/carriage/tunnel arms stay no-op — GM-10e/f/g). Because `purchased_num_paths` is already persisted and `_require_running_config` pins the TOTAL `numPaths` (unchanged), a granted line is Continue-exact with NO save/checkpoint-schema change (proven by round-trip); at the `num_paths` cap the grant is a state-inert no-op. Known limitation (deferred as GM-11 balance): a NEW_LINE offer generated when already at the cap is a wasted pick — excluding it from the pool would couple `generate_offers` to `purchased_num_paths`. `resolve_week_boundary(offer)` CONFINES application to a genuine pending choice — it raises unless the offer is one of `current_offers` at a held boundary — so no out-of-band call (a headless `MiniMetroEnv` with no calendar, a fabricated offer, or an offer the week did not present) can grant an upgrade and bypass the weekly economy. The GM-10a–d week-boundary hold + offer generate/apply LOGIC is factored into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023 — the mediator crossed the 1000-line hard ceiling; the facade reads/writes the host mediator's already-owned state — `steps`/`week_calendar`/`current_offers`/`context`/`_progression` — with no new fields, and invokes the spy-able seams `_apply_offer`/`_grant_free_line`/`_offer_rng_for_current_week` through the host, so the mediator keeps its public API); `mediator.py` drops to 940 lines and delegates.
- GM-10h (D-045) adds the SAVE/CONTINUE persistence a fleet/tunnel weekly upgrade needs (the prerequisite for the GM-10e/f/g effects), via an additive save-schema **v3**. `save_schema` gains `SAVE_SCHEMA_VERSION_V3 = 3` (`SUPPORTED = {1,2,3}`, current = 3) and ONE additive key `tunnelBonus` (`_TOP_LEVEL_KEYS_V3 = _TOP_LEVEL_KEYS_V2 | {tunnelBonus}`, a version-gated `_validate_tunnel_bonus` nonnegative-int check, and the map-identity gate widened to `version in {V2, V3}`). The FLEET is persisted as its grown TOTALS (no bonus field — `num_metros`/`num_carriages` are already stored attrs that 17 tests + the carriage rollback assign, so they can't be derived): `save_load._require_running_config` keeps `numPaths == config` for all and `numMetros`/`numCarriages == config` for v1/v2 but only `>= config` for v3. The TUNNEL gains a stored `Mediator.tunnel_bonus` (0 until upgraded) folded into the `num_tunnels` property (`None if budget is None else budget + tunnel_bonus`), which fixes `available_tunnels`/the env `tunnels` observation/`_require_legal_map_state` for free; the load-bearing fix is that `crossings.within_tunnel_budget` reads `map_definition.tunnel_budget` DIRECTLY, so the bonus is folded there too (`+ getattr(host, "tunnel_bonus", 0)`) or a bonus would never unblock a real crossing. `save_game.serialize_game` runs a new `_require_valid_upgrade_state` FIRST — a below-config fleet or a nonzero tunnel bonus on an unbounded map is rejected BEFORE the atomic write, so a desynced/forged state can't clobber a valid autosave; restore defaults `tunnelBonus` on absence. v1/v2 fixtures stay byte-frozen; the frozen `scripts/fixtures/save-v3-classic.json` pins the additive v2→v3 upgrade. NO checkpoint-schema change (a bonus is absorbed into the totals; RL never applies an offer, so bonuses stay 0 and the observation/checkpoint bytes are unchanged). A forged high fleet total loads (authoritative editable state, matching the threat model); a nonzero tunnel bonus is legal only on a bounded map. Applied-offer persistence is this unit; PENDING-offer (mid-offer) persistence is GM-10i.
- `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
- `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
- `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
- `src/passenger_capacity.py` owns the pure next-executable station-service oracle, identity-aware cache reconciliation with destination, executable transfer, then boarding priority, and the queued-return drain that force-alights exitless riders in one holder-order batch only when that oracle is quiet, leaving the service cache untouched. `src/passenger_flow.py` owns spawning, tick coordination, stop/exchange, delivery, waiting/game-over, scoped replanning, and proposal application; it executes one service identity per 500-millisecond interval, recomputes after every effect, preserves residual large-step progress, and creates no dwell interval for blocked work. Each call receives the current structural `PassengerFlowHost`; `Mediator` retains the public signatures, canonical collections, RNG, clocks, progression, router, factories, hooks, and identity-bound cache.
- `src/input_coordinator.py` owns path-button UI, layout, compatibility-render, mouse/keyboard, pause/speed, structured-action, and transient route-edit coordination as a dependency-light stateless component; `src/fleet_input.py` owns strict path index/id locomotive and carriage action selection plus release dispatch through the same public facade methods. `src/ui/fleet_button.py` and `src/ui/carriage_button.py` bind four controls only to stable path-button slots and resolve the live path at use time. Layout validation runs before mutation and reserves a quantization-safe bottom control band. `src/input_coordinator_host.py` holds only its structural facade typing contract. Assigned-button redraws remain immutable `src/path_redraw.py` values, while `src/path_handle_input.py` owns two-phase selection/gesture cleanup, `src/path_handles.py` owns weak idle selection plus immutable strong active edits, and `src/path_handle_geometry.py` builds collision-resolved descriptors shared by input and rendering. `Mediator` retains canonical UI, renderer, progression, topology, fleet, clock, and input state; false-to-true game over clears active pointer/edit references at the passenger-flow facade boundary.
- `scripts/verify_path_lifecycle_differential.py` materializes an exact committed baseline through `git archive`, runs baseline and candidate lifecycle scenarios in isolated bytecode-disabled child processes, guards each source tree against drift, and emits one canonical seven-action/nine-record equality artifact plus its digest summary without checking out or mutating either source tree.
- `scripts/verify_passenger_flow_differential.py` and its dependency-light support module apply the same non-mutating archived-baseline discipline to seeded spawning, pause/speed/waiting behavior, three fresh graph phases, metro delivery-transfer-boarding order, lazy arrival/route/fallback proposal effects, live-list mutation, and callable finalization timing. Exact-path `.gitattributes` rules keep the canonical artifact and summary LF-stable across Windows `core.autocrlf=true` checkouts so byte-level `--expected` replay remains portable.
- `scripts/verify_input_coordinator_differential.py` and its three split case/support modules guard the GM-03f input-coordinator extraction against its archived pre-extraction GM-03e baseline (`7ff9d9c`) in isolated bytecode-disabled children, assert source origins and pre/post runtime/verifier hashes, freeze nonzero case/record/event cardinalities, and cover hit-test, mouse/keyboard, purchase, pause/speed, and structured-action order. The layout/render case was retired at scenario version `v2` because GM-06c's pre-mutation `validate_resource_control_layout` reserved-band check, which the frozen baseline predates, makes that case's small-surface `prepare_layout` probes no longer comparable across the baseline boundary. Exact-path LF attributes plus external-output `core.autocrlf=true` replay make the canonical artifact byte-portable.
- `src/game_clock.py` owns the bounded deterministic `17, 17, 16` millisecond cadence, while `src/game_session.py` provides the shared player-event and fixed-update driver. The pygame window handles input before updates and uses one `Clock.tick(60)` pacing authority.
- `src/app_controller.py` owns the human entry path's explicit screen-state machine (`TITLE`, `PLAYING`, `PAUSE_MENU`, `GAME_OVER`, the GM-08a `SETTINGS`, and the GM-08c `TUTORIAL`): it consumes already-converted virtual-coordinate events, decides which reach `GameSession.dispatch`, absorbs the historical loop-inline game-over branch, and owns the one shared reconstruction path through the construction callable `main.run_game` supplies, so the controller never constructs the triple or touches the display and headless/programmatic entries (`env.py`, `rl/player_env.py`, `recursive_playtest.py`, `agent_play.py`) never meet it. `src/ui/menu_screens.py` provides the deterministic title/pause-menu layouts (exposed hit-test rects — the title and pause stacks each append a `settings` entry after their prior controls, so those earlier rects stay byte-identical) and byte-stable draw functions the loop paints above or instead of the gameplay frame; `draw_title_screen(surface, continue_available=...)` paints Continue only when available, `draw_notice` renders the load-failure banner, and `draw_settings_menu(surface, settings)` paints the SETTINGS chrome. The GM-08a `SETTINGS` screen is reachable from both the title and pause menus (from pause it keeps the `menu` hold and Back returns to the opening screen) and edits `AppController.current_settings` through the optional inert `settings` seam. `Mediator` keeps pause ownership behind the retained `is_paused` bool facade over an internal per-instance lazily created pause-reason store (`user`, `menu`): the property setter, `set_paused`, structured `pause`/`resume`, speed actions, and the Space toggle touch only the `user` reason, while `hold_pause_reason`/`release_pause_reason` are the controller-only `menu` entry points, so a menu hold can never be cleared by gameplay input and reasons stay process-local runtime state outside checkpoints and observations. GM-07c wires GM-07b persistence into this shell only: `AppController` takes optional inert `build_from`/`autosave` seams and, per D-027, autosaves on pause-menu entry and Exit to Title (before releasing the menu hold), deletes the autosave at the `PLAYING`->`GAME_OVER` promotion and the game-over exits, and resumes a proven-loadable save via title Continue while surfacing a `notice` on load failure; `main.run_game` supplies that seam bound to the single `saves/autosave.json` slot behind a patchable module-level `AUTOSAVE_PATH` and applies the state-gated window-close save/delete, so autosave and Continue live only in `main` plus `app_controller` and no headless, agent, recursive, or RL surface imports the save modules. GM-07d adds a second optional inert seam beside it (D-028): `AppController` takes a `highscores` recorder that it invokes exactly once at the `PLAYING`->`GAME_OVER` promotion — handing the seam the LIVE mediator only when present (GM-09f2/D-039: the recorder reads BOTH the deliveries objective and the map identity off it, so the controller itself touches no mediator attribute and a seam-less controller reads nothing) — and stores the result in public `last_highscore_result`; `main.run_game` binds the seam and the patchable `HIGHSCORES_PATH`/`record_highscore` to `src/highscores.py`, applies the same window-close game-over record (mutually exclusive with the promotion), and draws the best indicator with `menu_screens.draw_best_indicator` after the renderer's game-over frame so the near-ceiling `game_renderer` stays untouched. GM-07e makes that promotion frame-deterministic: the block is a public idempotent `AppController.reconcile_game_over()` (a no-op unless `PLAYING` and game over) that `handle_event` calls at its top and `main.run_game` calls once per frame after `session.advance` (re-reading the render state), so a tick-driven game over records, deletes the autosave, and shows the indicator the frame it ends independent of any incidental event; the state-gated window-close record stays mutually exclusive, now firing only for a game over still un-promoted at the QUIT. GM-08b hangs a pure gameplay-audio consumer off that same post-`reconcile_game_over` hook (`src/audio.py`, D-030): it reads the post-reconcile counters and plays one SFX tone per delta, entirely in `main.run_game` with no `AppController`/`Mediator` change, and defaults to an inert backend so only the interactive entry point ever opens a device. GM-08c adds the `TUTORIAL` screen and an optional inert `build_tutorial` seam beside the others: a menu-launched coached playthrough of a seeded, game-over-suppressed game whose per-frame `advance_tutorial` hook (beside the audio/reconcile hooks) drives the `src/tutorial.py` step machine, with no autosave/highscore and Escape skipping to the title (see the `tutorial.py` entry below).
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
- `src/settings.py` (GM-08a, D-029) owns the typed, presentation-only settings store, reusing `save_schema.canonical_save_bytes` and the scalar validators plus its own copy of the save-local atomic writer — so it joins the save-module isolation set and imports no gameplay directly (the shared save validators pull geometry/checkpoint dependencies transitively, exactly as the other save modules do). The immutable `Settings` value carries `fullscreen`, integer-percent `master`/`music`/`sfx` volumes, and `reduced_motion`; `validate_settings` is strict (exact keys before field access, forward versions and non-ASCII/out-of-range values rejected). Unlike `load_game`, `load_settings` is FAIL-SAFE: any missing, malformed, or forward-version file returns `DEFAULT_SETTINGS` and never raises; `save_settings` validates before writing and RAISES on failure with the best-effort swallow at `main`. `AppController` gains an `AppScreen.SETTINGS` state and an optional inert `settings` seam (`load`/`save`); it holds the current value in `current_settings` and edits it on the SETTINGS screen, and `main.run_game` injects the seam over a patchable `SETTINGS_PATH`, applies `fullscreen` through `pygame.display.set_mode`, and threads `reduced_motion` into the renderer. Settings never touch `Mediator` or `config` balance, so no save-schema version bump is implied (D-026).
- `src/rendering/flexible_draw.py` (GM-08a) holds the kwarg-filtering `_call_flexibly` dispatch extracted from `game_renderer` so the renderer can pass optional draw kwargs (`resources`, `reduced_motion`, ...) uniformly while each entity draw receives only what its signature declares; `reduced_motion` (D-029) rides that boundary to the `station`/`passenger`/`path_button` blink predicates (held steady) and the station snap blip (suppressed), defaulting False so every non-reduced path stays byte-identical, and the extraction keeps `game_renderer` under 500 lines.
- `src/audio.py` (GM-08b, D-030) owns procedural gameplay sound effects, importing only `pygame`/`numpy` and holding all its own tone constants (never `config`). `_generate_tone` builds a deterministic MONO int16 sine (with a click-free envelope) against a parameterized sample rate; `ProceduralAudio` reads the mixer's ACTUAL negotiated rate/channels from `pygame.mixer.get_init()`, builds one channel-shaped `Sound` per event, and plays best-effort at gain `(master/100)*(sfx/100)`; `NullAudio` is the inert backend; `create_audio` initializes the mixer and builds every sound in one `try/except`, degrading to `NullAudio` on any failure so audio-init never blocks play. `snapshot_of`/`diff_and_play` are a pure, duck-typed, tolerant per-frame counter differ (a host missing counters reads 0/False) that plays one tone per newly-occurred `deliveries`/`unlocked_num_paths`/`unlocked_num_stations`/`is_game_over` (False→True)/snap-sum delta. Audio is a pure `main.run_game` loop-level consumer at the post-`reconcile_game_over` hook — NOT an `AppController` seam and no `Mediator`/`GameSession`/`rendering` change — that owns its OWN session reference and re-baselines the snapshot on a session change so Continue/New Game/Restart never replay a stored delta as a spurious burst. `run_game`'s `audio_backend` defaults to inert `NullAudio`; the real mixer is constructed ONLY at the `__main__` entry point, so no test or embedder (even one driving `run_game` unbounded) opens a device. `audio` lives outside `rendering/` (transitively imported by `rl/player_env.py`) and joins both persistence-isolation scans, so only `main` imports it.
- `src/tutorial.py` (GM-08c, D-031) owns the coached-tutorial step machine — a pure, duck-typed, stdlib-only observer (the GM-08b snapshot pattern) that reads mediator attributes only. `TUTORIAL_STEPS` orders seven lessons (draw, reroute, train, deliver, overload, pause, speed); `tutorial_snapshot` tolerantly captures the signals; and `advance(progress, mediator, elapsed_ms, paused)` completes a `state` step on its predicate or a `dwell` step (overload) after `OVERLOAD_DWELL_MS` of unpaused play, re-baselining each transition. Reroute precedes the train (a metro mid-service persistently blocks `replace_path` under the strict path-lifecycle default), the reroute predicate accepts any route-topology change (a delete-and-redraw mints a fresh id), and train/pause/speed are current-state checks so they can never soft-lock at the metro cap or an already-used control. `AppController` gains an `AppScreen.TUTORIAL` state, an optional inert `build_tutorial` seam, `_start_tutorial`/`_handle_tutorial`/`advance_tutorial`/`tutorial_overlay` (Escape skips to the title with the letterbox-cancel; a cold start directly in TUTORIAL also builds the tutorial), and never autosaves or records. `main.run_game` supplies the seam over a seeded `Mediator(seed=42)` whose `overdue_passenger_threshold` is raised on the instance so the sim never game-overs or freezes (a per-instance write, not a `Mediator`/`config` change), calls `advance_tutorial` once per frame beside `reconcile_game_over`, and paints `menu_screens.draw_tutorial_overlay` over the real game frame — the controller exposes the overlay strings so `main` never imports `tutorial`. `tutorial` joins the isolation scan and is imported only by `app_controller`, so no headless/agent/recursive/RL surface constructs it; no `Mediator`/`GameSession`/`rendering`/schema/observation/checkpoint change.
- `src/highscores.py` (GM-07d, D-028) owns the persistent high-score leaderboard, reusing `save_schema.canonical_save_bytes` and the scalar validators plus its own copy of the save-local atomic writer (`main` owns the `SAVE_RULES_VERSION` identity) — so it joins the save-module isolation set but imports no gameplay. The document is a strict versioned `{schemaVersion, stateContract, entries}` shape whose entries carry a full map-identity key — GM-09f2 (D-039) makes it schema **v2**, keying each entry by `map`/`mapDefinitionVersion`/`rulesVersion` with `deliveries` (so a future `classic@2` terrain revision ranks and caps separately from `classic@1`, mirroring the save's `(mapId, mapDefinitionVersion)` identity); the `stateContract` stays `mini-metro-highscores-v1` across the additive version. `validate_highscores` checks exact keys before field access and rejects forward versions, bad types, non-ASCII content, and a malformed `map` id (nonempty ASCII, no whitespace — the save's mapId grammar). `record_score` requires an explicit map/mapDefinitionVersion/rulesVersion and validates its inputs (`_positive_int` version, `_map_id` grammar), then returns a NEW board (pure) with the score inserted, all entries in the canonical identity-asc/deliveries-desc order (one shared `_identity` helper keys the sort, the per-key cap, AND the rank count) with stable tie-breaking and the recorded identity capped at ten (other keys never dropped), and a `RecordResult` carrying the new entry's rank and best flag. Unlike `load_game`, `load_highscores` is START-EMPTY tolerant: any failure — missing, non-ASCII, malformed, duplicate-key, forward-version, a **legacy v1 board** (NOT migrated: its classic labels are not provably accurate, since the recorder was classic-hardcoded while non-Classic saves became loadable, so it starts empty rather than synthesizing authoritative `classic@1`), or pathologically nested (RecursionError) — yields the empty board and never raises, because a cosmetic leaderboard must never block play; `save_highscores` validates the board before writing and still RAISES on failure, and the best-effort swallow lives at `main`'s single patchable `record_highscore` recorder that both game-over surfaces funnel through.

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
- Ten original mediator-facing discovered modules partition behavior by ownership: interaction/layout, routing decisions, route-facade contracts, route observability, path lifecycle, path-facade and failure contracts, simulation/spawning/game over, passenger/metro flow, and progression/purchases. They preserve the former monolithic suite's exact 57 test bodies while adding focused characterization for extracted boundaries. `test/test_network_progression.py` directly covers dependency-free progression policy and cached-state semantics; four direct route-planner modules cover dependency-free queries, selection, resolver and callable-lifetime timing, and lazy proposal iteration; `test/test_path_lifecycle.py` plus its two non-discovered support modules cover the stateless host boundary, transition ordering, rebinding, factory lifetime and failures, and import isolation. `test/test_passenger_flow.py` plus its non-discovered support module cover the dependency-light stateless host boundary directly; two additional facade/effect contract modules pin all 16 public signatures, late dependency resolution, partial failures, live iteration, graph freshness, and exact passenger-effect ordering. `test/test_input_coordinator.py`, `test/test_input_coordinator_edge_contract.py`, and their non-discovered support module directly cover the final dependency-light stateless boundary, while `test/test_mediator_input_contract.py` is replayable against both the archived baseline and candidate and freezes all 19 real facade signatures plus late dependencies, subclass precedence, collection replacement, partial effects, and Python bound-method evaluation order. The five GM-05a modules add 40 focused structured-action/replay, metro continuity, passenger transition, rollback, and adversarial transaction-edge methods for atomic path replacement. The seven GM-05b modules add 52 pure-draft, real-event, player-pixel, canonical-state, button-feedback, preview, and no-tick continuity methods. GM-05c adds 45 focused pure-handle, converted-input, rendering/cache, fast/fidelity pixel, canonical-state, and live letterbox methods. GM-06a adds 34 focused runtime/failure, observation/checkpoint, HUD/geometry, and actual fast/fidelity low-level pixel methods. GM-06b adds 73 focused Python methods plus four Node replay tests for assignment transactions, canonical geometry preflight, queued movement/settlement, gesture/render/Pixel parity, canonical-LF training-source preservation, checkpoint v3, and recursive/agent v4 compatibility. GM-06c adds 172 focused Python methods plus four new Node tests for carriage conservation, capacity-aware service, controls/pixels, consist geometry, checkpoint v4, recursive/agent v5, and frozen v1-v4 behavior. `InputCoordinator` is 498 lines, its structural host is 104, `GameRenderer` is 478 (after GM-08a extracted the kwarg-filtering `_call_flexibly` dispatch into `src/rendering/flexible_draw.py`), the three recursive checkpoint modules are 497/499/243, and the explicit `Mediator` facade is 757 lines; every other changed handwritten production file remains below 500 lines.

## Rendering tests

- `test/test_game_clock.py` covers fixed cadence, clamp/drop behavior, pause/terminal consumption, and interpolation observer ordering.
- `test/test_render_layout.py` covers centered lanes, reverse-pair geometry, corner/loop metro projection, antialiased pixels, and cache invalidation/bounds.
- `test/test_game_renderer.py` covers lazy resources, layer order, metro interpolation, cached button fonts, the four-value HUD, and prepared game-over controls.
- `test/test_render_purity.py` renders real software surfaces and proves repeatable RGBA bytes, complete render-facing state and canonical-checkpoint purity, cache reuse, and rendered-versus-never-rendered trajectory equivalence.
- `test/test_gm05b_preview_rendering.py` covers selected/invalid feedback, immutable preview/live parity, shared-lane ordering, overlay layering, deterministic clipped cache behavior, and render-only reference bounds; `test/test_gm05b_render_continuity.py` covers exact-segment freshness, retained-edge and padding rebasing, loop/reversal direction, safe live-pose fallback, next-step recovery, and old-segment release.
- `test/test_path_handles.py` and the four GM-05c modules cover weak/strong reference boundaries, deterministic collision relocation, loop and endpoint edit derivation, converted two-phase input, arbitrary-slot and removal rendering, cache-free byte stability, actual downscaled fast/fidelity observations, checkpoint/structured-array invisibility, and game-over cleanup; the three GM-06a modules bind every inventory transition and failure seam to runtime, structured observation, genuine checkpoint v1/v2 reconstruction, exact HUD fallback and geometry, and genuine low-level inventory glyphs. The GM-06b control/render/Pixel modules cover quantized locomotive hits, queue pixels, synthetic-padding avoidance, explicit player actions, and a real-coordinate positive-delivery demonstrator. The GM-06c controls/render/Pixel/consist modules cover the four-control band, enabled/disabled states, body/passenger slicing, whole-consist queue outlines, coherent route sampling, topology rebasing, feasibility-checked terminal radial expansion, and dense two/four/six/seven-body terminal-turn clearance through real `Path.move_metro` arrivals; `test/test_main.py` retains live letterbox mouse-up coverage.

python_mini_metro/
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
|     |  \- README.md
|     \- done/
|        |- README.md
|        |- agents-repo-fit/
|        |- full/
|        |- rendering/
|        \- rl-framework/
|- scripts/
|  |- evaluate_rl.py
|  |- fixtures/
|  |  |- recursive-playtest-v2.json
|  |  \- recursive-playtest.json
|  |- playtest-recursive.mjs
|  |- playtest-verify.mjs
|  |- profile_rl_history.py
|  |- profile_rl_history_worker.py
|  |- recursive-ledger.mjs
|  |- recursive-ledger-lock.mjs
|  |- recursive-pass.mjs
|  |- source-provenance-engine.mjs
|  |- source-provenance.mjs
|  \- train_rl.py
|- src/
|  |- __init__.py
|  |- agent_play.py
|  |- config.py
|  |- env.py
|  |- game_clock.py
|  |- game_session.py
|  |- main.py
|  |- mediator.py
|  |- progression.py
|  |- route_planner.py
|  |- recursive_checkpoint.py
|  |- recursive_contract.py
|  |- recursive_oracles.py
|  |- recursive_playtest.py
|  |- simulation_context.py
|  |- travel_plan.py
|  |- type.py
|  |- utils.py
|  |- entity/
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
|  |  |- game_renderer.py
|  |  |- interpolation.py
|  |  |- layout.py
|  |  \- network_renderer.py
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
|     |- path_button.py
|     |- speed_button.py
|     \- viewport.py
|- test/
|  |- __init__.py
|  |- playtest-recursive.test.mjs
|  |- playtest-verify.test.mjs
|  |- recursive-ledger.test.mjs
|  |- recursive-pass.test.mjs
|  |- recursive-fixtures.mjs
|  |- source-provenance.test.mjs
|  |- mediator_test_support.py
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
|  |- test_main.py
|  |- test_mediator_interaction.py
|  |- test_mediator_passenger_flow.py
|  |- test_mediator_paths.py
|  |- test_mediator_progression.py
|  |- test_mediator_route_contract.py
|  |- test_mediator_route_observability.py
|  |- test_mediator_routing.py
|  |- test_mediator_simulation.py
|  |- test_network_progression.py
|  |- test_overdue_threshold.py
|  |- test_path.py
|  |- test_player_env.py
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

- `src/env.py` remains the public Gym-like drive surface over `Mediator`; its default reward is the delta in lifetime passenger `deliveries`, while explicit `line_credits_delta` mode reconstructs the legacy spendable-credit reward. Structured observations name both values and retain `score` as a line-credit compatibility alias. `Mediator.overdue_passenger_threshold` is the canonical overload field with repository default `2`; the writable `max_waiting_passengers` compatibility property addresses the same value. The recursive loop uses `MiniMetroEnv.reset(seed)` and `MiniMetroEnv.step(action, dt_ms)` without driving the pygame GUI clock.
- `src/simulation_context.py` gives every `Mediator` independent Python and NumPy random streams. Interactive, structured, and pixel environments share the same gameplay code without sharing host-global RNG state, so gameplay mechanics, normalized checkpoints, array views, and pixels are reproducible when same-process or spawned environments are interleaved. Opaque shortuuid entity IDs remain session-unique and are intentionally excluded from deterministic checkpoint comparison.
- `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
- `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
- `src/game_clock.py` owns the bounded deterministic `17, 17, 16` millisecond cadence, while `src/game_session.py` provides the shared player-event and fixed-update driver. The pygame window handles input before updates and uses one `Clock.tick(60)` pacing authority.
- `src/entity/path.py` owns logical centerline segments used by metro movement. `src/rendering/layout.py` derives immutable, symmetric visual lanes without rebuilding or re-identifying those simulation segments.
- `src/rendering/network_renderer.py` owns one bounded antialiased route cache per renderer. `src/rendering/interpolation.py` tracks render-only previous/current metro poses, and `src/rendering/game_renderer.py` composes routes, stations, metros, controls, a two-value deliveries/line-credits HUD, and overlays without mutating gameplay state. Fonts and surfaces are renderer-owned and lazy so state-only and headless sessions do not require a display.
- `Mediator.prepare_layout(width, height)` prepares all player hitboxes before input. Rendering consumes those prepared rectangles; drawing primitives never establish or move hitboxes.
- `src/rl/protocol.py` is the dependency-free, fingerprinted player contract: registered pixel profiles, low-level `MultiDiscrete` action semantics, exact coordinate mapping, cursor pixels, reward modes, fixed ticks, and episode horizon. `src/rl/player_env.py` implements that contract with Gymnasium over the same `GameSession`, player event converter, and `GameRenderer` as the window.
- `PlayerPixelEnv` exposes live game state only as pixels. Its implementation reads canonical deliveries and line credits, while terminal-metrics v1 deliberately retains the serialized `display_score` key for old manifests. Terminal episode metrics are emitted after the final action; `src/rl/privileged_oracle.py` is an explicitly separate validation/curriculum surface and must not be passed to a learning policy. `src/rl/demonstrator.py` uses that oracle only to generate deterministic low-level player actions for a positive-delivery integration case.
- `src/rl/dependencies.py` owns lazy imports for the optional RL stack. `src/rl/policy.py` owns recurrent/feed-forward hyperparameter contracts plus model construction and loading; fresh runs use SB3-Contrib RecurrentPPO, recurrent minibatches of 64, `src/rl/model.py`'s bounded adaptive-pooling `MiniMetroCNN`, and separate one-layer, 256-unit actor and critic LSTMs, while feed-forward Stable-Baselines3 PPO remains an explicit ablation. `src/rl/history.py` owns dependency-light immutable temporal descriptors and fingerprints plus the single profiled default factory for exact offsets `[128, 64, 7, 6, 5, 4, 3, 2, 1, 0]`; `src/rl/temporal_history.py` owns the optional-dependency bounded vector ring, terminal-copy, and fail-closed reset lifecycle. `src/rl/training.py` owns spawn-safe `base -> VecMonitor -> VecTemporalHistory` construction, default-factory consumption, environment/trainer source hashing (including both dependency lockfiles and history/manifest/temporal modules), and checkpoint callbacks while retaining `DEFAULT_FRAME_STACK = 8` and the former public training imports for explicit contiguous/PPO compatibility. `src/rl/evaluation.py` carries recurrent state across decisions and resets it at episode boundaries. `scripts/train_rl.py` resolves fresh recurrent omission to the promoted ten-frame descriptor, fresh explicit PPO omission to contiguous eight, `--frame-stack` to an explicit contiguous control, and reviewed `--history-layout` names to one descriptor shared by train/eval/persistence; resume and `scripts/evaluate_rl.py` reconstruct only the authenticated saved descriptor. Manifests bind algorithm and exact history identity across resume/evaluation, and evaluation separates final game-over totals from right-censored horizon totals. Core installs include Gymnasium; `requirements-rl.txt` adds Stable-Baselines3, SB3-Contrib, PyTorch transitively, and TensorBoard, while the universal hashed locks resolve platform-specific wheels reproducibly.
- `src/rl/resource_profile.py` owns dependency-light candidate, storage, MAC, cyclic-order, and promotion-gate contracts; `src/rl/profile_validation.py` independently recomputes the exact task/trainer/history/tensor/rate contract before a worker can count as valid. `src/rl/windows_api.py` isolates the pinned `ctypes` Toolhelp32/PSAPI ABI, while `src/rl/windows_resources.py` owns retained process identities, descendant discovery, full-tree current-working-set samples, system commit/physical metadata, cadence failures, and scoped cleanup. `src/rl/profile_supervisor.py` owns pre/post clean-source attestation, bounded handshake and log draining, launcher/worker supervision, raw sample hashing, and bounded summary metadata. The stdlib-only top of `scripts/profile_rl_history_worker.py` blocks at a pre-import handshake; after release it constructs the real temporal wrapper and RecurrentPPO, drives two explicit production-horizon collect/train iterations, and measures actual padded recurrent batches. `scripts/profile_rl_history.py` counterbalances fresh workers and applies the preregistered engineering-safety gates. Raw profile evidence is ignored under `output/`; compact committed evidence records its digests when GM-02d2 runs.
- `src/rl/artifacts.py` atomically writes versioned artifact indexes, hashes and parses one exact authenticated index snapshot, and captures one exact model byte sequence for SB3 rather than reopening the verified path. Training writes a zero-step recovery model/manifest before learning, refreshes provenance after periodic checkpoints, and uses unique index files so interruption cannot invalidate the previous recovery pair.
- `src/rl/provenance.py` captures immutable runtime package/Python metadata, including Shapely and shortuuid because they affect player transitions and identity-bearing state, plus Git revision/dirty paths. `src/rl/manifest_schema.py` owns the immutable v1/v2 record and strict JSON key migration; `src/rl/manifest.py` owns atomic I/O and compatibility validation. Manifest v2 records the descriptor plus an independently recomputed `historyFingerprint`, while genuine v1 bytes normalize their positive `frameStack` to contiguous offsets and reserialize without v2 keys. Fresh, resumed, and evaluated environments now consume that exact descriptor through the temporal ring; an explicit equal-channel but semantically different request is rejected by history fingerprint before artifact access, and SB3 separately rejects observation-shape mismatches before learning or evaluation. Evaluation reconstructs the manifest-declared task, defaults to the saved evaluation seed, and refuses silent protocol, task, history, content, trainer, runtime, or model-byte drift; every supported override is explicit and tagged.
- `src/agent_play.py` writes v3 playthrough records with explicit per-step/final deliveries, line credits, reward contract, and the post-reset overdue threshold. Its legacy return and `score`/`final_score` fields continue to mean line credits; separately named delivery-returning helpers expose the canonical objective. Schema-less/v1 and literal v2 records remain supported and reconstruct historical threshold `1`; v3 validates and applies its recorded threshold after reset replaces the mediator.
- `src/recursive_contract.py` owns strict immutable v1/v2/v3 scenario and recorded-input validation plus reward/threshold reconstruction. `src/recursive_playtest.py` preserves its existing public validation/version imports as compatibility re-exports, executes every ordered operation, and writes strict JSON inputs, transcript rows, authored findings, and the run result. V1 reconstructs `line_credits_delta` and threshold `1`; v2 preserves the explicit `deliveries` contract and threshold `1`; v3 requires deliveries plus a positive non-boolean threshold. Scenario v1 emits checkpoint v1, while scenarios v2/v3 emit checkpoint v2 after applying the selected threshold to the mediator created by reset.
- `src/recursive_checkpoint.py` converts observations and latent simulation state into UUID-free canonical JSON. Checkpoint v2 names deliveries, line credits, reward mode, their environment baselines, and the overdue threshold while retaining legacy aliases; the public normalizer projects genuine v1 checkpoints into that comparison shape without mutating recorded evidence, and v1 emission rejects a delivery-mode environment. Checkpoints also cover topology, passengers and travel plans, progression and unlocks, spawning counters, metro motion and dwell state, and Python/NumPy RNG state.
- `src/recursive_oracles.py` checks reference integrity and non-finite values; `src/recursive_playtest.py` combines those checks with action-result, selected-contract reward, rejected-action, pause, terminal-state, topology, and transcript-cardinality oracles. Findings are born unverified and carry a stable class in `data.class`.

## Recursive pass data flow

1. `scripts/source-provenance.mjs` inventories relevant runtime source with per-file and tree SHA-256 digests, records relevant Git status, and enforces the clean-by-default policy. `scripts/source-provenance-engine.mjs` independently resolves the live `civ-engine` package and pins its version, commit, and complete `package.json` plus `dist/` runtime-tree digest, including ignored build output. `--allow-dirty` is an explicit canary/development escape hatch that preserves attributable mismatches and `source-diff.patch` when a local diff is available.
2. `scripts/playtest-recursive.mjs` captures and writes that provenance before driving, creates a unique append-only directory under `output/recursive/`, launches the Python driver with the checked-in deterministic fixture by default, and captures the drive logs and artifacts.
3. `scripts/playtest-verify.mjs` launches a fresh Python process against the recorded `inputs.json`, compares exact replayable input metadata, transcript results, canonical checkpoint vectors, and authored finding semantics, then writes verification evidence and strict replay-verified findings. Standalone verification attempts use unique subdirectories under `<run-id>/verification-attempts/`.
4. Before finalization, the driver recaptures both source trees and turns any mid-run drift into an attributable `source-changed` failure with final-state evidence. `scripts/recursive-pass.mjs` selects the highest-severity verified open finding, builds civ-engine run/pass manifests, and validates their repository-level completeness including source-state summaries. New manifests use `source-state-v2`; immutable `source-state-v1` rows from earlier harness revisions remain readable during reconciliation. `scripts/recursive-ledger.mjs` and `scripts/recursive-ledger-lock.mjs` own write-ahead paired persistence, atomic manifest creation, repair of an unterminated final JSONL fragment, token-checked heartbeat locks, dead-owner recovery, and one-pass intent reconciliation.
5. Each run keeps `run-manifest.json` and `pass-manifest.json`; aggregate run rows append to `output/recursive/ledger.jsonl` and pass rows append to `output/recursive/passes.jsonl`. Pending intents are deleted only after both rows are durably confirmed. Outcomes are `verified` or `run-failed` for run manifests and `no-fix-candidate`, `proposal-only`, or `run-failed` for pass manifests.

The Node boundary depends on the live sibling `civ-engine` through `file:../civ-engine`. `package-lock.json` records engine 2.2.0, and CI checks out commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` as that sibling, builds it under Node 22, asserts the imported version, then runs the Node contract tests and Python unit suite. The pass is scripted and proposal-only: no model provider, automatic source edit, apply arm, or auto-merge boundary is present.

## Recursive-loop tests

- `test/test_recursive_playtest.py` covers strict scenario/input validation, one transcript row per operation, and recorded-input replay; `test/test_recursive_threshold_schema.py` pins immutable v1/v2/v3 threshold reconstruction and checkpoint mapping; `test/test_recursive_checkpoint.py` covers UUID-free checkpoint construction, schema normalization, alias agreement, reward-contract identity, and latent-state observability. `test/test_overdue_threshold.py` and `test/test_agent_play_threshold.py` cover default runtime overload semantics and agent evidence migration without enlarging the mediator characterization suites.
- `test/test_recursive_oracles.py` covers cross-view topology and the remaining environment-contract oracle classes.
- `test/source-provenance.test.mjs`, `test/recursive-ledger.test.mjs`, `test/playtest-verify.test.mjs`, `test/recursive-pass.test.mjs`, and `test/playtest-recursive.test.mjs` cover local and linked-engine inventory, ignored-runtime mismatch rejection, start/end recapture, token-safe concurrent/crash reconciliation, torn-tail repair, exact fresh-process verification, strict evidence promotion, manifest contracts, public verifier retries, and end-to-end success/failure outcomes. `test/recursive-fixtures.mjs` supplies strict shared manifest fixtures without registering another test entry point.

## Mediator characterization tests

- `test/mediator_test_support.py` owns the shared per-test mediator fixture, pygame draw cleanup, interaction helper, and two-station network builder without matching unittest's default discovery pattern.
- Eight discovered modules partition mediator behavior by ownership: interaction/layout, routing decisions, route-facade contracts, route observability, path lifecycle, simulation/spawning/game over, passenger/metro flow, and progression/purchases. They preserve the former monolithic suite's exact 57 test bodies while adding focused characterization for extracted boundaries. `test/test_network_progression.py` directly covers dependency-free progression policy and cached-state semantics; four direct route-planner modules cover dependency-free queries, selection, resolver and callable-lifetime timing, and lazy proposal iteration. Production `src/mediator.py` decomposition continues through GM-03d to GM-03f.

## Rendering tests

- `test/test_game_clock.py` covers fixed cadence, clamp/drop behavior, pause/terminal consumption, and interpolation observer ordering.
- `test/test_render_layout.py` covers centered lanes, reverse-pair geometry, corner/loop metro projection, antialiased pixels, and cache invalidation/bounds.
- `test/test_game_renderer.py` covers lazy resources, layer order, metro interpolation, cached button fonts, and prepared game-over controls.
- `test/test_render_purity.py` renders real software surfaces and proves repeatable RGBA bytes, complete render-facing state and canonical-checkpoint purity, cache reuse, and rendered-versus-never-rendered trajectory equivalence.

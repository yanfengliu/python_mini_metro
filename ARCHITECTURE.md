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
|  |  \- recursive-playtest.json
|  |- playtest-recursive.mjs
|  |- playtest-verify.mjs
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
|  |- recursive_checkpoint.py
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
|  |  |- manifest.py
|  |  |- model.py
|  |  |- player_env.py
|  |  |- policy.py
|  |  |- privileged_oracle.py
|  |  |- provenance.py
|  |  |- protocol.py
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
|  |- test_agent_play.py
|  |- test_coverage_utils.py
|  |- test_env.py
|  |- test_gameplay.py
|  |- test_game_clock.py
|  |- test_game_renderer.py
|  |- test_geometry.py
|  |- test_graph.py
|  |- test_headless_render.py
|  |- test_main.py
|  |- test_mediator.py
|  |- test_path.py
|  |- test_player_env.py
|  |- test_recursive_oracles.py
|  |- test_recursive_playtest.py
|  |- test_render_layout.py
|  |- test_render_purity.py
|  |- test_rl_artifacts.py
|  |- test_rl_cli.py
|  |- test_rl_demonstrator.py
|  |- test_rl_evaluation.py
|  |- test_rl_legacy_compat.py
|  |- test_rl_manifest.py
|  |- test_rl_protocol.py
|  |- test_rl_training.py
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

- `src/env.py` remains the public Gym-like drive surface over `Mediator`; the recursive loop uses `MiniMetroEnv.reset(seed)` and `MiniMetroEnv.step(action, dt_ms)` without changing that API or driving the pygame GUI clock.
- `src/simulation_context.py` gives every `Mediator` independent Python and NumPy random streams. Interactive, structured, and pixel environments share the same gameplay code without sharing host-global RNG state, so gameplay mechanics, normalized checkpoints, array views, and pixels are reproducible when same-process or spawned environments are interleaved. Opaque shortuuid entity IDs remain session-unique and are intentionally excluded from deterministic checkpoint comparison.
- `src/game_clock.py` owns the bounded deterministic `17, 17, 16` millisecond cadence, while `src/game_session.py` provides the shared player-event and fixed-update driver. The pygame window handles input before updates and uses one `Clock.tick(60)` pacing authority.
- `src/entity/path.py` owns logical centerline segments used by metro movement. `src/rendering/layout.py` derives immutable, symmetric visual lanes without rebuilding or re-identifying those simulation segments.
- `src/rendering/network_renderer.py` owns one bounded antialiased route cache per renderer. `src/rendering/interpolation.py` tracks render-only previous/current metro poses, and `src/rendering/game_renderer.py` composes routes, stations, metros, controls, text, and overlays without mutating gameplay state. Fonts and surfaces are renderer-owned and lazy so state-only and headless sessions do not require a display.
- `Mediator.prepare_layout(width, height)` prepares all player hitboxes before input. Rendering consumes those prepared rectangles; drawing primitives never establish or move hitboxes.
- `src/rl/protocol.py` is the dependency-free, fingerprinted player contract: registered pixel profiles, low-level `MultiDiscrete` action semantics, exact coordinate mapping, cursor pixels, reward modes, fixed ticks, and episode horizon. `src/rl/player_env.py` implements that contract with Gymnasium over the same `GameSession`, player event converter, and `GameRenderer` as the window.
- `PlayerPixelEnv` exposes live game state only as pixels. Terminal episode metrics are emitted after the final action; `src/rl/privileged_oracle.py` is an explicitly separate validation/curriculum surface and must not be passed to a learning policy. `src/rl/demonstrator.py` uses that oracle only to generate deterministic low-level player actions for a positive-delivery integration case.
- `src/rl/dependencies.py` owns lazy imports for the optional RL stack. `src/rl/policy.py` owns recurrent/feed-forward hyperparameter contracts plus model construction and loading; fresh runs use SB3-Contrib RecurrentPPO, recurrent minibatches of 64, `src/rl/model.py`'s bounded adaptive-pooling `MiniMetroCNN`, and separate one-layer, 256-unit actor and critic LSTMs, while feed-forward Stable-Baselines3 PPO remains an explicit ablation. `src/rl/training.py` owns spawn-safe vector environments, the eight-frame default stack, environment/trainer source hashing (including both dependency lockfiles), and checkpoint callbacks while retaining the former public training imports as compatibility re-exports. `src/rl/evaluation.py` carries recurrent state across decisions and resets it at episode boundaries. `scripts/train_rl.py` and `scripts/evaluate_rl.py` are guarded Windows-safe entry points; manifests bind algorithm and stack settings across resume/evaluation, and evaluation separates final game-over totals from right-censored horizon totals. Core installs include Gymnasium; `requirements-rl.txt` adds Stable-Baselines3, SB3-Contrib, PyTorch transitively, and TensorBoard, while the universal hashed locks resolve platform-specific wheels reproducibly.
- `src/rl/artifacts.py` atomically writes versioned artifact indexes, hashes and parses one exact authenticated index snapshot, and captures one exact model byte sequence for SB3 rather than reopening the verified path. Training writes a zero-step recovery model/manifest before learning, refreshes provenance after periodic checkpoints, and uses unique index files so interruption cannot invalidate the previous recovery pair.
- `src/rl/provenance.py` captures immutable runtime package/Python metadata, including Shapely and shortuuid because they affect player transitions and identity-bearing state, plus Git revision/dirty paths. `src/rl/manifest.py` records those snapshots with protocol/task/content/trainer fingerprints, parent run digests, hyperparameters, and artifact-index authentication. Evaluation reconstructs the manifest-declared task, defaults to the saved evaluation seed, and refuses silent protocol, task, content, trainer, runtime, or model-byte drift; every override is explicit and tagged.
- `src/recursive_playtest.py` validates a versioned scenario or recorded input document, executes every ordered operation, and writes strict JSON inputs, transcript rows, authored findings, and the run result.
- `src/recursive_checkpoint.py` converts observations and latent simulation state into UUID-free canonical JSON. It covers topology, passengers and travel plans, progression and unlocks, spawning counters, metro motion and dwell state, and Python/NumPy RNG state.
- `src/recursive_oracles.py` checks reference integrity and non-finite values; `src/recursive_playtest.py` combines those checks with action-result, reward/score, rejected-action, pause, terminal-state, topology, and transcript-cardinality oracles. Findings are born unverified and carry a stable class in `data.class`.

## Recursive pass data flow

1. `scripts/source-provenance.mjs` inventories relevant runtime source with per-file and tree SHA-256 digests, records relevant Git status, and enforces the clean-by-default policy. `scripts/source-provenance-engine.mjs` independently resolves the live `civ-engine` package and pins its version, commit, and complete `package.json` plus `dist/` runtime-tree digest, including ignored build output. `--allow-dirty` is an explicit canary/development escape hatch that preserves attributable mismatches and `source-diff.patch` when a local diff is available.
2. `scripts/playtest-recursive.mjs` captures and writes that provenance before driving, creates a unique append-only directory under `output/recursive/`, launches the Python driver with the checked-in deterministic fixture by default, and captures the drive logs and artifacts.
3. `scripts/playtest-verify.mjs` launches a fresh Python process against the recorded `inputs.json`, compares exact replayable input metadata, transcript results, canonical checkpoint vectors, and authored finding semantics, then writes verification evidence and strict replay-verified findings. Standalone verification attempts use unique subdirectories under `<run-id>/verification-attempts/`.
4. Before finalization, the driver recaptures both source trees and turns any mid-run drift into an attributable `source-changed` failure with final-state evidence. `scripts/recursive-pass.mjs` selects the highest-severity verified open finding, builds civ-engine run/pass manifests, and validates their repository-level completeness including source-state summaries. New manifests use `source-state-v2`; immutable `source-state-v1` rows from earlier harness revisions remain readable during reconciliation. `scripts/recursive-ledger.mjs` and `scripts/recursive-ledger-lock.mjs` own write-ahead paired persistence, atomic manifest creation, repair of an unterminated final JSONL fragment, token-checked heartbeat locks, dead-owner recovery, and one-pass intent reconciliation.
5. Each run keeps `run-manifest.json` and `pass-manifest.json`; aggregate run rows append to `output/recursive/ledger.jsonl` and pass rows append to `output/recursive/passes.jsonl`. Pending intents are deleted only after both rows are durably confirmed. Outcomes are `verified` or `run-failed` for run manifests and `no-fix-candidate`, `proposal-only`, or `run-failed` for pass manifests.

The Node boundary depends on the live sibling `civ-engine` through `file:../civ-engine`. `package-lock.json` records engine 2.2.0, and CI checks out commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` as that sibling, builds it under Node 22, asserts the imported version, then runs the Node contract tests and Python unit suite. The pass is scripted and proposal-only: no model provider, automatic source edit, apply arm, or auto-merge boundary is present.

## Recursive-loop tests

- `test/test_recursive_playtest.py` covers strict scenario/input validation, UUID-free checkpoint construction, latent-state observability, one transcript row per operation, and recorded-input replay.
- `test/test_recursive_oracles.py` covers cross-view topology and the remaining environment-contract oracle classes.
- `test/source-provenance.test.mjs`, `test/recursive-ledger.test.mjs`, `test/playtest-verify.test.mjs`, `test/recursive-pass.test.mjs`, and `test/playtest-recursive.test.mjs` cover local and linked-engine inventory, ignored-runtime mismatch rejection, start/end recapture, token-safe concurrent/crash reconciliation, torn-tail repair, exact fresh-process verification, strict evidence promotion, manifest contracts, public verifier retries, and end-to-end success/failure outcomes. `test/recursive-fixtures.mjs` supplies strict shared manifest fixtures without registering another test entry point.

## Rendering tests

- `test/test_game_clock.py` covers fixed cadence, clamp/drop behavior, pause/terminal consumption, and interpolation observer ordering.
- `test/test_render_layout.py` covers centered lanes, reverse-pair geometry, corner/loop metro projection, antialiased pixels, and cache invalidation/bounds.
- `test/test_game_renderer.py` covers lazy resources, layer order, metro interpolation, cached button fonts, and prepared game-over controls.
- `test/test_render_purity.py` renders real software surfaces and proves repeatable RGBA bytes, complete render-facing state and canonical-checkpoint purity, cache reuse, and rendered-versus-never-rendered trajectory equivalence.

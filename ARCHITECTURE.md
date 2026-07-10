python_mini_metro/
|- .github/
|  \- workflows/
|     \- test.yml
|- .vscode/
|  \- settings.json
|- docs/
|  \- threads/
|     |- README.md
|     |- current/
|     |  \- README.md
|     \- done/
|        |- README.md
|        |- agents-repo-fit/
|        \- full/
|- scripts/
|  |- fixtures/
|  |  \- recursive-playtest.json
|  |- playtest-recursive.mjs
|  |- playtest-verify.mjs
|  |- recursive-ledger.mjs
|  |- recursive-ledger-lock.mjs
|  |- recursive-pass.mjs
|  |- source-provenance-engine.mjs
|  \- source-provenance.mjs
|- src/
|  |- __init__.py
|  |- agent_play.py
|  |- config.py
|  |- env.py
|  |- main.py
|  |- mediator.py
|  |- recursive_checkpoint.py
|  |- recursive_oracles.py
|  |- recursive_playtest.py
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
|  |- test_geometry.py
|  |- test_graph.py
|  |- test_main.py
|  |- test_mediator.py
|  |- test_path.py
|  |- test_recursive_oracles.py
|  |- test_recursive_playtest.py
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
\- requirements.txt

## Runtime boundaries

- `src/env.py` remains the public Gym-like drive surface over `Mediator`; the recursive loop uses `MiniMetroEnv.reset(seed)` and `MiniMetroEnv.step(action, dt_ms)` without changing that API or driving the pygame GUI clock.
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

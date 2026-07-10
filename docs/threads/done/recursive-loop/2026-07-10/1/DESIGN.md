# Recursive self-improvement loop design

## Objective

Onboard `python_mini_metro` into the fleet recursive loop with the standard `npm run playtest:recursive` command and the full run -> evidence -> findings -> verify -> select -> fix -> rerun -> prove -> ledger contract. The loop is proposal-only at the command boundary; the driving agent remains the fix arm and must work any selected candidate to `fixed-proven`, `fix-unproven`, or a genuine user blocker.

## Existing foundation and gaps

`MiniMetroEnv.reset(seed)` plus `MiniMetroEnv.step(action, dt_ms)` is already a headless, scripted drive surface, and `src/agent_play.py` already offers in-memory action replay. The existing replay proof compares only final score, retains mutable action references, has no serialized inputs/transcript/checkpoints, and does not validate fleet manifests or findings. Entity IDs come from `shortuuid` and are not controlled by the environment seed, so raw structured observations cannot be compared across fresh processes. Equal-cost BFS routes also iterate a UUID-hashed neighbor set, which makes route choice nondeterministic across identical fresh drives.

## Architecture

### Python drive surface

Add `src/recursive_playtest.py` as a focused CLI/module over the existing public environment API; do not change `MiniMetroEnv` or `Mediator` signatures. A versioned scenario records a required integer seed, default `dtMs`, and an ordered non-empty operation list. Each operation records a stable name, JSON action, optional per-operation `dtMs`, and expected `actionOk` result.

Every drive writes an append-only run directory under `output/recursive/<run-id>/` containing `inputs.json`, `transcript.jsonl`, `findings.authored.json`, and a run result. The persisted input document records the source scenario path, seed, default timing, every exact operation, the selected Python executable/hash-seed context, and the run ID. There is exactly one transcript row per requested operation, including a deep-copied action, requested/effective timing, `actionOk`, reward, done, and a canonical checkpoint.

Canonical checkpoints replace all UUID relationships with encounter-order indices, convert enums/NumPy values to strict JSON, and include both normalized structured and arrays views plus simulation status, topology, passenger locations, travel plans, unlock/progression state, station spawn counters/intervals, metro motion/dwell state, and Python/NumPy RNG state needed to expose future divergence. JSON writes use `allow_nan=False`. The harness never drives the pygame GUI clock. Perturbation tests must prove that changing each latent-state family changes the checkpoint and civ-engine digest; two repeatable passes alone are not evidence that the checkpoint is complete.

Deterministic oracles run over each transcript row. The first required oracle cross-checks structured path station order against `arrays.path_station_indices`, producing stable class `observation-path-topology-mismatch`. Additional contract oracles cover expected action results, input/transcript cardinality, reward versus score delta, rejected-action mutation, paused time progression, terminal mutation, invalid references, and non-finite coordinates. All oracle findings are schema-valid `ImprovementFinding` JSON authored with `verificationStatus: "unverified"`, an addressed step reference where applicable, an explicit `data.class`, actionable routing, and a promotion target. No run-stage code may author `verified`.

### Deterministic foundation repairs

Change graph neighbor storage from an unordered set to insertion-ordered, deduplicated traversal and add a diamond-route tie-break regression. Deep-copy actions when the existing agent-play helper records them and add a mutation regression. These changes remove known replay hazards before the recursive command claims determinism.

### Node orchestration and civ-engine boundary

Add a minimal ESM `package.json` with only `civ-engine: "file:../civ-engine"`, a generated `package-lock.json`, and built-in Node test scripts. `scripts/playtest-recursive.mjs` owns stamped append-only run directories, spawns the Python runner with argument arrays and `shell: false`, calls the external verifier, validates manifests/findings through civ-engine 2.2.0, selects the highest-severity open fix-classified verified finding, writes `run-manifest.json` and `pass-manifest.json`, and appends validated compact rows to `output/recursive/ledger.jsonl` and `output/recursive/passes.jsonl`.

`scripts/playtest-verify.mjs` re-drives the recorded `inputs.json` in a second fresh Python process with the same explicit `PYTHONHASHSEED`. It computes civ-engine `stateDigest` values for every checkpoint and requires equal transcript length and full checkpoint-vector equality. Authored finding IDs and payloads are run-independent: verification requires an exact one-to-one match of the complete authored finding JSON from the original and replay drives, including claim text, severity, routing, disposition, data, and addressed step evidence. Only the replay-side mechanically re-derived finding is copied to `findings.verified.json` with `verificationStatus: "verified"`, `verificationMethod: "replay"`, and an added `{kind: "bundle", sessionId: <original-run-id>}` evidence ref, then strict-validated. Bug-class-only comparison is reserved for later cross-run prove-fixed checks through `improvementFindingSignature`. A checkpoint or semantic-finding mismatch emits a separate unverified nondeterminism finding and makes the pass `run-failed`; it is never tolerated as a flake or promoted.

`scripts/recursive-pass.mjs` contains pure candidate selection, outcome, and manifest construction. Selectable findings must pass strict validation, be verified, declare a stable class, use `autoFix`, `manualFix`, or `improveHarness`, and not be rejected or `wontFix`. Outcomes are exactly `no-fix-candidate | proposal-only | run-failed`.

Engine validation is necessary but not sufficient because the shared schema permits sparse manifests. A repo-level completeness validator requires every persisted run and pass manifest to carry `gameId`, objective, seed (or the explicit string `unavailable` when parsing failed before a seed existed), git commit, engine version, `costUsd: 0`, start/completion timestamps, duration, provider, stop reason, truthful existing-only artifacts, gates, tags, and outcome data. The implementation strict-validates and completeness-validates the in-memory object, the JSON file read back from disk, and every ledger row read back after append.

Every handled failure after orchestration starts, including missing/unparseable scenarios, subprocess spawn rejection, child nonzero exit, missing/unparseable artifacts, invalid engine payloads, and verification divergence, writes a complete `run-failed` run manifest plus pass manifest, appends exactly one attributable row to each ledger, and exits 1. Artifact lists include only files that exist and use repo-relative slash-normalized paths. Black-box tests run the real orchestrator with a nonexistent `PYTHON` executable and with an executable that exits nonzero, then assert exit 1, one new strict/read-back-valid failure row, and truthful artifacts.

### Dependency and CI discipline

Adding `package.json` triggers the repository dependency-change protocol. Generate and commit `package-lock.json`; regenerate `requirements-locked.txt` with hashes from the existing Python requirements; run `npm audit` and `pip-audit -r requirements-locked.txt --disable-pip`; and record zero-vulnerability results. The mandatory live sibling `file:../civ-engine` link has no registry integrity hash, so the design documents that fleet-required exception while keeping all registry-resolved Python dependencies hash-pinned.

Update CI to follow the established fleet sibling pattern: explicitly checkout this repository to `$GITHUB_WORKSPACE/python_mini_metro` and `yanfengliu/civ-engine` to `$GITHUB_WORKSPACE/civ-engine`, pin civ-engine to commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, configure Node 22 (satisfying Node >=20), build the engine, install this repo's Node dependencies from the lock, assert imported `ENGINE_VERSION === "2.2.0"`, install Python dependencies from the hashed lock, and run both Node loop-contract tests and the existing Python suite from the repository subdirectory. Local commands remain configurable through `PYTHON`; committed code does not hardcode a machine-specific interpreter.

### Evidence retention and documentation

Add `/output/`, `/node_modules/`, Python caches, and tool caches to `.gitignore`; recursive evidence is never committed. Update `README.md` with setup, command, artifacts, outcomes, and fix-arm expectations; `ARCHITECTURE.md` with the new boundary/data flow; `GAME_RULES.md` with deterministic equal-cost route tie-breaking; and `PROGRESS.md` with one dated completion bullet. Preserve the pre-existing untracked `.agents/` directory and never stage it.

## Acceptance drill

1. Run two consecutive default `npm run playtest:recursive` passes on the unchanged build. Both must exit 0, strict-validate every manifest, report successful full-vector fresh-process verification, and have no fix candidate.
2. Temporarily inject a one-line observation defect by reversing `structured.paths[*].station_ids` while leaving the arrays view unchanged. Run the default pass and require a mechanically verified `observation-path-topology-mismatch` candidate with `proposal-only` outcome. The injected defect is temporary working-tree state and is never committed.
3. While the defect is still present, add the promoted cross-view topology regression to `test/test_env.py` and run it red. Restore correct station order, rerun the regression green, then rerun the pass and prove the class absent at bug-class granularity.
4. Run a deliberately unparseable scenario, a nonexistent-Python spawn failure, and a child nonzero exit. Each must exit 1 and append exactly one attributable, complete, strict/read-back-valid `run-failed` run row and pass row with truthful existing-only artifacts.
5. Confirm the original authored-finding artifact contains no finding born verified, while any verified finding has strict method and addressed replay evidence.

## Boundaries

The default run is deterministic and scripted; `loop-ops/DIRECTIVES.md` currently keeps LLM exploration locked, so onboarding adds no model provider or autonomous apply arm. This task builds and proves the repo-local loop but does not edit the sibling `loop-ops` repository or activate `python_mini_metro` in its scheduled shift table.

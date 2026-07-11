# Final diff summary

## Intent

Make fresh player-pixel training optimize total passenger deliveries with longer visual history and learned episode memory, preserve legacy feed-forward PPO compatibility, and document the model-selection evidence across CNN, recurrent, Transformer/ViT, and world-model alternatives.

## Implementation

- Fresh runs resolve to `recurrent_ppo`, eight stacked RGB frames, `CnnLstmPolicy`, separate one-layer 256-unit actor/critic LSTMs, `gamma=1.0`, `gae_lambda=0.99`, and recurrent batch size 64. Feed-forward PPO remains an explicit algorithm/frame-stack ablation with its legacy estimator and preferred batch-size contract.
- `src/rl/dependencies.py` isolates optional imports; `src/rl/policy.py` owns algorithm configuration and model construction/loading; `src/rl/training.py` retains compatibility re-exports while focusing on vector environments, callbacks, task reconstruction, and fingerprints.
- Custom evaluation threads recurrent state and episode-start masks. Horizon-truncated terminal observations reach RecurrentPPO value bootstrapping. Evaluation reports game-over/truncation counts and rates, right-censoring, and delivery totals conditional on game over.
- Resume inherits saved algorithm/frame stack and rejects explicit mismatches. Authenticated pre-recurrent PPO artifacts require the existing training/runtime drift opt-ins when applicable and load through the legacy PPO dispatch. Legacy callback callers retain `mini_metro_ppo_*` checkpoint names.
- SB3-Contrib 2.9.0 is pinned, hash-locked, audited, and tracked in both runtime provenance lists. Windows CI exercises recurrent and legacy fresh/resume/evaluate paths.
- `docs/rl-model-selection.md` recommends the integrated CNN-LSTM lane, identifies DreamerV3 `size12m` as the research-grade world-model candidate, defers pure ViT/GTrXL pending task evidence, prioritizes a conditional pointer head, and defines seed-level/cluster-aware evaluation practice.

## Findings already fixed

- Added a direct timeout-bootstrap regression, not only a terminal-stack shape assertion.
- Added aggregate censoring semantics instead of labeling horizon partial totals as final game-over deliveries.
- Corrected statistical guidance so trained runs/seeds are the top-level independent units.
- Restored the legacy callback default to PPO naming.
- Added composed pre-recurrent artifact drift/authentication/load coverage.
- Split the 630-line training module into focused files under 500 lines.
- Replaced the recurrent batch-256 candidate after profiling: one local 8-env x 128-step run peaked at 3.909 GiB process-tree RSS and took 24.111 seconds; current batch 64 peaked at 3.030 GiB and took 17.030 seconds. This is documented as a single-machine result.
- Made unknown termination metadata explicitly indeterminate instead of allowing an all-game-over interpretation, and split the oversized RL integration test into a CI-covered legacy compatibility module.

## Validation completed before external review

- Exact locked RL environment: 316/316 Python unit tests passed with no skips.
- Current-code recurrent fresh/evaluate/resume/evaluate and legacy PPO fresh/evaluate/resume/evaluate lifecycles passed.
- The recurrent manifest records eight frames and batch 64; legacy resume inherits PPO/four frames; all short evaluations report horizon censoring.
- Full-default 8-env x 128-step recurrent rollout passed; process-tree memory was profiled.
- Both hashed dependency locks passed `pip-audit -r ... --disable-pip` with no known vulnerabilities; the RL environment passed `pip check`; `npm audit` reported zero vulnerabilities.
- Full-repo Ruff/format, changed-file pre-commit hooks, workflow YAML parsing, and product-diff whitespace checks passed; verbatim raw CLI captures retain their original whitespace by thread policy.
- Live `npm test` is affected by an unrelated sibling `civ-engine` drift (live 2.4.1 versus the repository's 2.2.0 pin); the pinned shadow acceptance layout passed 41/41. No Node source changed in this task.

## Review scope

Review all live changed and new files, especially `src/rl/dependencies.py`, `src/rl/policy.py`, `src/rl/training.py`, `src/rl/evaluation.py`, both RL scripts, RL tests, requirements/lock/provenance, Windows CI, README/architecture/progress, and `docs/rl-model-selection.md`. New untracked files do not appear in plain `git diff`, so read them explicitly.

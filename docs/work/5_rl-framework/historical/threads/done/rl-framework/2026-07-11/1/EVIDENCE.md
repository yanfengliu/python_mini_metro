# Verification evidence

## Behavior and lifecycle

| Check | Result |
| --- | --- |
| Fresh default manifest | `algorithm=recurrent_ppo`, `frameStack=8`, `policy=CnnLstmPolicy`, separate 256-unit one-layer actor/critic LSTMs, `gamma=1.0`, `gae_lambda=0.99`, `batch_size=64` |
| Recurrent lifecycle | Fresh train, authenticated evaluation, resume without repeating algorithm/frame stack, and resumed authenticated evaluation all passed on CPU |
| Feed-forward lifecycle | Explicit PPO/four-frame fresh train, authenticated evaluation, inherited PPO/four-frame resume, and resumed evaluation all passed |
| Pre-recurrent evaluation | A synthesized historically shaped PPO manifest with an authenticated real PPO zip failed with neither or only one drift override and evaluated successfully only with both training/runtime opt-ins |
| Genuine pre-recurrent resume | The authenticated July 10 `output/rl/final-fresh` PPO/four-frame artifact, whose runtime predates SB3-Contrib and whose trainer fingerprint predates the module split, resumed and evaluated successfully with `--allow-training-drift --allow-runtime-drift`; the child manifest contains both cross-drift tags, `resumed-training`, and both parent digests |
| Recurrent timeout target | The integration test spies on `predict_values`, verifies the 24-channel terminal frame stack and non-episode-start critic state reach RecurrentPPO, forces terminal value 5, and confirms the gamma-1 rollout reward includes the bootstrap |
| Evaluation memory | Feed-forward and recurrent fakes verify state threading plus episode-start masks `[True], [False], [True], [False]`, preventing cross-game state leakage |
| Evaluation reporting | Short-horizon recurrent and PPO evaluations report one horizon truncation, zero game overs, `primaryMetricCensored=true`, `primaryMetricComplete=false`, complete termination metadata, and no conditional game-over mean |

## Resource evidence

The fast profile's 8 environments x 128 steps x 24 x 108 x 192 raw `uint8` observations are exactly 486 MiB. A single local CPU rollout using the former recurrent batch-256 candidate completed in 24.111 seconds, reported 242 rollout FPS, and peaked at 3.909 GiB process-tree RSS. The implemented batch-64 configuration completed in 17.030 seconds, reported 329 FPS, and peaked at 3.030 GiB. These are single-machine engineering measurements, not general performance claims. The final recurrent policy has 1,478,933 trainable parameters.

## Final gates

| Gate | Command or surface | Result |
| --- | --- | --- |
| Full Python suite | `py313` with the exact-lock environment on `PYTHONPATH`, `python -m unittest -v` | 316/316 passed, no skips |
| Focused changed RL tests | `test.test_rl_cli test.test_rl_legacy_compat test.test_rl_training` | 23/23 passed |
| Full lint | `python -m ruff check .` | Passed |
| Full format | `python -m ruff format --check .` | 97 files passed |
| Hook parity | `python -m pre_commit run --files ...` in a fresh isolated cache | YAML, EOF, whitespace, Ruff, and Ruff format passed after the EOF hook added one missing newline to a prompt artifact; verbatim raw CLI captures were intentionally excluded from mutating hooks |
| Workflow syntax | PyYAML load of `.github/workflows/test.yml` | Passed |
| RL dependency integrity | Exact hashed RL lock installed into ignored `output/venv-rl`; `python -m pip check` | No broken requirements |
| RL vulnerability audit | `pip-audit -r requirements-rl-locked.txt --disable-pip` | No known vulnerabilities found |
| Core vulnerability audit | `pip-audit -r requirements-locked.txt --disable-pip` | No known vulnerabilities found |
| Node dependency audit | `npm audit --audit-level=low` | 0 vulnerabilities |
| Product diff whitespace | `git diff --cached --check -- . ':(exclude)docs/threads/done/rl-framework/2026-07-11/1/raw/**'` | Passed after final synthesis |
| Verbatim raw evidence | Whole-staged `git diff --cached --check` | Reports original trailing spaces in `raw/plan-codex.stdout.log`; retained intentionally because thread policy requires raw CLI output to remain verbatim |

## Known unrelated Node baseline

The live sibling `civ-engine` is version 2.4.1 while this repository pins 2.2.0, so live `npm test` fails the provenance/contract baseline for that external-state mismatch. The unchanged pinned shadow acceptance layout at `output/postcommit-clean-acceptance-20260710-235900/python_mini_metro` ran 41/41 Node tests successfully against `civ-engine` 2.2.0. No Node source or dependency declaration changed in this task.

## Research sources

The model-selection note grounds the recommendation in the PPO and GAE papers, official SB3/SB3-Contrib guidance, IMPALA, the RL-specific ViT evaluation, GTrXL, Memory Gym, DreamerV3 and its official size presets, Decision Transformer, Deep RL That Matters, Empirical Design in Reinforcement Learning, and statistical-precipice/rliable guidance. The integrated recommendation is eight-frame CNN-LSTM RecurrentPPO; DreamerV3 `size12m` is the research-grade world-model lane; a conditional pointer head is the next task-specific architectural experiment; pure ViT or temporal Transformer replacement is deferred pending matched evidence.

# Game maturity evidence

## Baseline snapshot - 2026-07-11

- Git: `main` equaled `origin/main` at `7d5304ad79b6054f85a1c48f3c1bc0b2475bf9fd`; tracked files were clean and only `.agents/` was untracked.
- Exact RL environment: `output/venv-rl/Scripts/python.exe -m unittest -v` passed 316/316 tests with no skips in 7.389 seconds.
- Dependency integrity: `output/venv-rl/Scripts/python.exe -m pip check` reported no broken requirements.
- Core environment: `C:/Users/38909/miniconda3/envs/py313/python.exe -m unittest -v` passed 316 tests with 8 expected optional-RL skips.
- Static checks: full-repo Ruff passed; Ruff format reported all 97 files formatted.
- Entrypoint: `src/main.py` completed a two-frame dummy-video-driver smoke successfully.
- Remote: GitHub Actions run `29170436131` passed the build and RL smoke jobs on the baseline commit.
- Local recursive tooling: `npm test` passed 22/41 and failed 19/41 because the live linked civ-engine reports 2.4.1 while `package-lock.json` and the provenance contract pin 2.2.0. Pinned CI passed; this is isolated external dependency drift, not a gameplay failure.
- Current RL artifacts are smoke/profile/compatibility runs only. The largest local manifest requests 1,024 timesteps with a four-decision episode horizon; no artifact is evidence of competent play.
- Size audit: `src/mediator.py` is 1,082 lines and `test/test_mediator.py` is 1,139 lines, both above the 1,000-line hard ceiling.
- Rules drift: code uses a 900-step passenger-spawn base randomized to 70-130 percent, while `GAME_RULES.md` states a 600-step base and 7-13 seconds.
- Objective drift: line purchases subtract `Mediator.score`, the HUD/game-over overlay render that remainder as score, and lifetime deliveries are separately stored in `total_travels_handled`.
- History design: 16 contiguous frames would cover only 1.5 seconds at 1x while raising the raw 8-environment x 128-step rollout payload from 486 MiB to 972 MiB; 32 contiguous frames would cover 3.1 seconds at roughly 1.90 GiB. The proposed 12-frame multiscale candidate covers anchors through 12.8 seconds for a 729 MiB raw rollout and keeps all eight current recent frames.
- Overload baseline: the exact command, seeds, route, horizon, output, and limitations are retained in `THRESHOLD_BASELINE.md`. An independently rerun 12-seed fixed-route comparison used the real deterministic 17/17/16 ms cadence and ended all 36 runs naturally. Threshold 1 produced median 16.0 deliveries and 95.47 seconds; threshold 2 produced 19.5 and 108.15 seconds; threshold 3 produced 22.5 and 118.61 seconds. This isolates the overdue-passenger threshold under one scripted route and is directional evidence only, not final human or learned-policy balance proof.

## Evidence format for future increments

For each GM increment append: changed contracts, focused red/green tests, full local gate commands and counts, resource or visual evidence when applicable, adversarial findings and dispositions, commit SHA, push result, remote workflow URL/result, and the next resume cursor.

## GM-00 Commit A - persistent reviewed plan

- Commit: `16a0e73f3becafacaf8b903530a4801c949f7434` (`docs: persist game maturity roadmap [GM-00:A]`).
- Push: `origin/main` advanced from `7d5304a` to `16a0e73`.
- Remote workflow: [run 29172923371](https://github.com/yanfengliu/python_mini_metro/actions/runs/29172923371) succeeded; `build` passed in 30 seconds and `rl-smoke` passed in 2 minutes 41 seconds.
- Review: external Codex found three High and seven Medium plan defects; all were fixed. Three independent in-process re-review lanes approved the final plan. External Claude and targeted Codex re-review limitations are recorded in `REVIEW.md`.
- Commit B purpose: durably record this evidence, mark GM-00 complete, and queue GM-01a behind Commit B's own CI.

## GM-00 Commit B - remote finalization

- Commit: `0411e68f1a4fa83e6777480059ce5dce80a82774` (`docs: finalize game maturity roadmap [GM-00:B]`).
- Push: `origin/main` advanced from `16a0e73` to `0411e68`.
- Remote workflow: [run 29173071970](https://github.com/yanfengliu/python_mini_metro/actions/runs/29173071970) succeeded; `build` passed in 34 seconds and `rl-smoke` passed in 2 minutes 39 seconds.
- Outcome: GM-00 is the last remotely finalized work unit and GM-01a began from this exact baseline.

## GM-01a Commit A - canonical semantics and persisted compatibility

- Runtime contracts: lifetime `deliveries` and spendable `line_credits` are independent canonical mediator fields; delivery increments both and line purchase spends only credits. Writable `total_travels_handled` and `score` aliases preserve old callers.
- Reward contracts: structured `MiniMetroEnv` defaults to delivery delta and exposes explicit `line_credits_delta` legacy mode; both modes fail closed on invalid mutation. Pixel learning reads canonical fields while retaining terminal-metrics-v1 `display_score` bytes.
- Persisted contracts: agent-play v2 names per-step/final deliveries, line credits, effective timestep, and reward contract while retaining old currency returns/fields. Checkpoint v2 records explicit counters, reward mode, reward baselines, and overdue-threshold alias; v1 normalization and emission are fail-closed. Recursive input v1 reconstructs credit-delta rewards and strict v2 requires `deliveries`.
- Fresh-process evidence: the checked-in recursive fixture now uses v2 delivery reward. Targeted Node verifier tests passed 5/5, public verifier v1/v2 tests passed 2/2, a generated v2 drive reverified all eight checkpoint digests, and an independent adversarial probe reverified a genuine pre-change v1 artifact exactly across checkpoints, transcript fields, findings, and inputs.
- TDD evidence: the initial semantic tests produced 3 failures and 5 errors across 84 focused tests before canonical fields/modes existed; recursive tests initially failed imports for the new schema symbols; privileged snapshot tests initially failed on missing canonical fields. The merged focused Python surface later passed 150/150 before the organization-only split, and the final recursive split surface passed 27/27.
- Full Python gates: `C:/Users/38909/miniconda3/envs/py313/python.exe -m unittest -v` and the concise repeat passed 341 tests with 8 expected optional-RL skips; `output/venv-rl/Scripts/python.exe -m unittest -v` and the concise repeat passed 341 tests with no skips.
- Static/hook gates: full-repo Ruff check passed; full-repo Ruff format reported all 99 files formatted; changed-file pre-commit hooks passed for all 26 files (`end-of-file-fixer`, trailing whitespace, Ruff, Ruff format). A two-frame dummy-video `src/main.py` smoke passed.
- Node boundary: full `npm test` passed 23/42 and the same 19 tests failed only because the live linked civ-engine is 2.4.1 while the repository pins 2.2.0. The two changed verifier paths pass locally, and pinned CI remains the authoritative full Node gate until GM-04 installs an isolated local pin.
- Size guard: extraction of `src/recursive_contract.py` and `test/test_recursive_checkpoint.py` leaves the five touched recursive source/test modules at 192, 498, 407, 208, and 386 lines. The pre-existing oversized mediator and mediator test remain explicitly owned by GM-03.
- Adversarial review: three independent live-code lanes converged on APPROVED after all High/Medium findings in iteration `2/REVIEW.md` were fixed. Multi-CLI transfer remained unavailable under the environment policy already recorded in GM-00; no bypass was attempted.
- Commit: `5e0076318b87b745e8f6ad75586b4c1ff24989ee` (`feat: make passenger deliveries canonical [GM-01a:A]`).
- Push: `origin/main` advanced from `0411e68` to `5e00763`.
- Remote workflow: [run 29175325493](https://github.com/yanfengliu/python_mini_metro/actions/runs/29175325493) succeeded; both `build` and `rl-smoke` passed, including the pinned 42-test Node boundary, clean recursive pass, Python suite, RL contracts, and recurrent/legacy PPO smoke.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-01a complete pending B's own CI, and queue GM-01b behind that remote gate.

## GM-01a Commit B - remote finalization

- Commit: `6c77033fa2af9d1a1913135f7da3d27b7ff4f2a5` (`docs: finalize canonical delivery semantics [GM-01a:B]`).
- Push: `origin/main` advanced from `5e00763` to `6c77033`.
- Remote workflow: [run 29175470189](https://github.com/yanfengliu/python_mini_metro/actions/runs/29175470189) succeeded; both `build` and `rl-smoke` passed.
- Outcome: GM-01a is remotely finalized and GM-01b began from this exact baseline.

## GM-01b Commit A candidate - objective presentation and verified cadence

- Presentation contract: the HUD now names lifetime `Passengers Delivered` and spendable `Line Credits` separately. Game over presents deliveries first and remaining credits second, while retaining canonical-first legacy fallbacks and the deprecated private `_draw_score` wrapper.
- Geometry and visual evidence: overlay content flows above unchanged prepared input rectangles and is regression-tested for horizontal and vertical containment at 1920x1080 and 800x600. Matching deterministic seed-42 before/after captures with 23 deliveries and 4 credits are checked in under iteration `3/visual/`; each PNG is 46 KiB or less.
- Cadence contract: a new 141-line focused test module pins the 900-step base, inclusive 630-1,170 per-station sampling, sample-once state, first-update attempts at 1x/2x/4x, reset after a due full-station attempt, 15-second speed-invariant simulated cadence, and the 1,170-step 4x quantized endpoint at wall tick 293.
- TDD evidence: the initial renderer run failed with one assertion failure and four missing-method errors because the old surface rendered only `Score`/`Final Score`; after implementation and review fixes the combined renderer/cadence surface passed 19/19.
- Fingerprint boundary: protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`; the default task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`; environment content intentionally changed from `390a9fbbd60b479b2957f89c99b5c01f699836a0bd2ecf8bc80de01591f50682` to `feb81d5d64e8304318c54cffc44cc105d6c16e9ef06cbe24c45d9ba3f01958cf`.
- Compatibility boundary: terminal-metrics v1 remains exactly `{deliveries, display_score, seed, simulation_time_ms}`, with `display_score` still meaning remaining line credits. No RL protocol, task, reward, manifest, checkpoint, or persisted schema changed.
- Full Python gates: the final core `python -m unittest -v` passed 352 tests with 8 expected optional-RL skips; the exact `output/venv-rl` environment passed 352/352 with no skips.
- Static and app gates: full-repo Ruff check passed; full-repo Ruff format reported all 100 Python files formatted; `git diff --check` passed; a two-frame dummy-video `src/main.py` smoke passed.
- Node baseline: full local `npm test` passed 23/42 and the same 19 tests failed because the linked civ-engine is 2.4.1 while the repository pin is 2.2.0. No Node file changed; pinned CI remains authoritative until GM-04.
- Adversarial review: three independent live-code lanes found no High or Medium defect. Four Low gaps were fixed and all three lanes re-approved with no remaining finding; raw output and synthesis are under iteration `3/`.
- Changed-file pre-commit passed after explicit user approval for its normal cache: check-yaml had no applicable file, and end-of-file, trailing-whitespace, Ruff check/fix, and Ruff format all passed without modifying source.

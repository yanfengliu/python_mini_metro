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

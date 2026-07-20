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
- Commit: `3523ea412a044d3a4c5f3dd43da913c736d78ed9` (`feat: clarify passenger objective and cadence [GM-01b:A]`).
- Push: `origin/main` advanced from `6c77033` to `3523ea4`.
- Remote workflow: [run 29177705475](https://github.com/yanfengliu/python_mini_metro/actions/runs/29177705475) succeeded; `build` passed in 36 seconds and `rl-smoke` passed in 2 minutes 53 seconds.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-01b complete pending B's own CI, and queue GM-01c behind that remote gate.

## GM-01b Commit B - remote finalization

- Commit: `18ef714badc510df044198381d80e22aa3bf0c09` (`docs: finalize objective presentation and cadence [GM-01b:B]`).
- Push: `origin/main` advanced from `3523ea4` to `18ef714`.
- Remote workflow: [run 29177848669](https://github.com/yanfengliu/python_mini_metro/actions/runs/29177848669) succeeded; `build` passed in 33 seconds and `rl-smoke` passed in 2 minutes 53 seconds.
- Outcome: GM-01b is remotely finalized. GM-01c starts from this exact baseline with the threshold and persisted-replay migration contract in iteration `4/PLAN.md`.

## GM-01c candidate - threshold and persisted replay migration

- TDD red: runtime coverage ran 10 tests with 4 failures and 3 errors; recursive v3 coverage ran 7 tests with 2 failures and 5 errors; agent-play v3 coverage ran 7 tests with 16 subtest failures and 3 errors. All failures were attributable to the absent canonical default or v3 routing, while explicit historical threshold-one characterization remained green.
- Focused green: the final combined runtime, pixel termination, recursive v1/v2/v3, agent-play v1/v2/v3, and checkpoint surface passed 55/55 after review regressions were added.
- Persisted compatibility: recursive and agent-play formats retain immutable v1/v2/v3 identifiers. V1/v2 reconstruct threshold `1`; v3 records a strict positive non-boolean threshold and applies it after reset. Recursive scenario v1 maps to checkpoint v1, while v2/v3 map to checkpoint v2. The default fixture is v3 and a checked-in literal v2 fixture remains available for fresh-process verification.
- Node boundary: verifier unit tests passed 6/6, literal-v2 public replay passed 1/1, and a direct v3 fresh-process replay matched inputs, findings, and all eight checkpoint digests. Full local `npm test` passed 25/44 and failed exactly the same 19 civ-engine 2.4.1-versus-pinned-2.2.0 cases; pinned CI remains authoritative.
- Balance evidence: the 12-seed thresholds 1/2/3 aggregates reproduced exactly, and default threshold two matched explicit threshold two on all 12 seeds. This remains directional fixed-route evidence only.
- Fingerprints: protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`; task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`; environment content intentionally changes from `feb81d5d64e8304318c54cffc44cc105d6c16e9ef06cbe24c45d9ba3f01958cf` to `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60`.
- Full gates: core and exact-RL suites passed 377 tests (8 expected optional-RL skips only in core); full Ruff and format passed across 103 Python files; `git diff --check` and the two-frame dummy-video app smoke passed.
- Changed-file pre-commit passed across the complete GM-01c file set: end-of-file, trailing-whitespace, Ruff check/fix, and Ruff format hooks made no source changes; the YAML hook had no applicable file.
- Adversarial review: one HIGH strict-v3 defect, one MEDIUM fail-open capability defect, and one MEDIUM stale-cursor defect were independently confirmed and fixed. Three in-process lanes and the targeted Opus fallback approved the final diff. Fable hit its usage limit, Codex CLI failed twice with HTTP 401, and Opus could not execute shell gates; raw output and compensating driver verification are under iteration `4/`.

## GM-01c Commit A - threshold and persisted replay migration

- Commit: `648025f299adec6fb907357339310923d375c4f4` (`feat: raise overdue passenger threshold [GM-01c:A]`).
- Push: `origin/main` advanced from `18ef714` to `648025f`.
- Remote workflow: [run 29180986088](https://github.com/yanfengliu/python_mini_metro/actions/runs/29180986088) succeeded; `build` passed in 35 seconds, including all 44 Node tests against pinned civ-engine 2.2.0 plus the clean recursive pass and Python suite, and `rl-smoke` passed in 2 minutes 44 seconds.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-01c complete pending B's own CI, and keep GM-02 behind that remote gate.

## GM-01c Commit B - remote finalization

- Commit: `14050af71df5c6cad8035904da467959767f68bb` (`docs: finalize overdue passenger threshold [GM-01c:B]`).
- Push: `origin/main` advanced from `648025f` to `14050af`.
- Remote workflow: [run 29181130841](https://github.com/yanfengliu/python_mini_metro/actions/runs/29181130841) succeeded; `build` passed in 39 seconds and `rl-smoke` passed in 2 minutes 43 seconds.
- Outcome: GM-01c is remotely finalized. GM-02 starts from this exact baseline with the long multiscale frame-history migration.

## GM-02a local implementation evidence

- Contract: fresh training-manifest v2 stores a canonical history descriptor, derived `frameStack`, and independently recomputed `historyFingerprint`; canonical manifest-v1 bytes remain exact and derive arbitrary positive contiguous offsets in memory. Until GM-02c, train/evaluate reject non-contiguous v2 history before artifact opening and fresh runtime remains eight-contiguous.
- TDD: descriptor import failed red before `src/rl/history.py`; manifest-v2/v1 tests failed red before schema migration; train/evaluate ordering tests reached artifact opening red before guards. Focused post-fix coverage reached 42/42, then final finder-fix probes passed 3/3.
- Full Python: core `python -m unittest` passed 389 tests with 8 expected optional-RL skips; `output/venv-rl/Scripts/python.exe -m unittest` passed 389/389 with no skips.
- Static/hooks/app: changed-file Ruff check and format passed for 11 Python files; pre-commit passed EOF, whitespace, Ruff, and Ruff format for every intended file; dummy-video `src/main.py` completed two frames. One initial app-smoke attempt used the wrong frame-limit variable and was terminated before rerunning successfully with `PYTHON_MINI_METRO_MAX_FRAMES=2`.
- Artifact smokes: a fresh 128-step recurrent run emitted/evaluated manifest v2 with eight contiguous offsets and history fingerprint `c68f2aeaea62e36cff4d9ab96d73eb02881028d01e50b74267da8a36da2f16b1`. A genuine on-disk v1 recurrent artifact evaluated with explicit historical drift opt-ins and resumed for 128 steps into v2 with authenticated parent manifest/model SHA-256 values and the same derived history identity.
- Fingerprints: protocol `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, default task `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and content `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60` remained unchanged; trainer identity intentionally changed to `cb0e6e0f679afb2677760e964aa8acc9adf728548b2128671da0417aee782686`.
- Review: all three plan lanes approved after corrections. Implementation finders were clean except a medium allowlist-mutation test gap and low v2 top-level exact-key gap; both were fixed, approved by the finder, and independently verified. External Codex/Claude review was unavailable because the platform denied repository-context export to Claude; no bypass was attempted.
- Node boundary: local `npm test` remained at 25/44 with the same 19 failures caused by live civ-engine 2.4.1 versus pinned 2.2.0. The three public verifier compatibility cases passed. Pinned CI remains authoritative until GM-04 supplies an isolated local engine.

## GM-02a Commit A - remote implementation gate

- Commit: `bab6b15442b0f23303e87667668b9d35df7c9552` (`feat: bind RL observation history identity [GM-02a:A]`).
- Push: `origin/main` advanced from `14050af` to `bab6b15`.
- Remote workflow: [run 29207490781](https://github.com/yanfengliu/python_mini_metro/actions/runs/29207490781) succeeded; `build` passed in 36 seconds, including all 44 Node tests against pinned civ-engine 2.2.0 plus the clean recursive pass and Python suite, and `rl-smoke` passed in 2 minutes 47 seconds including fresh recurrent and legacy PPO artifact paths.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-02a complete pending B's own CI, and keep GM-02b behind that remote gate.

## GM-02a Commit B - remote finalization

- Commit: `ab8e6eb1d9a4006b514d113e6ad2b93c3f6d9b48` (`docs: finalize RL history identity [GM-02a:B]`).
- Push: `origin/main` advanced from `bab6b15` to `ab8e6eb`.
- Remote workflow: [run 29207697382](https://github.com/yanfengliu/python_mini_metro/actions/runs/29207697382) succeeded; `build` passed in 34 seconds and `rl-smoke` passed in 2 minutes 37 seconds.
- Outcome: GM-02a is remotely finalized. GM-02b starts from this exact baseline with the bounded vectorized temporal-history ring.

## GM-02b local implementation evidence

- Contract: `VecTemporalHistory` stores one isolated `(max_offset + 1)` `uint8` ring per vector slot, samples exact oldest-to-newest offsets into owned channel-first outputs, constructs an ending-episode terminal stack before clearing an auto-reset slot, and requires a clean reset after any reset/consumed-step failure. Train/resume/evaluate remain honestly on contiguous `VecFrameStack` until GM-02c integrates all paths.
- TDD: the wrapper import initially failed red; later fail-closed expansion produced 13 expected failures for stale-state continuation and constructor cleanup; a forced reset-output `MemoryError` then failed because the wrapper became initialized. Each defect was implemented only after its red regression, and final focused wrapper plus fingerprint coverage passed 8/8.
- Exact lifecycle/resource coverage: chronology is byte-pinned through decision 130 and offset-128 wraparound; staggered termination/truncation, zero pre-history, repeated reset, retained output ownership, malformed terminal/batch/metadata poisoning, and N=1/4/8/13 SB3 equivalence pass. The eight-slot candidate ring is exactly 64,198,656 bytes with output space `(36, 108, 192)` and a 5,971,968-byte vector output.
- Full Python: core `python -m unittest -v` passed 395 tests with 8 expected optional-RL skips; `output/venv-rl/Scripts/python.exe -m unittest -v` passed 395/395 with no skips.
- Static/hooks/app: changed-file Ruff check and format, `git diff --check`, and changed-file pre-commit all passed; dummy-video `src/main.py` completed two frames.
- Fingerprints: protocol `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, default task `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and content `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60` remain unchanged; trainer identity intentionally changes from `cb0e6e0f679afb2677760e964aa8acc9adf728548b2128671da0417aee782686` to `a435f8d354967880e29bedd525f6ca48faced801ac4eed3f469aa82e23f765d8`.
- Adversarial review: three independent lanes found and refuted pre-reset dispatch, stale history after consumed invalid data, reset-assembly initialization, resource accounting, cleanup, and stale docs. Every confirmed finding was fixed test-first; real Dummy/VecMonitor, 36-channel RecurrentPPO timeout bootstrap, and spawned two-slot Subproc/VecMonitor probes passed, and all lanes returned clean. External Codex/Claude review remains unavailable because the platform denied repository-context export to Claude; no bypass was attempted.
- Node boundary: local `npm test` reproduced the known 25/44 result with the same 19 civ-engine 2.4.1-versus-pinned-2.2.0 failures; pinned CI remains authoritative until GM-04 supplies an isolated local engine.

## GM-02b Commit A - remote implementation gate

- Commit: `a5744c0e97832b296f5a02cef7fa40317d11f1e4` (`feat: add vectorized temporal history [GM-02b:A]`).
- Push: `origin/main` advanced from `ab8e6eb` to `a5744c0`.
- Remote workflow: [run 29209101298](https://github.com/yanfengliu/python_mini_metro/actions/runs/29209101298) succeeded; `build` passed in 41 seconds, including all 44 Node tests against pinned civ-engine 2.2.0 plus the clean recursive pass and 395-test Python suite, and `rl-smoke` passed in 2 minutes 42 seconds including the exact temporal-history and recurrent artifact paths.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-02b complete pending B's own CI, and keep GM-02c behind that remote gate.

## GM-02b Commit B - remote finalization

- Commit: `53bc5105099d6347078bd9fd2574d875b9d6d4d3` (`docs: finalize vectorized temporal history [GM-02b:B]`).
- Push: `origin/main` advanced from `a5744c0` to `53bc510`.
- Remote workflow: [run 29209297952](https://github.com/yanfengliu/python_mini_metro/actions/runs/29209297952) succeeded; `build` passed in 37 seconds and `rl-smoke` passed in 2 minutes 38 seconds.
- Outcome: GM-02b is remotely finalized. GM-02c starts from this exact baseline with descriptor-driven train/resume/evaluate integration.

## GM-02c local implementation evidence

- Contract: CLI controls resolve to one immutable `HistoryDescriptor`; `--frame-stack N` exclusively means arbitrary contiguous history and reviewed multiscale names use mutually exclusive `--history-layout`. Fresh omission remains contiguous eight, resume omission inherits the exact authenticated v1/v2 history, and evaluation accepts no reinterpretation override. Train, callback evaluation, resume, final evaluation, manifest persistence, and evaluation JSON all consume/report that descriptor through `base -> VecMonitor -> VecTemporalHistory`.
- TDD: the first 16-test integration slice produced the expected missing-constant/import, missing-helper/parser, unsupported `history=` builder, old `VecFrameStack`, temporary guard, and resolver-order failures (2 failures and 10 errors). Production changes followed those red contracts. The reviewer then replaced the fake episode-mask coverage with a real red/green RecurrentPPO rollout probe; final focused history/CLI/runtime/legacy coverage passed 59/59.
- Full Python: core `python -m unittest -v` passed 399 tests with 11 expected optional-RL skips; `output/venv-rl/Scripts/python.exe -m unittest -v` passed 399/399 with no skips.
- Runtime mechanisms: named twelve-frame history passed real two-slot spawned Subproc construction, terminal/truncation stacks, RecurrentPPO timeout bootstrap at 36 channels, `[[True], [False], [True]]` rollout masks, short learn/save/in-memory-load/predict, and model observation-space rejection before rollout. The repeatable legacy test explicitly creates a four-frame model through old `VecFrameStack` and evaluates it through the new ring.
- Named persisted lifecycle: a two-worker `decision-history-v1` fresh/evaluate/resume-without-selector/evaluate smoke preserved offsets `[128,64,32,16,7,6,5,4,3,2,1,0]` and history fingerprint `02138fee74a6e369029b2802f7d73302531ed8b29ded818bfd77d74d790ff450` across both manifests and evaluations, added the resumed tag and authenticated parent hashes, and used seeds 222/223. Temporary outputs were verified and removed.
- Genuine persisted-v1 lifecycle: ignored historical `output/rl/recurrent-final-smoke-20260711` supplied actual pre-GM-02 manifest/model bytes: v1 RecurrentPPO, frame stack eight, 21,784,628-byte model, manifest SHA-256 `fb9b08c44f4bd6930e6f04bd41790bb64e4be7f1610480e4d0c86b82f5bf3f8a`, and model SHA-256 `a940a4e049b67c439d241e6cb02262e3adffb6ab2fc69e4d3e667a782198fd9f`. Evaluation succeeded with explicit historical content/training drift, resume produced v2 contiguous offsets `[7,6,5,4,3,2,1,0]` and fingerprint `c68f2aeaea62e36cff4d9ab96d73eb02881028d01e50b74267da8a36da2f16b1`, preserved both parent hashes plus cross-content/cross-training/resumed tags, and the child re-evaluated successfully. No large binary was added.
- Static/app: ten changed Python files pass Ruff check and format; `git diff --check`, YAML parsing, PowerShell workflow parsing, and the two-frame dummy-video app smoke pass. Every source/test file remains under 500 lines; `test_rl_training.py` is 487.
- Fingerprints: protocol `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, default task `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and content `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60` remain unchanged; trainer identity intentionally changes from `a435f8d354967880e29bedd525f6ca48faced801ac4eed3f469aa82e23f765d8` to `dfc7e9b5430e518d92a62d9509ac14b84a9607d007d27680386bafde326f9699`.
- Adversarial review: manifest/CLI, runtime/recurrent, and CI/resource/docs lanes independently refuted the corrected implementation and returned clean. External Codex/Claude review remains unavailable because the platform denied repository-context export to Claude; no bypass was attempted.
- Node boundary: local `npm test` reproduced the known 25/44 result with the same 19 civ-engine 2.4.1-versus-pinned-2.2.0 failures; pinned CI now runs exact default, named multiscale, and legacy lifecycle assertions until GM-04 supplies an isolated local engine.

## GM-02c Commit A - remote implementation gate

- Commit: `9b75f3728bebadb6d8f3816dcfea6ef697f3ae0f` (`feat: integrate descriptor-driven RL history [GM-02c:A]`).
- Push: `origin/main` advanced from `53bc510` to `9b75f37`.
- Remote workflow: [run 29211060401](https://github.com/yanfengliu/python_mini_metro/actions/runs/29211060401) succeeded; `build` passed in 41 seconds, including all 44 Node tests against pinned civ-engine 2.2.0 plus the clean recursive pass and 399-test Python suite, and `rl-smoke` passed in 3 minutes 28 seconds including exact default recurrent, named multiscale fresh/resume/evaluate, and legacy PPO lifecycle paths.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-02c complete pending B's own CI, and keep GM-02d behind that remote gate.

## GM-02c Commit B - remote finalization

- Commit: `812e426f3d0d816dc0050930b3f948cf8ec1fe9a` (`docs: finalize descriptor-driven RL history [GM-02c:B]`).
- Push: `origin/main` advanced from `9b75f37` to `812e426`.
- Remote workflow: [run 29211292517](https://github.com/yanfengliu/python_mini_metro/actions/runs/29211292517) succeeded; `build` passed in 32 seconds and `rl-smoke` passed in 3 minutes 36 seconds.
- Outcome: GM-02c is remotely finalized. GM-02d1 starts from this exact baseline with the preregistered benchmark harness and Windows process-tree supervisor.

## GM-02d1 local implementation evidence

- Contract and TDD: implementation began with the expected red failures for missing benchmark modules and interfaces, then added the dependency-light campaign and promotion contracts, exact RecurrentPPO worker, source-provenance validation, and Windows process-tree supervisor without observing any benchmark candidate result. Final focused coverage passed 35 core tests plus 4 exact-RL integration tests.
- Full Python gates: the authoritative sequential core suite passed 436 tests with 12 expected optional-RL skips in 5.724 seconds; the authoritative sequential exact-RL suite passed 439/439 in 10.492 seconds. An earlier parallel full-suite attempt was invalid because host contention tripped two synthetic 100 ms sampler-gap tests; the sequential reruns removed that measurement interference and are the recorded gate results.
- Static, workflow, and app gates: changed-file Ruff check and format passed; the GitHub Actions YAML and embedded PowerShell parsed successfully; the two-frame dummy-video app smoke passed. Every new source and test file remains below 500 physical lines: the worker is 499 lines, the largest test is 496 lines, and `resource_profile.py` is 476 lines.
- Fingerprints: protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, default task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and environment content remains `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60`; trainer identity intentionally changes to `8bd0b9068d8b32a3ffed105eb43983a77bf773ec04e90b1f6b3fd6b99af092a4`.
- Node boundary: local `npm test` remained at 25/44 with the same 19 failures caused by live civ-engine 2.4.1 versus pinned 2.2.0. No Node behavior changed; pinned GitHub Actions remains authoritative until GM-04 supplies the isolated local pin.
- Adversarial review: three final independent in-process lanes returned clean after source-attestation, tensor/rate validation, process cleanup, log-drain, descendant-lifetime, and nonfatal-race findings were fixed and refuted. External Codex/Claude review remains unavailable because the platform denied repository-context export to Claude; no bypass was attempted.
- Durability boundary: no candidate benchmark result has been observed. GM-02d1 Commit A has not been created or pushed, and no remote CI result exists yet; Commit A is the next action.

## GM-02d1 Commit A - remote implementation gate

- Commit: `02ceb543f251e4a84eba37d3818838f012527536` (`feat: add matched RL history profiler [GM-02d1:A]`), based on the separately green headless-workflow commit `bd1f228c2011e75c1d057ddea9e800b70c5a28f8`.
- Push: `origin/main` advanced from `bd1f228` to `02ceb54`.
- Remote workflow: [run 29293092427](https://github.com/yanfengliu/python_mini_metro/actions/runs/29293092427) succeeded; `build` passed in 32 seconds and `rl-smoke` passed in 3 minutes 26 seconds, including the expanded resource-profile, Windows process-tree, recurrent history, and legacy lifecycle coverage.
- Commit B purpose: durably record A's exact SHA/CI, mark GM-02d1 complete pending B's own CI, and keep all GM-02d2 candidate measurements behind that exact remote gate.

## GM-02d1 Commit B - remote finalization

- Commit: `3c684724a73882b31a714553f1f87f58c39f31da` (`docs: finalize matched RL history profiler [GM-02d1:B]`).
- Push: `origin/main` advanced from `02ceb54` to `3c68472`.
- Remote workflow: [run 29293344902](https://github.com/yanfengliu/python_mini_metro/actions/runs/29293344902) succeeded; `build` passed in 31 seconds and `rl-smoke` passed in 4 minutes 37 seconds.
- Outcome: GM-02d1 is remotely finalized. Both GM-02d2 campaigns ran from this exact tracked-clean source commit with only the declared `.agents/` exclusion and ignored `output/` evidence present.

## GM-02d2 matched campaign evidence

- Frozen workload: Windows 11, Intel Core i9-13900KF with 32 logical CPUs, 68,423,581,696 physical RAM bytes, Python 3.13.10, NumPy 2.5.1, pygame-ce 2.5.7, Stable-Baselines3/SB3-Contrib 2.9.0, Torch 2.13.0, seed 42, eight environments, 128 rollout steps, recurrent batch 64, four epochs, one-million-step learning-rate horizon, and Torch threads `24/24`. Protocol fingerprint is `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`; task fingerprint is `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`; measured trainer fingerprint is `03a60b3cf0cf8c7b1c54ec4d8ec14b93cd82b312b0a4fe66e9e120ef655d2970`.
- Primary campaign: all nine workers exited normally, but one eight-contiguous control repeat had a 200,820,700 ns maximum sample gap and 190,223,900 ns acquisition, exceeding the preregistered 100 ms limits. The campaign is operationally invalid, so its aggregate medians/ratios are not promotion evidence. The valid twelve-frame target repeats nevertheless had a 4,454,989,824-byte median process-tree peak, independently exceeding the strict 4,197,256,790-byte historical cap. The 509,376-byte summary SHA-256 is `bf504fb127eb656593e740b34673e6bc9a3f3412f68c4022d8bfcd8aa325f051`; raw evidence occupies 9.179 MiB.
- Fallback campaign: all eight interleaved repeats were complete, valid, matched, and below the 100 ms timing bounds. Eight-contiguous versus ten-multiscale median peak working set was 3,636,346,880 versus 4,043,184,128 bytes, ratio `1.1118807587`; target headroom below the historical cap was 154,072,662 bytes. Median end-to-end throughput was 86.303195 versus 73.205171 FPS, ratio `0.84823245`. All three preregistered gates passed and promoted exact layout `decision-history-10-fallback-v1`, offsets `[128,64,7,6,5,4,3,2,1,0]`, fingerprint `8c2959aac108ea5b16b977d8fe5e0f9adff795dc2e38a7d233354f28319d3602`. The 448,745-byte summary SHA-256 is `43e7200a9dd54c12f75d353a83d70bf66d38b84cd82a5a8649533ebf0f7ef114`; raw evidence occupies 7.480 MiB.
- Storage interpretation: the gigabyte measurements are summed instantaneous process-tree working-set RAM across the launcher/trainer and eight environment workers, not disk use, and the OS metric can double-count shared pages across processes. The complete raw evidence for both campaigns occupies about 16.7 MiB and remains ignored; the compact committed artifact records every run and authenticates each raw sample/log plus both aggregate summaries.
- Compact artifact: the canonical LF Git content at `docs/threads/current/game-maturity/2026-07-12/1/gm02d2-profile-evidence.json` is 18,811 bytes with SHA-256 `e63f00365a62e0b95abf493ff93037511f304b72711b17cf3e0302b37ebcfcdd`. It preserves decision-recomputable rows and raw-file digests, not the ignored raw bytes themselves; deleting `output/` would therefore retain the compact claims but remove independent raw replayability. A Windows checkout may materialize one terminal CRLF and therefore has different working-tree byte size/hash; the recorded identity is deliberately the normalized committed content.
- Promotion boundary: engineering safety passed only for the ten-frame fallback. Passenger-delivery efficacy is unmeasured here and remains the multi-seed held-out objective under GM-12.

## GM-02d2 local promotion evidence

- TDD and contract: the first focused run failed with the expected missing default-history imports plus five stale aggregate/reason assertions. Production then added one exact default factory, fresh recurrent/PPO resolution precedence, default vector construction, and structural fail-closed decision semantics. Final focused coverage passed 20/20 dependency-light history/resource tests and 19/19 exact-RL CLI/training tests.
- Runtime smoke: a real 128-step fresh RecurrentPPO train/evaluate/resume/evaluate lifecycle emitted and preserved exact layout `decision-history-10-fallback-v1`, offsets `[128,64,7,6,5,4,3,2,1,0]`, and fingerprint `8c2959aac108ea5b16b977d8fe5e0f9adff795dc2e38a7d233354f28319d3602`, including resumed parent hashes/tags. A real fresh explicit `--algorithm ppo` run without a history selector emitted contiguous offsets `[7,6,5,4,3,2,1,0]`. Temporary model artifacts were verified and removed.
- Full Python gates: the sequential core suite passed 437 tests with 12 expected optional-RL skips in 5.662 seconds; the sequential exact-RL suite passed 440/440 in 9.567 seconds. Changed-file Ruff check/format, pre-commit hooks, workflow YAML plus embedded PowerShell parsing, compact-evidence JSON parsing, `git diff --check`, and a two-frame dummy-video app smoke all passed. All eight changed Python source/test files remain below 500 physical lines; the largest is `test_rl_training.py` at 493 and `resource_profile.py` is 488.
- Fingerprints: protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, default task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and environment content remains `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60`. Trainer identity intentionally changes from the measured source fingerprint `03a60b3cf0cf8c7b1c54ec4d8ec14b93cd82b312b0a4fe66e9e120ef655d2970` to `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93` for the promoted default implementation.
- Node boundary: local `npm test` reproduced the known 25/44 result with the same 19 failures rooted in live sibling civ-engine 2.4.1 versus repository pin 2.2.0; no Node source changed. Pinned CI remains authoritative until GM-04 supplies the isolated local engine.
- Review boundary: the required external Codex review attempt was blocked by the platform because it would export the uncommitted repository diff; the same export was not rerouted through Claude. The prepared task-specific prompts are committed. The independent code lane returned clean; the evidence/documentation lane found and closed three medium plus two low integrity/accuracy issues; the final refuter found and closed the stale raw-primary-decision representation; all three lanes then converged clean against the live repository.
- Durability boundary at implementation review: GM-02d2 Commit A had not yet been created or pushed. The exact remote result is recorded below; passenger-delivery efficacy remains explicitly deferred to GM-12.

## GM-02d2 Commit A - remote implementation gate

- Commit: `36cf0588941f02617f1de450ec4f47b35580a2a7` (`feat: promote profiled RL history [GM-02d2:A]`).
- Push: `origin/main` advanced from `3c68472` to `36cf058`.
- Remote workflow: [run 29297091497](https://github.com/yanfengliu/python_mini_metro/actions/runs/29297091497) succeeded; `build` passed in 34 seconds and `rl-smoke` passed in 3 minutes 22 seconds. The pinned jobs covered all 44 Node contract tests, the complete Python suite, exact-RL library contracts, a real recurrent ten-frame train/evaluate/resume/evaluate lifecycle, and the explicit legacy PPO lifecycle.
- Commit B purpose: durably bind the measured ten-frame promotion to A's exact SHA and green remote run before GM-03a begins.

## GM-02d2 Commit B - remote finalization

- Commit: `dc35cd6a7710a5e2bdfed2bea16ce1fe40dd5761` (`docs: finalize profiled RL history [GM-02d2:B]`).
- Push: `origin/main` advanced from `36cf058` to `dc35cd6`.
- Remote workflow: [run 29297764352](https://github.com/yanfengliu/python_mini_metro/actions/runs/29297764352) succeeded; `build` passed in 31 seconds and `rl-smoke` passed in 4 minutes. GM-02d2 is remotely finalized.

## GM-02e hybrid and semantic-memory research evidence

- Live boundary: `PlayerPixelEnv` is explicitly the official player-equivalent pixels-only learning task; `MiniMetroEnv` is privileged structured debugging/verification state. Exact semantic tensors therefore define an assisted observation task even when restricted to rendered facts. A pixel-only deployed actor may still use privileged simulator labels through a separately authenticated teacher, auxiliary target, or asymmetric critic during training.
- Feasibility: the installed SB3-Contrib and Stable-Baselines3 versions are both 2.9.0, and local introspection confirms `MultiInputLstmPolicy` aliases `RecurrentMultiInputActorCriticPolicy`. The current `MiniMetroCNN` and `VecTemporalHistory` remain Box-specific, so hybrid training requires a custom multi-input extractor plus a Dict-aware pixel-only history lifecycle rather than a policy-name swap.
- Current-size estimate: one non-frozen diagnostic packing of the present 20-station/4-line/4-metro/7-shape game fits 2,178 `float32` semantic features, about 8.51 KiB per observation or 8.51 MiB for 8 environments x 128 steps. That is tiny beside the current ten-frame rollout's 607.5 MiB raw pixel payload, but GM-05 through GM-10 will change the final field inventory and the durable schema waits until post-balance GM-12.
- Research result: retain ten-frame CNN-LSTM RecurrentPPO as the bounded pixel-only baseline. Measure semantic structured-only and direct semantic-hybrid LSTM lanes first; if semantics help, test a pixel-only actor trained with privileged semantic assistance. Escalate current-entity pooling to relation attention and LSTM/GRU to temporal Transformer only after targeted diagnostics demonstrate the simpler model's ceiling.
- Primary evidence: SB3-Contrib documents recurrent Dict/MultiDiscrete support; Relational Deep RL motivates entity reasoning; GTrXL motivates gated long-memory attention; the 2025 Memory Gym study found GRU significantly ahead of Transformer-XL on every endless variant; Asymmetric Actor Critic, Learning by Cheating, and UNREAL motivate training-time privileged or auxiliary signals without granting them to a deployed visual actor.
- Review boundary: independent live-code reviewers found and closed contradictory task identity, privileged-precision labeling, Box-only history lifecycle, final GM-05-through-GM-10 inventory, persistence-authority, and premature-freeze gaps. The external pinned Codex plan review was blocked before launch because the platform would not export repository plan/code context without separate disclosure approval; Claude was not used to reroute the prohibited same export. In-process re-review is the completion authority for this unit.
- Disk/RAM clarification: the profile's 3.6-4.5 GB figures are summed peak process-tree working-set RAM. Live repository measurement found ignored `output/` at 816.6 MiB, led by `output/venv-rl` at 735.9 MiB (`torch` about 490 MiB); raw history-profile evidence is 16.7 MiB.
- Durability boundary at research review: GM-02e Commit A had not yet been created or pushed. Its exact remote result is recorded below. No runtime, reward, observation, model, dependency, or manifest default changed in this research-only work unit.

## GM-02e Commit A - remote research gate

- Commit: `27a0304df1309096561ecdf21ffdcb46d6c9688f` (`docs: plan hybrid RL memory [GM-02e:A]`).
- Push: `origin/main` advanced from `dc35cd6` to `27a0304`.
- Remote workflow: [run 29299216859](https://github.com/yanfengliu/python_mini_metro/actions/runs/29299216859) succeeded for the exact commit; `gh run watch 29299216859 --exit-status` returned zero after the pinned workflow completed. A subsequent metadata-only query was unavailable because the approval service reached its usage limit, so no unobserved per-job durations are claimed.
- Commit B purpose: durably bind the hybrid/semantic-memory research decision to A's exact green remote result before GM-03a begins.

## GM-02e Commit B - remote finalization

- Commit: `60b4174b2bbe2f92ae3abac4a44991f03caa518b` (`docs: finalize hybrid RL memory plan [GM-02e:B]`).
- Push: `origin/main` advanced from `27a0304` to `60b4174`.
- Remote workflow: [run 29302064550](https://github.com/yanfengliu/python_mini_metro/actions/runs/29302064550) succeeded; `build` passed in 36 seconds and `rl-smoke` passed in 3 minutes 58 seconds. GM-02e is remotely finalized.

## GM-03a frozen baseline

- Source boundary: `test/test_mediator.py` is 1,158 physical lines with Git blob `a52b410258b513ded74e71a58bbea40cb1555506`, 57 unique tests, and three fixture/helper methods. `src/mediator.py` is 1,112 lines and is explicitly out of scope until GM-03b through GM-03f.
- Local baseline: isolated py313 mediator tests passed 57/57; the full py313 suite passed 437 tests with 12 expected optional-RL skips in 10.275 seconds.
- Review boundary: the pinned Codex plan review was blocked before launch because external repository-context transfer lacked separate post-disclosure approval; Claude was not used to reroute the prohibited export. Three independent in-process reviewers approved the corrected exact partition, discovery/body-preservation contract, documentation/process obligations, and durable cursor before implementation.

## GM-03a local implementation evidence

- Mechanical preservation: the monolithic test was replaced by `mediator_test_support.py` plus six behavior modules with standalone counts `12/8/8/10/8/11`. A frozen-baseline verifier proved exactly 57 unique discovered test IDs, all 57 original method names, all three helpers, attribute-free AST equality, exact dedented source-segment equality, and all six in-method comments. The original file is deleted without an aggregator.
- Runtime validation: all six modules passed independently in fresh py313 processes and passed together 57/57 in 0.186 seconds. The sequential core suite passed 437 tests with 12 expected optional-RL skips in 5.646 seconds; the sequential exact-RL suite passed 440/440 in 11.622 seconds.
- Static/size boundary: Ruff check and format passed all seven new Python files after deliberate `isort: split` boundaries kept the support path bootstrap ahead of bare production imports. File sizes range from 72 to 270 physical lines, below the 500-line target.
- Production boundary: comparison against frozen baseline `60b4174`, ordinary/cached diffs, and explicit `git status --short -- src` all prove no modified, staged, or untracked production file. `ARCHITECTURE.md` and `PROGRESS.md` document only the behavior-neutral test ownership change; README and GAME_RULES remain unchanged.
- Hooks/review boundary: final pre-commit passed all 33 GM-03a changed/deleted/new paths with EOF, trailing-whitespace, Ruff check, and Ruff format hooks clean. Three independent live-code reviewers found no Python defect; all three found stale implementation/cursor evidence, and two found the inaccurate word “seeded” for the unchanged entropy-backed fixture. Both documentation defects were corrected, and all three final re-review lanes returned `CLEAN`. External final-diff review remains unlaunched under the same prohibited repository-export boundary. GM-03a is locally ready for Commit A.

## GM-03a Commit A - remote implementation gate

- Commit: `83d02d4002f739a41e2562e251a6b0023b98d6d3` (`test: split mediator test suite [GM-03a:A]`).
- Push: `origin/main` advanced from `60b4174` to `83d02d4`.
- Remote workflow: [run 29303936139](https://github.com/yanfengliu/python_mini_metro/actions/runs/29303936139) succeeded; `build` passed in 32 seconds and `rl-smoke` passed in 3 minutes 35 seconds.
- Commit B purpose: durably bind the exact behavior-neutral split and its local proofs to A's green remote result before GM-03b changes production mediator ownership.

## GM-03a Commit B - remote finalization

- Commit: `fbcb31d0321d690da56d4d7299c9720248881059` (`docs: finalize mediator test split [GM-03a:B]`).
- Push: `origin/main` advanced from `83d02d4` to `fbcb31d`.
- Remote workflow: [run 29304181859](https://github.com/yanfengliu/python_mini_metro/actions/runs/29304181859) succeeded; GitHub rendered `build` at 39 seconds and `rl-smoke` at 3 minutes 32 seconds.
- Outcome: GM-03a is remotely finalized. GM-03b starts from this exact baseline and records the result before production edits.

## GM-03b frozen baseline and plan review

- Source boundary: `src/mediator.py` is 1,112 physical lines with Git blob `73eb42b9970418b8edc7b465fda76eaa8fdaf4e1`; its current progression cluster spans configuration/runtime state, writable aliases, price/unlock/purchase policy, entity/UI effects, and delivery integration. `test/test_mediator_progression.py` has 11 tests and 159 physical lines.
- Local baseline: progression, passenger-flow, structured-environment, and recursive-checkpoint coverage passed 56/56 tests in 0.192 seconds from `fbcb31d`.
- Ownership decision: a dependency-free `NetworkProgression` will solely own moved scalar/config/cache state and pure policy. Explicit writable `Mediator` properties and real public wrappers preserve callers; stations, buttons, identities, simulation-time effects, and delivery-hook orchestration remain on the facade.
- Plan review: three independent live-code lanes initially disagreed on stateful aggregate versus stateless host controller, then converged on the precise no-duplication stateful design after checking direct writes, mutable lists, stale caches, constructor dispatch/RNG order, checkpoint access, monkeypatched hooks, and future save boundaries. Zero substantive plan finding remains.
- External boundary: pinned external review was not relaunched because the platform's repository-context export prohibition was not superseded by the user's approval for pre-commit, Git, and GitHub CI. No transfer or reroute occurred; limitation artifacts and task-specific prompts are preserved under `2026-07-13/3/`.
- Durability boundary at plan review: production and behavior-test edits had not started at this snapshot. The completed implementation evidence follows.

## GM-03b local implementation evidence

- TDD and ownership: baseline-green facade characterization passed before production edits; direct `NetworkProgression` contracts then produced the expected `ModuleNotFoundError: progression` red result. The dependency-free aggregate now solely owns the declared progression scalars/config/caches, while explicit writable `Mediator` properties and real public wrappers preserve consumers and side effects.
- Runtime validation: the final focused progression/passenger slice passed 77/77 tests in 0.250 seconds. The authoritative sequential core suite passed 454 tests with 12 expected optional-RL skips in 5.490 seconds; the exact-RL environment passed 457/457 in 10.832 seconds.
- Compatibility proof: all 11 public progression method AST signatures match baseline. A seeded baseline/current canonical checkpoint is byte-identical at 13,818 bytes after 90 deliveries, 90 credits, three unlocked paths, and six stations. Public next-index and price override dispatch, skipped/full-target price short-circuiting, stale-cache behavior, live list identity, RNG order, entity identity, delivery-hook order, and simulation-time effects have explicit regression coverage.
- Static and identity gates: Ruff check and format pass all five changed Python files; final all-path pre-commit passes EOF, trailing-whitespace, Ruff check, and Ruff format hooks across the complete intended unit. Protocol fingerprint remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`; task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`; training remains `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93`; the intentional new content fingerprint is `31d2a4c146fdf54234c2ef94f7b6ca5276926dfcb2f05e9a9a7fff2f5026b9a7`.
- Adversarial review: the first code lane found a real public-dispatch regression; its initial fix exposed a second eager-price-query regression. Both were corrected and independently refuted with high-price/non-mutation and raising-price/short-circuit tests. Final code and refutation lanes returned `CLEAN`. The documentation lane's stale cursor, incomplete untracked-diff procedure, undisclosed size debt, and retry-prompt findings were corrected before final staging.
- Size boundary: `src/progression.py` is 100 lines; `test/test_network_progression.py` is 139; `test/test_mediator_progression.py` is 341; and `test/test_mediator_passenger_flow.py` is 265. The explicit facade makes `src/mediator.py` 1,193 lines, 81 above its 1,112-line baseline and still above the 1,000-line ceiling. This is disclosed temporary debt: GM-03c must finish below 1,112 and GM-03d below 1,000 before later clusters continue toward the practical under-500 target.
- Staged boundary: the exact 29-file GM-03b unit is staged; cached `diff --check` is clean and the staged secret-pattern scan reports zero matches. The complete cached inventory includes every new aggregate, test, and iteration artifact; only the pre-existing `.agents/` tree remains untracked and ignored `output/` remains excluded.
- Durability boundary at local review: GM-03b Commit A had not yet been created or pushed. Final all-path pre-commit and cached-diff review were green; the exact remote result now follows.

## GM-03b Commit A - remote implementation gate

- Commit: `36e89d9bd70f0b41ce1a3d863fa85cd26eee811c` (`refactor: extract mediator progression [GM-03b:A]`).
- Push: `origin/main` advanced from `fbcb31d` to `36e89d9`.
- Remote workflow: [run 29310175226](https://github.com/yanfengliu/python_mini_metro/actions/runs/29310175226) succeeded for the exact commit; `build` passed in 4 minutes and `rl-smoke` passed in 3 minutes 59 seconds. The pinned jobs covered the full Python/recursive/Node contract gate plus the exact RL library and recurrent-history/legacy-PPO smoke.
- Commit B purpose: durably bind the progression extraction and its local compatibility proofs to A's exact green remote result before GM-03c begins.

## GM-03b Commit B - remote finalization

- Commit: `00ea38c2dbee3fd51985ae9c52377ae404502e29` (`docs: finalize mediator progression extraction [GM-03b:B]`).
- Push: `origin/main` advanced from `36e89d9` to `00ea38c`.
- Remote workflow: [run 29311017088](https://github.com/yanfengliu/python_mini_metro/actions/runs/29311017088) succeeded for the exact commit; both `build` and `rl-smoke` ran from 06:19:41Z through 06:20:19Z, 38 seconds each by the API timestamps.
- Outcome: GM-03b is remotely finalized. GM-03c starts from this exact baseline and must reduce `src/mediator.py` below its original 1,112-line pre-GM-03b baseline without public-dispatch or route-selection drift.

## GM-03c frozen baseline

- Source boundary: `src/mediator.py` is 1,193 physical lines at `00ea38c`; route planning occupies the tail cluster beginning with destination-station selection at line 1,049 and includes eight public methods through line 1,193. `travel_plans` remains a mutable mediator-owned passenger/entity mapping.
- Local baseline: routing, passenger flow, path lifecycle, simulation, graph, recursive checkpoint, and structured environment coverage passed 80/80 tests in 0.409 seconds.
- Durability boundary: no GM-03c production or test edit has started. Three independent live-code lanes are mapping the pure planning boundary, compatibility seams, test obligations, and feasible below-1,112 size recovery before the implementation plan is frozen.

## GM-03c plan review

- Boundary: one stateless pygame-free `RoutePlanner` owns deterministic queries/search/compression and lazy boarding/bulk proposals. Mediator keeps RNG, fresh graph creation, every public method, plan-map and entity mutation, topology, movement, and passenger effects.
- Review findings closed: search-only size insufficiency; callback and plan-map rebinding; exact boarding plan yield; lazy bulk apply-before-resume; constrained-unowned versus bulk-installed hook visibility; empty/non-empty graph lookup order; adjacent-arrival and unreachable-sentinel identity; absent-path no-RNG short-circuit; fingerprint/oracle/import proof; worktree/artifact/prompt accuracy.
- Size contract: the 178 in-scope mediator lines have a 95-line target and 96-line hard replacement ceiling, yielding a target of 1,110 and hard maximum of 1,111. No unrelated topology or passenger ownership moves merely to meet the gate.
- Convergence: all three independent live-code lanes returned `APPROVED`; no substantive plan finding remains. External pinned plan review remains unlaunched under the unchanged repository-context transfer boundary, with no reroute.
- Durability boundary: no production or behavior-test edit has started. Baseline-green facade characterization is next, followed by the expected-red missing direct planner contract.

## GM-03c baseline-green facade characterization

- Nine new behavior-level tests pass against untouched baseline production in 0.050 seconds. They freeze dynamic BFS/compression and constrained-plan rebinding, constrained versus bulk station-node lookup timing, same-list compression identity, absent-path no-passenger/no-RNG short-circuit, unreachable retry RNG plus empty-sentinel identity, adjacent-arrival live-list timing, and constrained-unowned versus bulk-installed hook visibility.
- `test/test_mediator_route_contract.py` is 348 physical lines and passes Ruff check/format. No production file changed. Split direct planner query/selection/iterator contracts are being added next; their first isolated run must fail only because `route_planner` does not yet exist.

## GM-03c expected-red direct contract

- `test/test_route_planner_queries.py` was added before production and its isolated unittest run produced one loader error with exactly `ModuleNotFoundError: No module named 'route_planner'`. No implementation failure or unrelated error was present.
- The query module is 162 physical lines and passes Ruff check/format. Selection and lazy-iterator contracts are being completed before the smallest planner implementation is added.

## GM-03c implementation and adversarial correction evidence

- Direct TDD: query, selection, and iterator modules each produced the expected isolated `ModuleNotFoundError: route_planner` before production existed. The stateless `RoutePlanner` then made all direct contracts green and imports in a fresh process without loading pygame, mediator, travel-plan, entity, or graph modules.
- First implementation review: independent live-code reviewers found two mutable path-ID snapshots and one captured `travel_plans` mapping that differed from baseline attribute-load timing. Six new direct/facade tests reproduced the regressions before fixes. The planner now accepts fresh ID and map resolver thunks invoked only at the original short-circuited comparison/read points; all six tests and the full 40-test direct/facade slice pass.
- Focused compatibility: direct planner, mediator route facade, routing, passenger flow, path lifecycle, simulation, graph, recursive checkpoint/oracles, and structured environment coverage passes 129/129 tests in 0.405 seconds after the fixes.
- Differential proof: baseline `00ea38c` and current mediators ran the same seeded 2,400-step three-station route scenario. All reward/action/done results matched, 44 canonical checkpoints matched exactly, and both produced four deliveries without game over.
- First-correction size and identity snapshot: `src/mediator.py` was 1,110 physical lines, meeting the target and below the 1,111 hard ceiling; `src/route_planner.py` was 192 lines and every changed test remained below 500. All nine public route-facade AST signatures matched baseline. Protocol remained `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, task remained `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, training remained `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93`, and the then-current content fingerprint was `6095ec0dd2d446673b4fa6546865e72f56f3183ab187b4f968b4061b5c0748d0`.
- Boundary at that checkpoint: three post-fix in-process re-review lanes and the final post-fix core/exact-RL/hook/staging gates remained in progress. No GM-03c commit or push had occurred; `main` and `origin/main` remained at `00ea38c`.

## GM-03c final correction and local validation

- Second expected-red contract: five facade observability tests and three direct resolution-order tests initially produced eight errors. They proved facade route remeasurement, false arrival after compression, missing post-arrival fallback, arrival effects after destination-iterator finalization, and reducer/shared/factory lookup after argument effects. Explicit `arrival`/`route`/`fallback` proposals plus callable getters made all eight green.
- Lifetime refutation: later live-HEAD reviewers proved that closing a nested selector released yielded destinations and prior reduced routes before the fallback guard, and that storing resolved reducer/shared/factory callables extended their lifetime beyond the original call. Two destination/route-local tests and four callable-lifetime tests reproduced those state-changing differences red. Bulk selection now stays in the proposal generator frame, while direct getter-call composition resolves each callable before its arguments and releases it immediately after invocation.
- Review convergence: the final arrival/finalizer lane, resolution/map/callable lane, and broad code/test lane independently returned `CLEAN`. The reviewers re-ran the actual prior HEAD/current differentials, which now match, and found no unresolved substantive defect. External Codex/Claude review remains unlaunched under the recorded repository-context transfer boundary.
- Final local gates: the route-planning compatibility slice passed 144/144 in 1.066 seconds; the sequential py313 core suite passed 509 tests with 12 expected optional-RL skips in 6.972 seconds; the sequential exact-RL suite passed 512/512 in 12.845 seconds. Ruff check and format passed across all nine changed Python files.
- Differential and identity proof: baseline `00ea38c` and current code again matched all 2,400 action/reward/done outcomes and all 44 canonical checkpoints in the seeded three-station scenario, ending with four deliveries and no game over. All nine public route-facade AST signatures still match. A fresh import of `route_planner` loads none of pygame, mediator, travel-plan, entity, or graph modules.
- Final fingerprints: protocol is unchanged at `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`; default task is unchanged at `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`; training is unchanged at `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93`; the intentional final content fingerprint is `548d2fbd7a28abeec2ae45ef1c64e5239bc6ff5c7e2d1540336a12ee7c813394`.
- Final size boundary: `src/mediator.py` is 1,110 lines, meeting the GM-03c target and hard gate; `src/route_planner.py` is 231. The largest changed test is `test_route_planner_selection.py` at 462 lines; all changed tests remain below 500. GM-03d still owns the next reduction below the repository-wide 1,000-line ceiling.
- Durability boundary at local review: changed-path pre-commit passed all end-of-file, trailing-whitespace, Ruff check, and Ruff format hooks across the 37-file intended unit without rewrites. The cached stat was 37 files with 2,955 insertions and 152 deletions; cached diff check, high-confidence credential scan, dependency-declaration scan, and `.agents/`/`output/` exclusion checks all passed. Commit A had not yet been created at that checkpoint; its exact remote result follows.

## GM-03c Commit A - remote implementation gate

- Commit: `1b751e47cd3edce3556b32880a26851db3a072d2` (`refactor: extract route planning [GM-03c:A]`).
- Push: `origin/main` advanced from `00ea38c` to `1b751e4`.
- Remote workflow: [run 29351838271](https://github.com/yanfengliu/python_mini_metro/actions/runs/29351838271) succeeded for the exact commit. API timestamps show `build` ran from 16:58:34Z through 16:59:08Z (34 seconds) and `rl-smoke` from 16:58:35Z through 17:02:18Z (3 minutes 43 seconds).
- Commit B purpose: durably bind the route-planning extraction and its local equivalence proofs to A's exact green remote result before GM-03d changes topology/path lifecycle ownership.

## GM-03c Commit B - remote finalization

- Commit: `5e6186d8b331207d2a6ec583b7a82f80533f5203` (`docs: finalize route planning extraction [GM-03c:B]`).
- Push: `origin/main` advanced from `1b751e4` to `5e6186d`.
- Remote workflow: [run 29352432028](https://github.com/yanfengliu/python_mini_metro/actions/runs/29352432028) succeeded for the exact commit. API timestamps show `build` ran from 17:07:08Z through 17:07:52Z (44 seconds) and `rl-smoke` from 17:07:07Z through 17:10:51Z (3 minutes 44 seconds).
- Outcome: GM-03c is remotely finalized. GM-03d starts from this exact baseline and owns topology/path lifecycle extraction plus the required reduction of `src/mediator.py` below 1,000 physical lines.

## GM-03d frozen baseline

- Source boundary: `src/mediator.py` is 1,110 physical lines at `5e6186d`; GM-03d must preserve every public compatibility method while moving topology/path lifecycle ownership into a focused module and finishing below 1,000.
- Durability boundary: no GM-03d production or test edit has started. Three independent live-code lanes are mapping method ownership, observable mutation/identity/order contracts, TDD coverage, and a credible line budget before the implementation plan is frozen.

## GM-03d plan review

- Baseline proof: the 102-test topology-facing slice covering mediator paths/interaction, gameplay, environment, routing/passenger flow, recursive checkpoints/oracles, and render purity passed in 0.883 seconds at exact baseline `5e6186d`.
- Boundary: stateless, non-retaining `PathLifecycle` owns exactly 12 transition algorithms through a call-scoped host. Mediator keeps canonical writable collections/maps/flags, RNG/entities/effects, every real public method, and late module-global `Path`/`Metro` factories.
- Size contract: the frozen 168-line replacement envelope has a 57-line hard wrapper/import/install ceiling, proving `1110 - 168 + 57 = 999`; the target envelope is at most 45, projecting 987 and requiring no GM-03e/GM-03f scope.
- Findings closed: mirrored state/proxy overhead; collection and callback capture; public-to-public dispatch; late factory resolution/release; exact button-map replacement; removal snapshots/order/partial state; detached object graphs; draft graph visibility; loop/snap/abort/finish identity; signature/import/differential/fingerprint/remote evidence.
- Convergence: the contracts and refutation lanes returned `APPROVED`; a fresh final live-code lane independently verified the exact method set, arithmetic, factories, hooks, state ownership, and coverage and returned `APPROVED`. External pinned plan review remains unlaunched under the recorded repository-context-transfer boundary.
- Durability boundary: no production or test edit has started. Baseline-green facade characterization is next, followed by the expected-red missing direct lifecycle module contract.

## GM-03d baseline-green facade characterization

- `test/test_mediator_path_contract.py` and non-discovered `test/path_lifecycle_test_support.py` were added before production moved. Ten behavior-level tests pass against the untouched baseline in 0.053 seconds.
- The tests freeze all 12 public signatures; button clearing and mapping replacement; removal snapshots/order/detached graphs; rebound public hooks, path collections, and travel-plan maps; late module-global Path/Metro factory resolution; exact created entity identity and state timing; public creation transitions; loop/snap/finish/abort semantics; selector validation/first match; and draft-versus-finished graph/checkpoint visibility.
- `test/test_mediator_path_contract.py` is 425 physical lines and its support module is 170; both remain below 500. Ruff check and format pass for both files.
- Durability boundary: `src/` remains untouched. The direct lifecycle host contract is next and its isolated first run must fail only because `path_lifecycle` does not exist.

## GM-03d expected-red direct contract and facade coverage review

- `test/test_path_lifecycle.py` and non-discovered `test/path_lifecycle_direct_support.py` were added while `src/path_lifecycle.py` remained absent. The isolated py313 run produced exactly one loader error containing `ModuleNotFoundError: No module named 'path_lifecycle'`, reported `Ran 1 test`, and had no implementation or unrelated failure.
- The direct module is 460 physical lines with ten planned tests; its support module is 185. Ruff check and format pass for both. The contract requires a stateless `__slots__` lifecycle, dependency-light import, exact button/removal/invalidation/selectors, late factories and immediate callable release, programmatic creation, add/abort/release/finish/end transitions, partial factory failure, and call-scoped host state.
- An independent facade-test refuter found five substantive distinctions still missing from the first ten baseline-green tests: index collection re-read, abort pointer/path re-read after release, late finish assignment hook, captured created path versus current rebound collection, and exact partial state/propagated exceptions. A separate baseline-green module is closing all five before production starts.
- Durability boundary: `src/` remains untouched. Production implementation is blocked on those five facade distinctions passing against the baseline.

## GM-03d facade coverage closure

- `test/test_mediator_path_failure_contract.py` adds six baseline-green tests for all five refuter findings and is 207 physical lines. Both facade modules pass 16/16 in 0.060 seconds against untouched production; Ruff check and format pass across all five new test/support files.
- The closure proves live path collection re-read between index bounds and lookup; abort pointer/collection re-read after public release; finish assignment-hook resolution after metro installation; programmatic creation's captured path versus current collection; and unchanged Path/Metro exception identity with exact partial state and no rollback.
- Durability boundary: all reviewed facade distinctions are green and the direct missing-module red is captured. `src/path_lifecycle.py` is still absent and `src/mediator.py` remains unchanged; the 12-method production extraction is next.

## GM-03d production extraction and initial local gates

- The 12 frozen topology/path-lifecycle transition bodies now live in dependency-light `src/path_lifecycle.py`; `Mediator` installs one stateless `PathLifecycle`, retains every real public compatibility method and every canonical directly writable collection/map/flag, and passes late `Path`/`Metro` getter thunks only at the original construction points.
- TDD sequence: the exact baseline topology slice passed 102/102 before test or production edits; 16 facade distinctions then passed against untouched baseline; the direct contract's isolated first run failed only with `ModuleNotFoundError: No module named 'path_lifecycle'`; after production moved, the initial direct/facade slice passed 26/26.
- Initial verification: the topology-focused compatibility slice passed 156/156. After review-driven regression coverage, the final sequential py313 core suite passed 535 tests with 12 expected optional-RL skips in 7.141 seconds, and the exact-RL suite passed 538/538 with no skips in 15.264 seconds. All 12 public facade AST signatures match baseline `5e6186d8b331207d2a6ec583b7a82f80533f5203` exactly.
- Import and size proof: a fresh `path_lifecycle` import loaded none of pygame, mediator, entity, graph, route planner, progression, simulation context, travel plan, or related gameplay modules. `src/mediator.py` is 984 physical lines from the 1,110-line baseline, `src/path_lifecycle.py` is 235, and the five test/support files are 170, 185, 207, 450, and 484 lines; every changed handwritten file is below 500.
- Identity proof: protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and training remains `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93`. The source extraction intentionally changes the content fingerprint to `17c5bbf8e034d3b99e8aa91e70a032bf66470ae6fc54b4a7e29b3d1810f7ed50` under the existing artifact-drift rules.

## GM-03d corrected lifecycle differential

- Implementation-test review identified one real coverage gap in the first proof: generic loop input did not explicitly distinguish the closed encoding `[0, 1, 2, 0]`. The finding was accepted and resolved rather than retaining the pre-finding differential digest. The corrected direct/real-facade pair passes 20/20, while deleting the de-duplication branch now produces exactly two assertion failures and no errors.
- The strengthened baseline/current scenario uses explicit closed-loop input `[0, 1, 2, 0]` with `loop=True`. All seven actions succeed in both versions; all nine normalized observation/canonical-checkpoint records match; both RNG streams match; and the loop topology is station indices `[0, 1, 2]` with `is_looped=True` and snap-blip counts `[0, 2, 2]`, leaving the start station untouched.
- The corrected aggregate is byte-identical across baseline and current at 10,490 bytes with SHA-256 `d6fb9dd21730f381776959c48dab8a9c87f82c7e3387646bf4ce30fd691c978d`. This supersedes the pre-finding differential digest.

## GM-03d implementation-review and durability boundary

- The semantic implementation lane returned `CLEAN` after comparing all 12 normalized bodies/signatures against the live baseline and inspecting mutation order, public dispatch, fresh reads, late factory resolution, partial failures, callable lifetime, identity, and retention. The implementation-test lane returned `CLEAN` after resolving and mutation-testing its explicit closed-loop finding. The process lane returned `NOT CLEAN` because durable status and architecture/progress were stale and the final review/hook/staging bundle was incomplete.
- This documentation update closes the stale state/review/diff plus architecture/project-log findings and preserves implementation-specific Codex/Claude prompts with truthful nonlaunch records. Neither external CLI was launched because repository-context transfer was not authorized; no external approval is inferred.
- The explicit closed-loop finding and final core/exact-RL regression suites are green. With the semantic and implementation-test lanes clean and the process lane's durable-doc findings resolved by this live-state remediation, in-process implementation review is converged. Changed-path pre-commit, staging and cached stat/full-diff inspection, credential scan, dependency-declaration scan, `.agents/`/`output/` exclusion audit, Commit A, and remote CI all remain pending. No GM-03d commit or push has occurred; `main` and `origin/main` remain at `5e6186d`.

## GM-03d fresh commit-readiness review and reproducible differential

- The user explicitly requested review and an early coherent commit. Codex CLI 0.144.4 was confirmed equal to the current registry release after its active binary prevented replacement. Pinned Codex and Claude implementation reviews were launched, but both returned HTTP 401 authentication failures and no approval; the exact failures remain under `raw/codex-2.stdout.log` and `raw/opus-2.md`.
- Three fresh in-process lanes compensated for the unavailable CLIs. Semantic equivalence returned `CLEAN`. The test lane found two `MEDIUM` gaps: black palette fallback/unlocked-prefix behavior survived two mutations, and the earlier 10,490-byte differential had no durable runner or normalized record. The process lane found stale external-review status, missing explicit exclusion of the separate modified `AGENTS.md`, and an ordinary-diff claim that could not cover 29 untracked candidate paths.
- Direct-host and real-Mediator tests now exhaust the unlocked palette while a later locked color remains free. They freeze black fallback plus prefix selection, the focused direct/facade/failure slice passes 27/27, and the changed direct/failure modules remain below 500 lines at 495 and 221.
- `scripts/verify_path_lifecycle_differential.py` now reproduces the exact seven-action/nine-record scenario from archived baseline `5e6186d` and live candidate source without a checkout or worktree. Separate bytecode-disabled child processes emit full canonical checkpoints, source-tree hashes prove no runtime drift, and the commit-bound result plus `--expected` replay are byte-identical at 135,371 bytes with SHA-256 `4ceaf17d638f932df6c3ce31cdba8789f56c0ea82748b4b2b6dcbc111d47c668`. The prior non-reproducible digest is superseded.
- The fresh test/evidence re-review is `CLEAN`: both palette mutations now produce exactly two failures with no errors, and a live replay regenerated the same seven-action/nine-record artifact and summary. The post-fix core suite passes 536 tests with 12 expected optional-RL skips, exact-RL passes 539/539, and Ruff check/format pass across all eight changed Python files.
- The fresh process re-review is `CLEAN`: external 401 status/raw preservation, explicit `AGENTS.md`/`.agents/`/`output/` exclusions, ordinary-versus-cached diff language, artifact/runtime-tree hashes, docs, line limits, and unchanged dependency declarations all match the live tree.
- Changed-path pre-commit is clean. EOF, trailing-whitespace, Ruff check, and Ruff format hooks pass all 41 hook-safe paths. The Codex UTF-16LE stdout remains byte-identical at SHA-256 `3614704f5876bf28d97f87f16dc0c80b9e53d3d311536c5aca79a13af9cd1d5a`; the Claude UTF-16LE raw failure is intentionally excluded from the EOF fixer because that hook appends an invalid single byte, and its restored exact capture remains SHA-256 `fccf9497458d6e0487324107b9fc41af93efd5ce47837c6c3abbe3761b59289b`.
- Durability boundary at local review: the exact 42-path GM-03d unit was staged at 2,959 insertions and 160 deletions. Cached diff/check, high-confidence credential, dependency-declaration, and modified-`AGENTS.md`/`.agents/`/`output/` exclusion audits all passed; only modified `AGENTS.md` remained unstaged and only `.agents/skills/multi-cli-review/SKILL.md` remained untracked. Commit A had not yet been created at that checkpoint; its exact remote result follows.

## GM-03d Commit A - remote implementation gate

- Commit: `9321dcde0a0b062bb4953a3ac75d6f2bdaa06c3a` (`refactor: extract path lifecycle [GM-03d:A]`).
- Push: `origin/main` advanced from `5e6186d` to `9321dcd`.
- Remote workflow: [run 29386046847](https://github.com/yanfengliu/python_mini_metro/actions/runs/29386046847) succeeded for the exact commit. API timestamps show both `build` and `rl-smoke` ran from 03:14:27Z through 03:15:02Z (35 seconds each).
- Commit B purpose: durably bind the path-lifecycle extraction and its local equivalence proofs to A's exact green remote result before GM-03e changes passenger-flow ownership.

## GM-03d Commit B - remote finalization

- Commit: `b1e419e21080fd5bd43e1ac6a4eef7e264f732ec` (`docs: finalize path lifecycle extraction [GM-03d:B]`).
- Push: `origin/main` advanced from `9321dcd` to `b1e419e`.
- Remote workflow: [run 29386306430](https://github.com/yanfengliu/python_mini_metro/actions/runs/29386306430) succeeded for the exact commit. API timestamps show `build` ran from 03:20:59Z through 03:24:57Z and `rl-smoke` from 03:20:58Z through 03:24:57Z.
- Outcome: GM-03d is remotely finalized. Per D-007, GM-03e's opening transaction records this terminal metadata result rather than creating a third GM-03d commit.

## GM-03e frozen baseline

- Last game-maturity boundary: GM-03d Commit B `b1e419e` and exact run `29386306430` are green.
- Actual repository baseline: policy commit `fba557f6f53efb53c5fe0b782ca321be5ebb3c77` passed run `29387235173`, and current HEAD `2c4cd4fe484222549fd177455dd413859983ad50` passed run `29411000340`.
- Scope proof: `b1e419e..2c4cd4f` changes only `AGENTS.md`, `PROGRESS.md`, and commit-cadence review artifacts; it changes no `src/`, `test/`, runtime script, workflow, package manifest, or dependency declaration.
- Worktree proof: the tracked tree was clean and `main == origin/main == 2c4cd4f`; the only pre-existing untracked path was `.agents/`, and ignored `output/` evidence remained outside scope.
- Executable baseline: the 110-test passenger/simulation/route/path/overload/environment/checkpoint/oracle/render slice passed in 0.949 seconds before any GM-03e production or test edit.
- Durability boundary: cursor reconciliation and plan/review artifacts are retained for the eventual coherent GM-03e Commit A. Production and tests remain untouched while the extraction plan is adversarially reviewed.

## GM-03e plan review

- Boundary: a stateless, non-retaining `PassengerFlow` receives the current facade only for each call and extracts 16 public algorithms: the 15-method passenger/simulation envelope plus passenger-owned application of bulk route proposals. `Mediator` retains canonical state and every real exact-signature public method; route queries/generation stay in `RoutePlanner`, and GM-03f input/layout scope remains untouched.
- Line contract: the frozen envelopes remove 346 lines and the explicit wrapper/import/install model adds 97, projecting `src/mediator.py` from 984 to 735 physical lines with a 740 target and 750 hard ceiling. `src/passenger_flow.py` targets at most 480 and must remain below 500.
- Findings closed: late per-station color/size/factory lookup; one-time router iterator resolution; per-delivery progression-hook re-resolution; exception-sensitive spawn-counter reset; three fresh ordered graph builds with no reuse; exact generator arrival/route/fallback and callable-lifetime traces; and a durable archived-baseline differential runner with isolated bytecode-disabled children, drift guards, committed canonical bytes/digest, and `--expected` replay.
- Convergence: the boundary, GM-03f scope, and adversarial refutation lanes approved the corrected live-code plan. Pinned Codex and Claude were attempted but failed authentication (Codex HTTP 401 after full retries; Claude expired OAuth); their exact raw failures are preserved and no external approval is claimed.
- Durability boundary: cursor, evidence, decision, plan, prompt, review, and raw failure artifacts are the only GM-03e edits. Production and tests remain untouched; baseline-green facade characterization is next.

## GM-03e TDD and production extraction

- Baseline-green facade phase: 12 new signature/effect characterizations passed against untouched `2c4cd4f` in 0.038 seconds. They freeze all 16 public signatures, late spawn globals, partial failure state, public-hook rebinding, one-time router iterator resolution, three fresh graph phases, live collections, delivery/transfer/boarding order, bulk arrival/route/fallback effects, generator finalization, and the complete waiting scan.
- Expected-red direct phase: while `src/passenger_flow.py` was absent, the isolated direct run reported exactly one loader error, `ModuleNotFoundError: No module named 'passenger_flow'`, and `Ran 1 test`; Ruff check and format were already green for the 12-test direct contract and its support module.
- Green production phase: the 16 frozen bodies now live nearly verbatim in a dependency-light, stateless `PassengerFlow`; `Mediator` installs one instance and keeps exact-signature real public wrappers plus canonical collections, RNG, clocks, progression, routing, globals/factories, pause/speed/game-over state, and public effect hooks. The 24 new tests passed in 0.083 seconds and the focused passenger/simulation/route/path/overload/environment/checkpoint/oracle/render slice passed 134/134 in 1.024 seconds.
- Boundary proof: `src/mediator.py` is 735 physical lines and `src/passenger_flow.py` is 448. The direct test/support files are 498 and 387 lines, facade/effect modules are 472 and 489, and differential runner/support files are 387 and 422; every new handwritten file remains below 500. A fresh import loads none of pygame, mediator, entity, graph, progression, route planner, simulation context, travel plan, rendering, or UI modules, and `PassengerFlow.__slots__ == ()` prevents retained host/callback state.
- Identity proof: protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and training remains `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93`. Content changes intentionally to `877a19b5c609dda20ee460a6f31f1f73c02732cbc3d90cf45a62235a71ee63f3` because the runtime source boundary changed.

## GM-03e archived-baseline differential

- `scripts/verify_passenger_flow_differential.py` materializes exact baseline `2c4cd4fe484222549fd177455dd413859983ad50` through `git archive`, runs baseline and candidate in separate bytecode-disabled child processes, asserts target-module origins, and hashes both runtime source trees plus the verifier before and after execution to fail on drift without checking out or mutating either tree.
- The canonical artifact contains two cases, five records, and 80 mutation-sensitive events. It records normalized structured observations, full canonical checkpoints, both RNG streams, outcomes, and event cursors while distinguishing pause/speed/spawn/waiting behavior; three graph builds and consumers; two delivery hooks plus transfer and boarding; arrival/route/fallback effects; adjacent live-list skipping; destination finalization; reducer/plan/delivery callable release; and proposal iterator finalization.
- Baseline, candidate, canonical artifact, and required `--expected` replay are byte-identical at 110,080 bytes with SHA-256 `d096c039cc613e70b38f6a137f83aaaa1b1404626040801d012fe29e9856da32`. Baseline and candidate runtime-tree hashes differ as expected because the source extraction is present, while their behavior evidence bytes are exact.
- A process refuter proved that unspecified text attributes would let Windows `core.autocrlf=true` add one byte on clean checkout and break raw equality. Exact-path `.gitattributes` rules now force LF for the canonical artifact and summary; a temporary-index clean-checkout simulation preserved 110,080 bytes and the exact `d096c039...` digest, and `--expected` replay against that rematerialized copy passed.

## GM-03e local validation and implementation review

- Full py313 core passed 560 tests in 5.819 seconds with 12 expected optional-RL skips and no failures/errors. The exact `output/venv-rl` Python 3.13.10 environment passed 563/563 in 11.377 seconds with no skips, failures, or errors, including the optional SB3/RecurrentPPO integrations.
- Ruff check and format pass for every changed Python file. `git diff --check` exits zero; five LF-to-CRLF working-copy conversion warnings are informational. Changed-path pre-commit passes all 36 hook-safe paths; the UTF-16LE Claude plan failure and Codex stdout failure remain exact recaptured bytes and are intentionally excluded from the EOF/trailing-whitespace mutators. Exact scoped staging, cached audits, Commit A, push, and exact remote CI remain pending.
- Two independent semantic implementation lanes returned `CLEAN` after method-by-method comparison to `2c4cd4f`, direct lifetime/evaluation-order analysis, focused live tests, and signature/import/retention/size checks. A process/evidence lane found stale status, copied model pins, an inaccurate warning description, and the Windows EOL portability defect; all were accepted and closed. Its final review returned `CLEAN` after refreshing the full pre-staging scope, fingerprints, hashes, line budgets, clean-checkout replay, documentation, and `.agents/` exclusion.
- Fleet-pinned external implementation review was retried after Codex CLI 0.144.6 verification. Codex exhausted WebSocket and HTTPS retries with HTTP 401 missing authentication; the fleet-pinned Claude invocation failed because its OAuth session expired. Exact failure outputs are preserved, neither lane reviewed the code, and no external approval is claimed.
- Commit-readiness audit: the intended/live scope sets are equal at 38 paths. Exact scoped staging contains those 38 paths, has no unstaged tracked file, and leaves only the pre-existing `.agents/skills/multi-cli-review/SKILL.md` untracked. Hook-safe cached diff/check, high-confidence credential scan, dependency-declaration scan, staged LF attributes, artifact sizes, and `.agents/`/ignored-output exclusion all pass. The full cached whitespace check reports only the byte-verbatim Codex stdout capture's original trailing spaces; that exact raw file and the UTF-16LE Claude failure are excluded from mutating whitespace/EOF checks and remain authentic recaptures.
- Durability boundary: implementation, tests, canonical differential evidence, architecture/progress, parent cursor/evidence/decision, and iteration review artifacts are staged as one coherent local unit. GM-03e Commit A has not yet been committed, pushed, or remotely validated.

## GM-03e Commit A - remote implementation gate

- Commit: `7ac89cf100e13a256ec3cbe7550d3e6926a31d23` (`refactor: extract passenger flow [GM-03e:A]`).
- Push: public `origin/main` advanced from `2c4cd4f` to `7ac89cf` after owner/repository visibility, configured URL, default branch, and expected remote parent were verified.
- Remote workflow: [run 29719845761](https://github.com/yanfengliu/python_mini_metro/actions/runs/29719845761) succeeded for the exact commit. API timestamps show `build` ran from 05:44:53Z through 05:45:32Z (39 seconds) and `rl-smoke` from 05:44:54Z through 05:48:33Z (3 minutes 39 seconds).
- Commit B purpose: durably bind the passenger-flow extraction, clean-checkout differential, local validation, and review results to A's exact green remote result before GM-03f changes input/layout ownership.

## GM-03e Commit B - remote finalization

- Commit: `7ff9d9c4e0cee91898d84ce29c13641201f6ac83` (`docs: finalize passenger flow extraction [GM-03e:B]`).
- Push: public `origin/main` advanced from implementation Commit A `7ac89cf` to evidence-only Commit B `7ff9d9c`.
- Remote workflow: [run 29720233286](https://github.com/yanfengliu/python_mini_metro/actions/runs/29720233286) succeeded for the exact commit. API timestamps show `build` ran from 05:54:36Z through 05:55:12Z (36 seconds) and `rl-smoke` from 05:54:36Z through 05:58:26Z (3 minutes 50 seconds).
- Outcome: GM-03e is remotely finalized. GM-03f opens from this exact green baseline and records B's result in its Commit A transaction as required by D-007.

## GM-03f - input and layout coordination extraction

- Baseline: remotely finalized GM-03e Commit B `7ff9d9c4e0cee91898d84ce29c13641201f6ac83`. The exact focused player/render command passed 75/75 and the exact broader interaction/progression/path/environment/render command passed 156/156 before production changes.
- Plan review: two independent live-code lanes found and closed TDD-order, LF portability, differential drift/cardinality, numeric-global resolver, subclass/type-precedence, bound-method capture, and file-size acceptance gaps. Both final re-reviews returned `CLEAN`. The fleet-pinned external launch was rejected before execution at the repository-export authorization boundary, so no external review or approval is claimed.
- TDD: the final 19-signature and mutation-sensitive facade characterization is baseline-runnable and passes 10/10 against both archived `7ff9d9c` source and the candidate. The isolated direct module first failed exactly one test with `ModuleNotFoundError: No module named 'input_coordinator'` and `Ran 1 test`. After implementation and adversarial coverage strengthening, the direct, edge, and facade surface passes 22/22.
- Implementation: dependency-light `InputCoordinator` is stateless through `__slots__ = ()`, imports no pygame/game domain at runtime, retains no host or callback, and receives only a call-scoped structural host plus late resolver thunks. `Mediator` keeps every canonical field and real public method while shrinking from 735 to 605 lines; the coordinator is 391 lines, the largest new direct test is 487 lines, and the largest differential file is 308 lines, so every new Python file remains below 500 lines.
- Differential: isolated bytecode-disabled archived-baseline and candidate children produced the same four cases, 16 records, 90 mutation-sensitive events, 7,123 bytes, and SHA-256 `147f90d827a9b4c3fb17f0aae212e2603c5c6bdc99915a87bbfde29f8d699f05`; committed expected replay matched those exact bytes. The 3,047-byte summary has SHA-256 `1a2bab0f45f796be519e33771d6940b9ac6bb06bc1b97d33eac78a90748f6b5f`. Module origins and pre/post runtime/verifier hashes were stable, both artifacts have zero carriage returns plus a final LF, and a separate `core.autocrlf=true` checkout remained clean while external-output `--expected` replay passed.
- Local regression: the frozen broader consumer command remains 156/156. The full py313 suite passes 582 tests with 12 expected optional-RL skips; the exact RL environment passes 585/585 with no skips. Ruff check and format pass for all 11 changed Python files.
- Contract identity: protocol `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, task `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, promoted default history `8c2959aac108ea5b16b977d8fe5e0f9adff795dc2e38a7d233354f28319d3602`, and training `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93` remain unchanged. Content/source identity intentionally changes to `0bb4d066611244e41ef6c453631c5e4dbc3db76321cee4d64ca099347e52bef3` under the existing drift contract.
- Review: the semantic lane returned `CLEAN`. The process/test lane found and closed missing index identity/bool forwarding, speed-active truth-table, uncovered edge outcomes, live-list and late-type timing, and final baseline-replay defects; after the fixes it found every executable coordinator statement covered by the 582-test discovered suite and the live code/test surface semantically clean. Durable documentation was then refreshed to the final counts and evidence, and final re-review returned `CLEAN`.
- Delivery audit: pre-commit passed end-of-file, trailing-whitespace, Ruff, and Ruff-format hooks across the exact 28 transaction paths. Exact staging contains those 28 paths with no missing or extra path, 3,393 insertions and 212 deletions, no unstaged tracked delta, no dependency/workflow declaration, and no recognized credential-token signature; cached diff checking and cached LF artifact bytes are clean.
- Commit A delivery: exact implementation commit `c676c30832d934449ca81ea5473ecaa492b8d001` passed its exact remote workflow; evidence-only Commit B is active.

## GM-03f Commit A - remote implementation

- Commit: `c676c30832d934449ca81ea5473ecaa492b8d001` (`refactor: extract input coordinator [GM-03f:A]`).
- Push: public `origin/main` advanced from remotely finalized GM-03e Commit B `7ff9d9c` to implementation Commit A `c676c30` after the expected parent and public origin were verified.
- Remote workflow: [run 29724753115](https://github.com/yanfengliu/python_mini_metro/actions/runs/29724753115) succeeded for the exact commit. GitHub job timestamps show `build` ran from 07:29:02Z through 07:29:41Z (39 seconds) and `rl-smoke` from 07:29:02Z through 07:32:42Z (3 minutes 40 seconds).

## GM-03f Commit B - remote finalization

- Commit: `be0b1e1812c126e7472a3ed56fe4a66f62d17122` (`docs: finalize input coordinator extraction [GM-03f:B]`).
- Push: public `origin/main` advanced from implementation Commit A `c676c30` to evidence-only Commit B `be0b1e1`.
- Remote workflow: [run 29725101133](https://github.com/yanfengliu/python_mini_metro/actions/runs/29725101133) succeeded for the exact commit. GitHub job timestamps show `build` ran from 07:35:38Z through 07:36:11Z (33 seconds) and `rl-smoke` from 07:35:40Z through 07:39:20Z (3 minutes 40 seconds).
- Outcome: GM-03 is remotely finalized through GM-03f. GM-04a opens from this exact green baseline and records B's result in its Commit A transaction as required by D-007.

## GM-04a - isolated pin contract baseline and plan review

- Live baseline: `main == origin/main == be0b1e1`; only the pre-existing `.agents/` tree is untracked. `node_modules/civ-engine` is a junction to the unrelated clean sibling at version 2.4.1, commit `2632daca2ea1d1330cf1270962941005354f775b`, and runtime digest `8da72fd76e9f513773bb5f63c899321ffd7a9ef6dbb0cf82d2aec3dbba481971`.
- Node baseline: `npm test` registers 44 tests and reports 25 pass plus 19 failures attributable to the live sibling differing from pinned version 2.2.0, commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, and runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`. The parent plan's 41-test count is corrected; final GM-04c evidence must retain all 44 baseline test names and report the exact larger post-change suite.
- Plan review: three independent live-code lanes converged on a strict checked-in descriptor; package/lock/CI parity; a repo-owned ignored checkout outside `node_modules`; realpath and ESM-resolution identity before execution; no sibling mutation; Windows-safe setup; non-overridable location mismatch; and attributable path/version/commit/digest diagnostics. The selected root is `/.civ-engine-pin/`; GM-04a enforces the contract, GM-04b adds the public setup/verifier and pre-hooks, and GM-04c records the final clean and mismatch proofs.
- Review boundary: the fleet-pinned external workflow is not retried because the established repository-export authorization boundary has not changed. No external reviewer read this plan and no external approval is claimed.

## GM-04a - TDD, implementation, and local validation

- TDD: the first isolated pin-contract test failed at module load with `ERR_MODULE_NOT_FOUND` because `scripts/civ-engine-pin.mjs` did not exist. After the initial loader, the focused contract reported four passes and one expected static-wiring failure because `.npmrc` was absent. The final split pin/provenance/source suite passes 22/22.
- Implementation: the frozen descriptor pins credential-free origin `https://github.com/yanfengliu/civ-engine.git`, root `/.civ-engine-pin/`, version 2.2.0, commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, and runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`. Package, generated lock, `.npmrc`, ignore rule, CI checkout/build, recursive version checks, and provenance all consume that contract; Node support is truthfully bounded at 20.6 or newer.
- Physical identity: the live retained pin is a clean detached physical checkout at the exact descriptor commit with 365 runtime files and the exact descriptor digest; `node_modules/civ-engine` resolves to it. Regressions reject configured-root junctions, top-level `dist` junctions, nested resolution shadows, conditional runtime-entry mismatches, stripped summaries, and spread or in-place full-state forgery under both normal and `--allow-dirty` policy. The unrelated sibling remains clean on `main` at `2632daca2ea1d1330cf1270962941005354f775b`.
- Node validation: the final serial `npm test` passes 56/56 while retaining all 44 frozen pre-GM04 names. One overlapping parent/reviewer run reported 54/56 because two recursive children observed unstable source capture while the independent reviewer suite was active; ten immediate paired source captures were stable, the reviewer run passed 56/56, and the serial parent rerun passed 56/56. A public dirty-attributed pass completed as `recursive-2026-07-20T08-55-57-969Z-f9f3ba5c` with outcome `no-fix-candidate`; exact clean execution remains the Commit A CI and GM-04c proof.
- Python validation: full py313 passes 582 tests in 5.499 seconds with 12 expected optional-RL skips. The exact `output/venv-rl` Python 3.13.10 environment passes 585/585 in 9.910 seconds with no skips, failures, or errors.
- Install and audit: `npm ci --omit=dev` followed by `npm ls --depth=0` is clean with only `civ-engine@2.2.0 -> ./.civ-engine-pin`. On Node 24.12.0/npm 11.7.0, the root full lock audits at zero vulnerabilities, the actual pin build lock reports one moderate `js-yaml` advisory with zero high/critical, and the pin runtime-only graph audits at zero. An earlier reviewer snapshot counted nine moderate dependency instances; the final exact audit counts one unique vulnerable package, and both results agree there is no high/critical blocker.
- Review: three independent implementation lanes found and closed configured-root and `dist` alias escapes, summary/full-state policy bypasses, unsafe PowerShell continuation, Node-floor drift, dangerous descriptor paths, incomplete workflow/credential/order assertions, missing audit attribution, and oversized mixed provenance tests. Final provenance, supply-chain/workflow, and test/documentation re-reviews all returned `CLEAN`; the largest affected production file is below 500 lines and the split tests/helpers are 315/262/207/346 lines.
- Hook and syntax gates: two sandboxed task-cache pre-commit attempts timed out while installing the hook environment before checks ran. The same exact 34-path invocation through the normal cache then passed check-yaml, end-of-file, and trailing-whitespace; Ruff and Ruff-format correctly skipped because no Python file changed. The direct fallback had already checked all 34 final-LF/whitespace surfaces and ten MJS syntax targets, and it exposed the inline provenance command as invalid YAML. That accepted finding was fixed with a folded block, PyYAML then parsed the workflow, all three JSON files parsed, all 150 registry lock entries retained integrity, and the final Node rerun passed 56/56.
- Commit-readiness audit: exact scoped staging contains 34 paths, 3,769 insertions, and 292 deletions; cached whitespace checking exits zero, the added-line high-confidence credential-signature scan reports zero matches, no tracked delta remains outside the index, and the only untracked surface is the pre-existing `.agents/` tree.

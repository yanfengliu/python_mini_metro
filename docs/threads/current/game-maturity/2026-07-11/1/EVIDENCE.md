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

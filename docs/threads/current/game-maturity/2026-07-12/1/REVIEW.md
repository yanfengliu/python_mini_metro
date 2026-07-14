# GM-02 plan and implementation review synthesis

Status: APPROVED for test-first implementation after correction and re-review

## Coverage

- Manifest/API lane inspected v1/v2 parsing, canonical bytes, trust boundaries, factory inputs, resume/evaluation, and focused tests; baseline 23/23 passed.
- Temporal lane inspected installed Gymnasium/SB3/SB3-Contrib 2.9.0 reset, terminal, timeout-bootstrap, recurrent-mask, and vector-wrapper behavior; baseline terminal/recurrent/roundtrip checks passed 3/3.
- Resource lane inspected live observation/model shapes, SB3 recurrent buffers, Windows process-tree measurement, benchmark comparability, and default-promotion boundaries.
- The driver directly reran manifest, CLI, vector/recurrent training, and legacy compatibility under `output/venv-rl`: 37/37 passed before implementation.

## Disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | Manifest v2 could claim multiscale history before runtime supported it | Resolved with an intermediate contiguous-only guard and actual-layout emission |
| High | Fresh default could change before resource profiling | Resolved; eight-contiguous remains default through GM-02c |
| High | Original fallback had no promotion-eligible candidate | Resolved with an exact ten-frame fallback or full matched rerun |
| Medium | Descriptor/fingerprint had dual sources and open semantics | Resolved with one descriptor input, derived summary/digest, exact keys, and fixed literals |
| Medium | Ring/reset/terminal lifecycle and aliasing were underspecified | Resolved with circular per-slot state, strict terminal validation/copy order, and exact-byte tests |
| Medium | Benchmark safety and process-tree metrics were post-hoc or ambiguous | Resolved with preregistered numeric gates, repeated counterbalanced runs, instantaneous aggregate working set, and explicit throughput/allocation metrics |

All three lanes re-read the corrected plan and returned APPROVED with no remaining substantive finding.

## GM-02a implementation review

Three independent live-diff finders covered manifest trust/schema, train/evaluate/legacy ordering, and architecture/docs/resource boundaries. The manifest and CLI lanes were clean. The architecture lane found two test-coverage defects: the new trainer-identity modules were not each mutation-tested, and the v2 exact-key branch lacked top-level missing/unknown cases. Both were fixed. The original finder approved the corrections, and an independent refuter verified them with focused tests plus direct parser probes. No substantive implementation finding remains.

| Severity | Implementation finding | Disposition |
| --- | --- | --- |
| Medium | New history/schema allowlist entries were not independently mutation-tested | Resolved; each module now changes trainer identity and trainer-only edits leave content identity unchanged |
| Low | V2 top-level exact-key branch lacked direct missing/unknown regressions | Resolved with required `history` removal and unknown `future` injection cases |

Implementation validation reached 389 core tests with 8 expected optional-RL skips and 389/389 in the exact RL environment, changed-file Ruff/format and pre-commit, a two-frame dummy-video app smoke, fresh v2 train/evaluate, genuine v1 evaluate/resume into v2, and unchanged protocol/task/content fingerprints. Local Node remained at the known 25/44 result because the live sibling is civ-engine 2.4.1 rather than the repository pin 2.2.0; pinned CI remains authoritative until GM-04.

## GM-02b implementation review

Three independent live-code lanes reviewed vector lifecycle/correctness, real SB3/RecurrentPPO compatibility, and allocation/cleanup/documentation. The finders independently reproduced two medium fail-closed defects: stepping before reset dispatched work before rejection, and validation failures after an underlying transition left stale history usable. After those fixes, a refuter forced reset output assembly to fail and found the wrapper initialized despite `reset()` never returning. The final implementation rejects before `step_async` delegation, poisons all history on any reset/step failure, marks reset successful only after owned output assembly, and closes the base on failed construction. All three lanes then returned clean.

| Severity | GM-02b finding | Disposition |
| --- | --- | --- |
| Medium | Pre-reset `step()` dispatched an action before rejecting in `step_wait()` | Resolved with a pre-delegation `step_async()` guard and no-dispatch regression |
| Medium | Malformed consumed step or reset data left stale/cross-episode history usable | Resolved with zeroing poison state that requires a successful explicit reset |
| Medium | Reset output-assembly failure initialized a wrapper whose reset never completed | Resolved by assembling inside the failure guard and setting initialized only after success |
| Low | Candidate-size allocation, construction cleanup, and intermediate docs were incomplete | Resolved with exact 64,198,656-byte ring and 5,971,968-byte output assertions, failed-construction close coverage, and explicit dormant-runtime documentation |

Refutation included synthetic exact-byte tests, real `DummyVecEnv -> VecMonitor`, RecurrentPPO timeout bootstrap with a 36-channel terminal stack, and a spawned two-slot `SubprocVecEnv -> VecMonitor` lifecycle probe. Final local validation reached 395 core tests with 8 expected optional-RL skips and 395/395 in the exact RL environment, 8/8 focused wrapper/fingerprint checks, changed-file Ruff/format and pre-commit, diff checks, and a two-frame dummy-video app smoke. Protocol, task, and content fingerprints remain unchanged; trainer identity intentionally changes. Local Node remains at the known 25/44 result because the live sibling is civ-engine 2.4.1 rather than the repository pin 2.2.0.

## GM-02c implementation review

Three independent live-diff lanes covered manifest/CLI ordering and persisted compatibility, real temporal/recurrent runtime behavior, and CI/resource/documentation truth. The only runtime defect was a medium coverage gap: the initial episode-mask regression used a fake prediction policy and could not catch SB3 rollout integration failures. It was replaced with a real RecurrentPPO `policy.forward` probe over a two-step horizon, which records `[[True], [False], [True]]`. CI review also tightened default and legacy exact-history assertions, renamed the expanded workflow step, and required final cursor/evidence reconciliation before Commit A.

| Severity | GM-02c finding | Disposition |
| --- | --- | --- |
| Medium | Episode-start mask test used a fake model instead of RecurrentPPO rollout collection | Resolved with real `RecurrentPPO.learn` mask capture and independent refutation |
| Medium | Default Windows smoke could accept equal-count eight-frame multiscale history | Resolved with exact contiguous layout/offset/fingerprint assertions for default and legacy lanes |
| Medium/Low | Persistent state/evidence lagged the implemented and reviewed stage | Resolved before Commit A with exact local gates, fingerprints, artifact hashes, and resume actions |
| Low | Workflow step name omitted the new named-history lifecycle | Resolved by naming the recurrent history and legacy PPO scope |

The manifest reviewer initially questioned the lack of a committed frozen historical model, then retracted the finding after directly authenticating the existing 21,784,628-byte pre-GM-02 v1 recurrent artifact and verifying the driver's evaluate/resume/re-evaluate evidence. The plan requires exercising genuine persisted bytes, not committing a large binary; the repeatable old-`VecFrameStack` unit mechanism test complements that exact-byte smoke. Final refutation passed 29/29 runtime tests and 59/59 manifest/history-focused tests with no remaining substantive finding.

Final local validation reached 399 core tests with 11 expected optional-RL skips and 399/399 in the exact RL environment, changed-file Ruff/format, diff checks, a two-frame dummy-video app smoke, a real named-history two-worker fresh/evaluate/resume/evaluate lifecycle, and a persisted-v1 evaluate/resume/re-evaluate lifecycle. Local Node remained at the known 25/44 result because the live sibling is civ-engine 2.4.1 rather than the repository pin 2.2.0; the expanded pinned Windows CI gate is authoritative.

## External CLI limitation

The required Codex 0.144.1 and Claude Fable review commands were prepared after reading the canonical runbook. The platform rejected the combined external action because sending repository context to Claude was not an approved third-party data export. No repository context was routed around that control and neither external report was treated as approval. Three independent in-process live-code lanes plus separate refutation compensate for GM-02a/02b coverage; retry the external CLIs in the next high-risk iteration if the platform permits it.

## GM-02d benchmark and promotion plan review

Three independent live-code lanes reviewed the GM-02d harness, installed SB3/SB3-Contrib 2.9.0 timing and recurrent-buffer semantics, Windows process-tree measurement, promotion gates, and default-history ownership. The first pass found one high default-selection defect, one high schedule-horizon defect, and several medium measurement/provenance ambiguities. The plan was split into GM-02d1 harness A/B and GM-02d2 clean-commit campaign A/B so measured workers can name one remotely verified source commit. All findings were corrected and all three lanes approved the final plan.

| Severity | GM-02d plan finding | Disposition |
| --- | --- | --- |
| High | Changing only `DEFAULT_FRAME_STACK` would promote contiguous twelve rather than the reviewed multiscale descriptor | Resolved with one shared default-history descriptor/factory used by fresh CLI and default environment construction |
| High | `learn(total_timesteps=2048)` would drive the measured update's linear learning rate to zero | Resolved with production-horizon `_setup_learn()` and two explicit collect/progress/train iterations |
| Medium | Nominal batch bytes and `4096` rows ignored recurrent padding | Resolved by recording every actual padded minibatch, valid and padded rows, normalized inputs, and separately named rates |
| Medium | Full-lifecycle process-tree completeness, PID reuse, cadence, and dirty-tree semantics were incomplete | Resolved with retained handles/creation times, 50 ms absolute cadence, gap/acquisition failure gates, explicit `.agents/**` exclusion, and source/script digests |
| Medium | MAC scope omitted live post-LSTM MLPs and lacked a defensible unit | Resolved as one-row inference MACs covering CNN, actor/critic LSTMs, both MLP stacks, and action/value heads |
| Medium | Ten-frame fallback eligibility was ambiguous | Resolved with a fresh interleaved baseline campaign and the same preregistered gates |

The historical 3.909 GiB cap remains an explicitly rounded, non-method-equivalent guardrail; the freshly matched eight-contiguous relative control is primary. GM-02d proves only engineering safety, while delivery efficacy remains GM-12. Raw plan reviews are preserved as `raw/gm02d-plan-resource.md`, `raw/gm02d-plan-harness.md`, and `raw/gm02d-plan-windows.md`.

## GM-02d1 implementation review

Three independent live-diff lanes reviewed the completed benchmark harness from contract/campaign, Windows supervision, and resource/math perspectives, then re-read the fixes and returned clean. The review confirmed that the campaign now distinguishes a valid non-promotion result from an operationally invalid or incomplete run, durably records and aborts on source drift, validates the exact production workload and every evidence-bearing allocation/rate, and cleans supervised process trees across startup and exception paths.

| Severity | GM-02d1 implementation finding | Disposition |
| --- | --- | --- |
| High | Operationally invalid or incomplete campaigns could finish with exit code zero | Resolved with an explicit `operationallyValid` aggregate contract and nonzero CLI exit while preserving the written decision artifact |
| High/Medium | Source state was checked only at campaign start, leaving post-worker drift and script-provenance races | Resolved with clean-commit checks before every worker, post-worker source and profile/worker-script hashes, durable drift evidence, and immediate campaign abort |
| Medium | Worker validation accepted incomplete workload, storage, MAC, tensor, timing, and rate evidence | Resolved with exact seed/task/protocol/training fingerprints, batch/epoch/horizon/thread settings, history ages, actual storage shapes/dtypes/bytes, live MAC components, recurrent padding/masks/normalized inputs, measurement windows, and recomputed rates |
| Medium | The supervisor could block before readiness, deadlock on child pipes, or leave processes behind on pre-ready and exception failures | Resolved with a bounded ready timeout, concurrent stdout/stderr draining, tracked-tree termination before launcher cleanup, and explicit cleanup regressions |
| Medium | PID reuse, descendant lifetime, and ordinary exit races could invalidate or undercount process-tree evidence incorrectly | Resolved with retained creation-time identities, continued tracking after the root exits, fatal live-query failures, and a separately recorded nonfatal exit-between-snapshot-and-working-set warning |
| Low | The first surviving-descendant regression exercised only root to child despite claiming a grandchild | Corrected to a true root to intermediate to grandchild topology before final refutation |

Final refutation passed 46/46 focused contract checks, 36/36 resource/campaign/Windows checks, and 4/4 exact-RL resource integration checks. A real twelve-frame, 128-step worker probe populated offset age 128 and confirmed exact `uint8` ring, one-step, and rollout storage; independent live-model introspection matched the analytical one-row inference estimate at 110,226,752 MACs. All final review lanes were clean, every changed source and test file remained below 500 lines, and the external Codex/Claude review limitation described above still applies because repository-context export was not approved.

## GM-02d2 measured promotion review

The clean-source primary campaign was operationally invalid because one control repeat violated the preregistered sampling contract; no aggregate from that campaign was accepted as promotion evidence. A fresh interleaved fallback produced eight valid matched rows and promoted exact ten-frame layout `decision-history-10-fallback-v1`. Two independent plan reviewers then grounded the default-selection path against live CLI/training/resume code before implementation, and three implementation lanes independently reviewed code, compact evidence/documentation, and the corrected final diff.

| Severity | GM-02d2 finding | Disposition |
| --- | --- | --- |
| Medium | Explicit fresh PPO would silently inherit the new recurrent history if the resolver remained algorithm-independent | Resolved; recurrent omission uses the exact ten-frame factory, explicit PPO omission remains contiguous eight, explicit selectors win, and resume/evaluation inherit persisted history |
| Medium | Incomplete, duplicate, invalid, or settings-drifted campaigns could publish partial/non-matched medians and misleading memory/throughput failure reasons | Resolved; structural prerequisites suppress all four medians and three measurement gates, with one priority reason before performance gates are evaluated |
| Medium | The first compact artifact recorded Windows CRLF bytes rather than canonical Git bytes, omitted per-row batch/epoch settings, overstated per-run byte authentication, and retained the old non-fail-closed primary decision as current | Resolved; all 17 rows now carry exact settings, live decisions recompute exactly, old raw-summary metrics are explicitly non-authoritative, the valid-target cap check is separately scoped, authentication wording is exact, and canonical LF identity is pinned |
| Low | Model parameter math and campaign-summary KiB labels were inconsistent with exact evidence | Resolved to 1,450,005 CNN/recurrent/head core parameters, 1,491,221 full live policy parameters, and exact 448,745-509,376-byte / 438.2-497.4 KiB summary sizes |

The code lane returned clean after 20/20 core and 39/39 exact-RL focused tests. The documentation/evidence lane found three medium and two low issues, then returned clean after rechecking all 51 raw-file digests, both summary identities, canonical line endings, every row setting, live decision recomputation, and parameter/unit corrections. The final refuter independently reproduced default/resume/PPO behavior, both decisions, raw digests, canonical artifact identity, workflow parsing, and file-size bounds and returned clean.

The required external Codex CLI was updated to 0.144.3 and a task-specific `gpt-5.6-sol` review was prepared, but the platform rejected sending the uncommitted repository diff to the external service. The same export was not rerouted through Claude. The exact prepared prompts are preserved, no external report is treated as approval, and the three in-process live-code lanes are the completed review basis for this iteration. Raw in-process reports are preserved as `raw/gm02d2-plan-default.md`, `raw/gm02d2-plan-refuter.md`, `raw/gm02d2-impl-code.md`, `raw/gm02d2-impl-docs.md`, `raw/gm02d2-impl-docs-rereview.md`, and `raw/gm02d2-impl-refuter.md`.

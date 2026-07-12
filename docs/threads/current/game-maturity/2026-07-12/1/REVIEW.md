# GM-02 plan review synthesis

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

## Implementation review

Three independent live-diff finders covered manifest trust/schema, train/evaluate/legacy ordering, and architecture/docs/resource boundaries. The manifest and CLI lanes were clean. The architecture lane found two test-coverage defects: the new trainer-identity modules were not each mutation-tested, and the v2 exact-key branch lacked top-level missing/unknown cases. Both were fixed. The original finder approved the corrections, and an independent refuter verified them with focused tests plus direct parser probes. No substantive implementation finding remains.

| Severity | Implementation finding | Disposition |
| --- | --- | --- |
| Medium | New history/schema allowlist entries were not independently mutation-tested | Resolved; each module now changes trainer identity and trainer-only edits leave content identity unchanged |
| Low | V2 top-level exact-key branch lacked direct missing/unknown regressions | Resolved with required `history` removal and unknown `future` injection cases |

Implementation validation reached 389 core tests with 8 expected optional-RL skips and 389/389 in the exact RL environment, changed-file Ruff/format and pre-commit, a two-frame dummy-video app smoke, fresh v2 train/evaluate, genuine v1 evaluate/resume into v2, and unchanged protocol/task/content fingerprints. Local Node remained at the known 25/44 result because the live sibling is civ-engine 2.4.1 rather than the repository pin 2.2.0; pinned CI remains authoritative until GM-04.

## External CLI limitation

The required Codex 0.144.1 and Claude Fable plan-review commands were prepared after reading the canonical runbook. The platform rejected the combined external action because sending repository context to Claude was not an approved third-party data export. No repository context was routed around that control and neither external report was treated as approval. The three independent in-process live-code lanes compensate for plan coverage; retry the external CLIs in the next high-risk iteration if the platform permits it.

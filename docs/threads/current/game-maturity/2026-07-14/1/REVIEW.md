# GM-03d review synthesis

## Plan review

Three independent live-code maps covered the extraction boundary/line budget, observable contracts/TDD coverage, and adversarial process/architecture risks. All converged on a stateless, non-retaining `PathLifecycle` that receives an explicit call-scoped host while Mediator remains the canonical owner and public facade for writable topology state.

The code map identified exactly 12 lifecycle methods and rejected adjacent RNG palette, progression, input/action, and general passenger-flow scope. The contract map froze exact creation/removal/button/graph/checkpoint identity and ordering. The refuter rejected a mirrored stateful aggregate because its proxy properties would consume the required size recovery and expand the rebinding surface; it added a 57-line hard wrapper/import/install ceiling, late `Path`/`Metro` factory getters, exact non-transactional removal sequencing, direct rebinding/lifetime tests, and no-generator guidance.

The corrected plan was then reviewed against the live code by three independent lanes. The contracts lane returned `APPROVED`; the refutation/process lane returned `APPROVED`; and a fresh final lane verified the live 1,110-line file, all 12 methods, the 168-line envelope, the `1110 - 168 + 57 = 999` hard arithmetic, late factories, public hooks, state ownership, and TDD/equivalence coverage before returning `APPROVED`. No substantive plan finding remains.

## Frozen acceptance boundary

- Extract only the 12 listed transition bodies into dependency-light `src/path_lifecycle.py`.
- Keep real unchanged public Mediator methods and canonical directly writable lists/maps/flags.
- Retain fresh host reads, dynamic public-to-public dispatch, direct factory getter-call composition, exact snapshots/live iteration, partial failures, identity, and mutation order.
- Target Mediator at most 990 lines and require below 1,000; cap all wrapper/import/install replacement at 57 lines; keep every new handwritten file below 500.
- Add baseline-green facade characterizations before an expected-red missing-module direct contract, then implement and verify against baseline/current differentials plus all local/remote gates.

## External reviewer boundary

Task-specific pinned Codex and Claude plan and implementation prompts are preserved. The user subsequently and explicitly requested that the coherent unit be reviewed and committed, superseding the earlier repository-context-transfer limitation for this review. Codex CLI 0.144.4 was confirmed equal to the current registry release after the global updater could not replace its active in-use binary. The pinned Codex and Claude implementation reviewers were then launched, but both returned HTTP 401 authentication failures; Codex produced only its captured stdout/error log and Claude produced the exact one-line failure. Neither yielded a review or approval. Their raw failure artifacts are preserved, and the runbook fallback is three fresh independent in-process live-code lanes with the external reviewers recorded unavailable until credentials are restored.

## Implementation review

The production extraction is present at 984 physical lines in `src/mediator.py` plus a 235-line dependency-light, stateless `src/path_lifecycle.py`. All 12 frozen facade signatures match baseline `5e6186d8b331207d2a6ec583b7a82f80533f5203`, the first direct/facade production slice passed 26/26, the focused topology slice passed 156/156, core py313 passed 535 tests with 12 expected optional-RL skips, and exact-RL passed 538/538 without skips. Fresh import isolation and unchanged protocol/task/training fingerprints are also proved; the content fingerprint changed intentionally.

The semantic implementation lane returned `CLEAN` after live AST/body normalization, signature comparison, public-hook/fresh-read/factory-lifetime inspection, and focused tests. The process lane returned `NOT CLEAN` for three commit-readiness findings: stale durable state/review docs, an incomplete final proof/review/hook/staging bundle, and missing architecture/project-log coverage. This documentation remediation closes the stale status plus architecture/project-log finding and records the remaining gates without claiming completion.

A separate implementation-test review found one substantive `MEDIUM` gap: the direct/facade suite did not explicitly distinguish closed-loop input `[0, 1, 2, 0]` from generic loop input. The finding is resolved in the live tests. The direct and real-facade pair now passes 20/20, deleting the de-duplication branch produces exactly two assertion failures and no errors, and both changed test files remain below 500 lines at 484 and 450. The strengthened baseline/current differential covers that encoding and is byte-identical across seven actions and nine normalized records at 10,490 bytes, SHA-256 `d6fb9dd21730f381776959c48dab8a9c87f82c7e3387646bf4ce30fd691c978d`; the earlier digest is superseded. The implementation-test re-review verdict is `CLEAN`.

A fresh commit-readiness review retained the semantic verdict `CLEAN` but found four evidence/process defects. First, both palette mutations—changing black fallback and ignoring the unlocked-prefix slice—survived the 535-test core suite. Direct-host and real-Mediator cases now exhaust the eligible prefix while a later locked color remains free; both freeze black selection and prove the external color remains untouched. The focused direct/facade/failure slice passes 27/27, with the direct and failure modules at 495 and 221 lines.

Second, the earlier 10,490-byte differential digest had no durable runner or normalized record, so that claim was not independently auditable. It is superseded by `scripts/verify_path_lifecycle_differential.py` and the commit-bound `gm03d-path-lifecycle-v1` artifact. The runner archives baseline `5e6186d` without checkout/worktree mutation, executes baseline/current children with target source first and bytecode disabled, hashes each runtime tree before and after, and compares seven actions across nine full canonical checkpoints. Baseline, candidate, and `--expected` bytes are identical at 135,371 bytes and SHA-256 `4ceaf17d638f932df6c3ce31cdba8789f56c0ea82748b4b2b6dcbc111d47c668`.

The fresh test/evidence re-review is `CLEAN`. It independently applied both palette mutations and each produced exactly two failures with no errors, one direct and one real-Mediator. It regenerated the full artifact and confirmed its action/record counts, bytes, digest, runtime-tree hashes, summary fields, and `--expected` equality. The post-fix full core suite passes 536 tests with 12 expected optional-RL skips, exact-RL passes 539/539, and Ruff check/format pass across all eight changed Python files.

Third, the durable thread incorrectly said external reviewers were never launched; the corrected external boundary above and raw failure captures close that status defect without inferring approval. Fourth, the prior ordinary `git diff --check` could not cover untracked files, and the separate modified `AGENTS.md` was not named as outside GM-03d. The exact 42-path staged unit now explicitly excludes `AGENTS.md`, `.agents/`, and ignored `output/`; cached diff/check, credential, dependency, and exclusion audits are clean.

The process re-review is also `CLEAN`. It verified the corrected 401 history, explicit `AGENTS.md`/`.agents/`/`output/` exclusions, honest ordinary-versus-cached diff boundary, artifact and runtime-tree hashes, documentation consistency, line limits, and unchanged dependency declarations. Final changed-path hooks pass all 41 hook-safe paths. The UTF-16LE Codex stdout is classified as binary and remains byte-identical; the UTF-16LE Claude capture is excluded only from the EOF fixer because it appends an invalid single byte, then verified separately by SHA-256.

Implementation review is re-converged: semantic, test/evidence, and process lanes are `CLEAN`, and both accepted test mutations are rejected in two layers. Changed-path hooks and exact staged audits are clean.

## Remote implementation gate

Commit A `9321dcde0a0b062bb4953a3ac75d6f2bdaa06c3a` passed exact [run 29386046847](https://github.com/yanfengliu/python_mini_metro/actions/runs/29386046847): `build` and `rl-smoke` each completed successfully in 35 seconds by API timestamps. Evidence-only Commit B is the remaining GM-03d transaction.

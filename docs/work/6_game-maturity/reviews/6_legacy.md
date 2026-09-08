# GM-03a mediator test-suite split review

## Scope

Behavior-neutral split of `test/test_mediator.py` into one fixture/support module and six behavior-focused test modules. Production mediator decomposition remains deferred to GM-03b through GM-03f.

## Reviewer availability

- External Codex plan review: blocked before launch because repository-context export lacked separate post-disclosure approval; see `raw/codex-plan.md`.
- External Claude plan review: not launched because rerouting the prohibited same export was disallowed; see `raw/opus-plan.md`.
- In-process partition reviewer: completed two rounds and approved the corrected plan.
- In-process adversarial refuter: completed three rounds and approved the corrected plan.
- In-process documentation/process reviewer: completed two rounds and approved the corrected plan.

## Plan findings and disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | The plan referenced a missing exact 57-method allocation artifact | Fixed: `raw/in-process-partition.md` now lists all 57 methods exactly once across the six modules |
| High | Parent state/evidence still directed resume to GM-02e Commit B | Fixed: exact B SHA/run/durations are recorded and the durable cursor now names `[GM-03a:A]` |
| High | Multi-CLI wording required reviewers that the platform had prohibited launching | Fixed: require honest attempt/failure artifacts plus converged independent in-process review; never treat a non-launch as approval |
| Medium | AST-only comparison could silently drop six explanatory in-method comments | Fixed: require both AST equality and dedented source-segment equality |
| Medium | Production guard missed staged and then untracked `src/` changes | Fixed: compare frozen baseline plus ordinary/cached diffs and require empty `git status --short -- src` |
| Medium | A/B language did not state where B's future CI is persisted | Fixed: A/B contents and GM-03b opening evidence boundary are explicit |
| Low | Current pins, refresh preflight, Claude fallback/status audit, and final raw artifact names were absent | Fixed: plan records exact runbook mechanics and the denied machine-level refresh |

## Plan convergence

All three independent in-process reviewers returned `APPROVED` after the final untracked-production guard. External reviewers did not run and are not counted as approvals. Implementation may begin from the exact `60b4174b2bbe2f92ae3abac4a44991f03caa518b` baseline.

## Implementation findings and disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | Persistent state/review/evidence still described planning after the split and green local gates | Fixed: parent cursor, resume steps, ledger, evidence, and this synthesis now name the pre-commit/final-review boundary |
| Low | Architecture called the unchanged entropy-backed fixture “seeded” | Fixed: describe it accurately as a shared per-test mediator fixture |

No reviewer found a Python implementation defect. Verbatim initial reports are preserved in `raw/in-process-implementation-partition.md`, `raw/in-process-implementation-refuter.md`, and `raw/in-process-implementation-docs.md`.

## Implementation validation

- Six fresh-process module runs passed `12/8/8/10/8/11`; the combined suite passed exactly 57/57.
- Frozen-baseline verification passed for 57 unique discovery IDs, 57 test names, three helpers, 60 ASTs, exact per-method source segments, and six comments.
- Core py313 passed 437 tests with 12 expected optional-RL skips; exact RL py313 passed 440/440.
- Ruff check and format passed all seven new Python files; all are 72–270 lines.
- Frozen-baseline, ordinary, cached, and status-based `src/` guards are clean.
- Final pre-commit passed all 33 GM-03a paths with EOF, whitespace, Ruff check, and Ruff format hooks clean and no hook edits.

## Implementation convergence

The partition/code reviewer, adversarial refuter, and documentation/process reviewer each returned `CLEAN` after the stale evidence and inaccurate fixture wording were fixed and pre-commit passed. Their final responses are preserved in `raw/in-process-implementation-final.md`. External non-launch artifacts remain limitations, not approvals. The reviewed GM-03a diff is locally approved for Commit A.

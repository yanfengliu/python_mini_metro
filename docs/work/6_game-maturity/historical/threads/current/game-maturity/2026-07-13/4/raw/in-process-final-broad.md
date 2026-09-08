CLEAN — no remaining post-fix GM-03c finding.

Verified against the current live files:

- All four previously failing `HEAD` differentials now match exactly:
  - bulk reducer lifetime,
  - constrained reducer lifetime,
  - constrained shared-path lifetime,
  - constrained plan-factory lifetime.
- Direct and bulk selection loops currently agree on arrival handling, raw/reduced ranking, strict first-tie behavior, callback timing, and mapping access. The in-frame duplication preserves baseline local lifetimes without current algorithm drift.
- Focused route suite: 55/55 passed.
- Full suite: 509 passed, 12 optional-RL skips.
- Ruff and format checks passed for all 9 changed Python files.
- All 9 public mediator route signatures match `HEAD`.
- Isolated planner import loaded no pygame or domain modules.
- `git diff --check` passed.
- LOC: mediator 1,110; planner 231; every changed test remains below 500.
- No files were edited during review.

The known scope note remains: mediator meets GM-03c’s 1,111 ceiling but still needs GM-03d to cross the repository-wide 1,000-line ceiling.

# GM-03c review diff

Baseline: `00ea38c2dbee3fd51985ae9c52377ae404502e29`

Status: implementation, final in-process review, changed-path hooks, and exact Commit-A remote CI green; evidence-only Commit B pending.

## Production boundary

- Adds dependency-light stateless `src/route_planner.py` for route queries, compression, direct/constrained selection, and lazy boarding/bulk proposals.
- Keeps every public route method and all RNG, graph construction, travel-plan map writes, arrival/removal, and passenger/metro effects in `src/mediator.py`.
- Reduces Mediator from baseline 1,193 lines to 1,110; RoutePlanner is 231 lines.
- Uses explicit arrival/route/fallback bulk phases, an in-frame selection loop for original Python local lifetimes, and direct getter-call composition for original callable resolution/release timing.

## Tests

- Adds `test/route_planner_test_support.py` plus direct query, selection, iterator, and resolution-order modules.
- Adds mediator route-facade and observability modules covering public dispatch, lookup/RNG order, plan identity/ownership, raw-arrival provenance, iterator finalization, fallback guards, local lifetime, and callable lifetime.
- Final compatibility slice passes 144/144; core passes 509 with 12 expected optional-RL skips; exact RL passes 512/512.

## Documentation and review evidence

- Updates `ARCHITECTURE.md`, `PROGRESS.md`, and the parent game-maturity decision/evidence/state ledger.
- Adds the iteration-4 plan, prompts, plan/implementation findings, correction evidence, external non-launch records, and three final clean in-process reports.
- External Codex/Claude review remains unlaunched under the recorded repository-context transfer boundary; the in-process live-code lanes are authoritative.

## Identity and equivalence

- All nine public route-facade AST signatures match baseline.
- Protocol/task/training fingerprints remain unchanged; final intentional content fingerprint is `548d2fbd7a28abeec2ae45ef1c64e5239bc6ff5c7e2d1540336a12ee7c813394`.
- Baseline/current 2,400-step results and 44 canonical checkpoints match exactly, ending at four deliveries without game over.
- Fresh `route_planner` import loads no pygame or domain module.

## Staging boundary

Changed-path pre-commit passed all hooks across the 37-file Commit-A unit without rewrites. The complete cached stat was 37 files changed, 2,955 insertions, and 152 deletions: six tracked modifications and 31 additions, with no deletion or rename. `git diff --cached --check` passed; the staged high-confidence credential scan found zero hits; no dependency declaration was staged; and staged paths contained zero `.agents/` or `output/` entries. Ignored `output/` evidence remained excluded.

## Remote implementation gate

Commit A `1b751e47cd3edce3556b32880a26851db3a072d2` advanced `origin/main` from `00ea38c` and passed exact [run 29351838271](https://github.com/yanfengliu/python_mini_metro/actions/runs/29351838271): `build` succeeded in 34 seconds and `rl-smoke` in 3 minutes 43 seconds. Commit B changes only persistent/thread evidence.

# GM-03d review diff

Baseline: `5e6186d8b331207d2a6ec583b7a82f80533f5203`

Status: production extraction, corrected reproducible local proofs, clean three-lane re-review, changed-path hooks, exact staged audit, and exact Commit-A remote CI green; evidence-only Commit B pending.

## Current production boundary

- `src/path_lifecycle.py` now contains the 12 exact path-transition algorithms as a 235-line stateless, non-retaining component; `src/mediator.py` is 984 physical lines from the 1,110-line baseline.
- Canonical writable collections/maps/flags and every real public compatibility method remain on Mediator. Public hook/factory lookup, snapshot/live mutation, identity, exception, and partial-state timing remain the frozen compatibility boundary.
- Palette/RNG, progression, input/action, general passenger flow, reward/history/training, and dependency declarations remain outside this extraction.

## Test and evidence boundary

- TDD recorded 102 baseline topology tests green, 16 facade distinctions baseline-green, an isolated expected-red missing-module direct contract, then the first production direct/facade slice green at 26/26.
- All 12 public facade AST signatures match baseline. Fresh import loads none of pygame, mediator, entity, graph, route planner, progression, simulation context, or travel plan. The focused topology slice is 156/156; after final review fixes, core py313 is 536 tests plus 12 expected optional-RL skips and exact-RL is 539/539 without skips.
- Protocol, task, and training fingerprints are unchanged; content changed intentionally. Review-driven cases now reject explicit closed-loop de-duplication plus unlocked-palette prefix and black-fallback mutations in both direct and real-facade layers.
- The unauditable 10,490-byte digest is superseded by a commit-bound non-mutating runner and one canonical seven-action/nine-record artifact. Archived baseline, current source, and the `--expected` replay produce identical 135,371-byte bytes at SHA-256 `4ceaf17d638f932df6c3ce31cdba8789f56c0ea82748b4b2b6dcbc111d47c668`; the machine-readable summary also authenticates distinct baseline/current runtime trees.
- External Codex and Claude were attempted after explicit user review authorization and both failed authentication with HTTP 401, so no external approval exists. Fresh in-process semantic, test/evidence, and process lanes are `CLEAN`. Changed-path hooks pass all 41 hook-safe paths while both UTF-16LE raw captures remain digest-verified; exact staging/cached-diff/credential/dependency/exclusion checks are clean and remote A/B CI is not yet complete.

## Current worktree boundary

The owned 42-path GM-03d unit comprises parent state/evidence/decision edits, this iteration's plan/review/prompt/differential artifacts, the durable differential runner, architecture/progress updates, `src/path_lifecycle.py`, the Mediator facade rewiring, and focused direct/facade tests and support. Its staged scope is audited at 2,959 insertions and 160 deletions. The separately modified `AGENTS.md`, pre-existing untracked `.agents/` tree, and ignored `output/` are excluded.

## Remote implementation gate

Commit A `9321dcde0a0b062bb4953a3ac75d6f2bdaa06c3a` advanced `origin/main` from `5e6186d` and passed exact [run 29386046847](https://github.com/yanfengliu/python_mini_metro/actions/runs/29386046847): both `build` and `rl-smoke` succeeded in 35 seconds by API timestamps. Commit B changes only persistent/thread evidence.

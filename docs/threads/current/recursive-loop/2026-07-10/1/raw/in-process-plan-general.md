Not approved. Four substantive gaps:

- [P1] Finding verification is too weak. `DESIGN.md:31` compares only the re-derived `data.class` multiset, then copies original findings to `verified`. Equal classes do not prove the same claim, evidence step, severity, routing, or disposition was mechanically re-derived. Compare normalized semantic finding payloads one-to-one, omitting only documented run-scoped fields; reserve class-only comparison for cross-run prove-fixed.

- [P1] Failure-ledger wiring lacks a black-box crash test. `DESIGN.md:35` promises ledger rows for spawn/exit/artifact failures, but `PLAN.md:4` tests row construction and `PLAN.md:7` drills only an unparseable scenario. A rejected `spawn()` promise can bypass finalization entirely. Add an orchestration test with a nonexistent `PYTHON` executable and another with a nonzero runner; each must exit 1 and append exactly one strict-valid `run-failed` row.

- [P1] The seeded-bug promotion violates TDD. `DESIGN.md:51` and `PLAN.md:7` restore the fix before adding the promoted regression. While the defect is seeded, first add and run the regression red; then restore the implementation and run it green; finally re-seed only for revert-proof if desired.

- [P2] Checkpoint observability is promised but not tested. `PLAN.md:3` tests only “UUID-free JSON checkpoints,” while live latent state includes spawn counters (`src/mediator.py:105-106`), travel plans (`:111`), speed/progression state (`:113-116`), and metro dwell state (`src/entity/metro.py:42-43`). Two identical passes prove repeatability, not that divergence in omitted state is observable. Add schema/perturbation tests showing each determinism-critical latent-state family changes the canonical checkpoint/digest.

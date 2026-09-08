# GM-06c carriage composition diff ledger

Status: delivered as Commit A `80cc611`, exact [run 29853718512](https://github.com/yanfengliu/python_mini_metro/actions/runs/29853718512) green; evidence-only Commit B active

## Implemented production surface

- Add attached carriage entities, derived inventory and Metro capacity, deterministic attach/detach transactions, and whole-consist safe-return accounting.
- Make station dwell scheduling capacity-aware at both live stop-start seams.
- Add path-bound carriage controls, fourth-line HUD feedback, route-following consist rendering, passenger slicing, and fast/fidelity pixel evidence without changing the low-level action protocol.
- Add structured carriage observations, checkpoint v4, recursive-input v5, agent-play v5, index-only persisted carriage actions, frozen legacy fixtures, and Node v5 projection.

## Implemented evidence surface

- Reconcile GM-06b Commit B exact run `29809810291` and persist two live-code research reports.
- Require three independent plan reviews and clean re-reviews before tests, then record focused and combined red evidence before production edits.
- Add focused resource, capacity/timing, controls/actions, rendering/pixels, checkpoint/replay, compatibility, demonstrator, line-count, and failure/rollback tests.
- Update public/project docs, parent state/decision/evidence, this iteration's reviewed raw evidence, and exact local/remote A/B gates.

The reviewed carriage behavior and evidence above were delivered as Commit A `80cc611` (130 paths, +14890/-543), which excludes the pre-existing `.agents/` tree and three `.tmp-gm06c-*-precommit/` task-cache roots. Two full-`npm test`-only defects were fixed before staging: a `.gitattributes` `scripts/fixtures/*.json text eol=lf` hunk reverted to baseline because the recursive source-provenance guard rejects source-root attributes, and stale `playtest-recursive.test.mjs` default-pass assertions aligned to the v5/checkpoint-v4 advance. The exact pre-commit hook passed and the exact hosted [run 29853718512](https://github.com/yanfengliu/python_mini_metro/actions/runs/29853718512) passed `build` and `rl-smoke`. Evidence-only Commit B binds this result; GM-06d opens only after B's own exact workflow is green.

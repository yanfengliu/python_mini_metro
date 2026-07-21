# GM-06c carriage composition diff ledger

Status: reviewed implementation and local Python/Node/static gates complete; exact hook/staging and Commit A pending

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

The working candidate now contains the reviewed carriage behavior and evidence above. It remains uncommitted until the exact hook and staged-integrity gates pass; no Commit A or remote result is claimed yet.

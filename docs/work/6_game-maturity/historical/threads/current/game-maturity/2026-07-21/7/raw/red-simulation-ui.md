# GM-06c simulation/render/UI RED evidence

Status: `CLEAN` test contract; intentionally RED product state; production unchanged

The first independent RED audit returned `NOT CLEAN`. It identified conflicts with three superseded baseline assertions, missing live stop-start seams, weak turnaround/rebase proofs, incomplete dynamic control ownership, recording-double-only carriage rendering, post-warm purity snapshots, a UUID scan that discarded mapping keys, asymmetric pixel masking, missing HUD/layout failure boundaries, and a hard-coded locomotive-derived carriage spacing.

The revised suite migrated the GM-06a HUD blocker, GM-06b locomotive-only helper, and aggregate PassengerFlow dwell assertion; added real increment-time seams, route-search execution, deterministic half-circle turnaround, retained-edge and positive-length padding rebases, removal/rebinding and detach failures, real occupied Carriage rendering, pre-first-draw whole-state signatures, UUID-key scans, symmetric masks, carriage-minus states, and config-owned geometry.

Two further cross-reviews closed long-route terminal extrapolation, paused/moving composition timing, unplanned reconciliation purity, a noncanonical rider fixture, value-frozen layout rollback, exclusive per-body queued outlines in both profiles, full render-state purity, deterministic turnaround direction, zero HUD/glyph/cache evidence, slotted-ID overconstraints, both interpolation caches, preview/network cache bounds, and enum/string action-kind compatibility.

Final focused evidence:

- 99 tests across 14 simulation/render/UI and migrated-baseline modules.
- Expected pre-product RED with no collection/harness errors.
- Ruff check and Ruff format-check passed across all 17 touched simulation/UI files.
- Every touched test/support file is below 500 physical lines; maximum 499.
- Final fresh independent verdict: `CLEAN`.

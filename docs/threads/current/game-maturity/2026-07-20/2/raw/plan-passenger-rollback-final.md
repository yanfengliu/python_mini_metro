# Final corrected-plan passenger/RNG/rollback review

Result: CLEAN

Evidence:

- Full-station behavior now requires zero scoped-replanner calls and RNG parity with an equivalent legacy-side-effect control, correctly accounting for boarding-candidate RNG before and after the capacity guard.
- The private late-bound replanner boundary is exact through both `PathLifecycle` and `PassengerFlow`.
- Stable waiting batches, fresh marker nodes, raw plan preflight, four-field exhaustion reset, and network-wide alias checks are explicit.
- Rollback covers every declared mutable surface and both RNG streams, while excluding arbitrary rebound-hook side effects.
- PLAN, REVIEW, STATE, and DECISIONS are mutually consistent.

Read-only review; no files edited or tests run.

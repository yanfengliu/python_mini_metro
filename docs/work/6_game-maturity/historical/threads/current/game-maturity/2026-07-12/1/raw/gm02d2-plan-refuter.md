One remaining medium issue:

- With medians set to `None` and measurement booleans set to `False`, the existing zipped reason generation (`src/rl/resource_profile.py:313-337`) would still label unevaluated gates as `relative-memory-failed`, `historical-memory-failed`, and `throughput-failed`. That would preserve misleading evidence semantics.

Short-circuit reasons by prerequisite:

- Ineligible target → `target-ineligible`
- Incomplete campaign → `campaign-incomplete`
- Invalid repeat → `repeat-invalid`
- Settings drift → `settings-mismatch`
- Only after all prerequisites pass should measurement gates be evaluated and reported as failed.

Keep the measurement booleans `False` for API compatibility and medians `None`; add exact-reason regressions for incomplete, invalid, and settings-mismatch cases.

With that addition, the corrected plan is approved. The recurrent/PPO split, preserved `DEFAULT_FRAME_STACK == 8`, exact ten-frame descriptor, persisted-resume behavior, and B-CI evidence are coherent with the live contracts.

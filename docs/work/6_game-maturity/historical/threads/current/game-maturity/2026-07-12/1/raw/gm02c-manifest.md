# GM-02c manifest and CLI finder/refuter

## Initial finding

MEDIUM — The required genuine pre-GM-02 model/manifest-byte compatibility smoke is not implemented in the automated test. The test creates a new model with current dependencies and serializes v1 through the current writer, so it validates the old VecFrameStack mechanism but not persisted historical ZIP/manifest bytes.

Everything else inspected was clean: train resolver/defaults/exact descriptor inheritance; equal-count semantic mismatch rejection before artifact open; evaluation reconstruction/reporting; source fingerprints; no stale temporary guard; files below 500 lines; focused exact-RL 59/59.

## Final refutation

CLEAN; the prior finding is retracted. The plan requires exercising genuine historical bytes, not committing them as an automated fixture. The ignored persisted parent was authenticated directly: schema v1, recurrent PPO, frame stack eight, 21,784,628-byte model, manifest SHA `fb9b08c44f4bd6930e6f04bd41790bb64e4be7f1610480e4d0c86b82f5bf3f8a`, and model SHA `a940a4e049b67c439d241e6cb02262e3adffb6ab2fc69e4d3e667a782198fd9f`. Current evaluate/resume/re-evaluate evidence into v2 with inherited contiguous history satisfies the persisted-byte contract; the repeatable generated test separately covers old-wrapper semantics. No large fixture should be committed.

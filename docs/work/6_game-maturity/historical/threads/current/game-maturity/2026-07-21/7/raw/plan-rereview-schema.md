NOT CLEAN.

1. P1 — Fresh-process v5 replay could pass without exercising carriage serialization. Require the default or a dedicated Node-redriven v5 scenario to attach a carriage and compare a checkpoint with nonempty structured, top-level, and motion carriage references.

2. P1 — V4 needs an explicit exhaustive bijection: every top-level carriage index appears exactly once in its declared owner’s ordered `carriage_indices`, each owner list exactly matches its contiguous attachment slice, and the structured prefix satisfies the same relation. Current wording does not reject orphan suffix records or owner/reference disagreement.

3. P2 — Freeze agent-v4 observations through the existing UUID-free canonical-checkpoint projection, not raw `MiniMetroEnv.observe()` bytes, which contain process-local IDs.

All other prior schema/replay findings are resolved.

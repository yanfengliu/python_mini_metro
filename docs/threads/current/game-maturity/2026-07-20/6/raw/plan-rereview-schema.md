# GM-06b schema and replay plan re-review

Status: `NOT CLEAN`

1. `P1` - The complete v3 fleet object duplicates total inventory, but the validator did not explicitly require `structured.fleet.locomotives_total == progression.limits.num_metros`. Require that equality, exact integer-not-boolean typing of the persisted limit, and disagreement rejection.

2. `P2` - Make prefix correspondence executable in normalized JSON. Structured `path_index` represents the Metro's declared path and must match motion `declared_path_index`, not actual-owner `path_index`; position, current-station index, ordered passenger indices, and queue boolean must also agree. Canonical generation must reject a stale caller observation by verifying its ordered Metro IDs against the exact live global sequence before building the motion union.

All earlier schema/replay findings were otherwise closed: the shared pre-tick adapter, old byte fixtures/oracles, recursive/agent v4 fields, Node projection, index-only UUID-free persistence, preflight rejection, named historical fixtures, and file-size extraction/gates are testable.

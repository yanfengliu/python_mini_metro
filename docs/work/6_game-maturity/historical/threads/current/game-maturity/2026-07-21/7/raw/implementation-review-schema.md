# GM-06c implementation review - schema and replay

Status: `CLEAN` after live-code adversarial probes.

The implementation rejects duplicate live owners, duck-typed Carriages, duplicate or missing serialized references, invalid capacities and identities, and mismatched path/global topology. Per-path order is independent from global Metro order, including queued path-only-before-global round trips. Frozen v1/v2/v3 checkpoints normalize without carriage leakage, direct legacy generation rejects every forward carriage field, and nonempty v5 recursive/agent evidence replays in a fresh process.

The checkpoint-focused surface passed 25 tests; the adjacent schema/replay surface passed 78 tests. No actionable finding remained.

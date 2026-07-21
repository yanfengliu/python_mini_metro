# GM-06b roadmap, scope, and evidence research

Result: accepted scope is exactly explicit assign, queued-unassign, and redistribution controls/actions, with public/manual parity and the GM-06a ownership formula retained.

- Remove automatic allocation only in the same green unit that supplies usable replacement controls/actions. Multiple locomotives per line are already supported by path/global collections, simulation, replacement, rendering, and observations.
- Implement redistribution as queue-return-then-assign rather than a destination reservation. A reservation introduces a third state that D-021 does not represent.
- Use separate plus/minus controls because the path button already owns creation redraw, handle selection, click deletion, and purchase. Controls must be handle obstacles and reachable under both registered pixel profiles.
- GM-06c owns carriages/capacity/attachment/rendering. GM-06d owns occupied request semantics, detachment recovery, and existing destructive line-removal behavior. GM-06b must not conceal those boundaries.
- Adding queue intent silently to checkpoint v2 violates the global version invariant. Recommend checkpoint v3 and likely recursive schema v4, with genuine v1/v2 normalization and an explicit fail-closed boundary for old schemas that cannot encode a pending request.
- The frozen GM-03d lifecycle differential embeds automatic allocation. Preserve it as historical evidence and add a bounded reviewed transition proof; do not rewrite history or claim unchanged current behavior.
- Plan review and implementation review each need conservation/failure, schema/replay, and controls/Pixel lanes. Required delivery remains Commit A plus evidence-only Commit B, each with exact build and RL-smoke verification.

No files were edited by this research lane.

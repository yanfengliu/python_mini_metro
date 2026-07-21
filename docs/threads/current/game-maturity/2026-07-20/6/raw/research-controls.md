# GM-06b controls and ownership research

Result: recommend one explicit fleet transaction in which new lines start unserved, plus/minus controls and matching structured actions manage locomotives, and unassignment remains pending until an empty train reaches a station.

- Remove automatic construction from `PathLifecycle.finish_path_creation` and add real public `assign_locomotive(path) -> bool` plus `queue_locomotive_unassignment(path) -> bool` methods.
- Add strict `assign_locomotive` and `unassign_locomotive` actions with exactly one ID or index selector. Resolve the Metro factory only after validation, use existing `Path.add_metro`, and append the same identity globally.
- Select the last nonpending candidate deterministically. Keep a queued Metro assigned and unavailable; force its next stop, prevent boarding, preserve ordinary unloading, and detach only when empty at a station.
- Define redistribution as source queued return followed by destination assignment. Do not add a compound destination reservation because it creates target deletion/cancellation/persistence semantics and another ownership category.
- Use a focused stateless fleet component and compact plus/minus controls dynamically associated with path buttons. Put controls into the existing button list so route-handle obstacle logic sees them automatically. Keep PlayerPixel on existing pointer actions and render a visible queued marker.
- Cover creation without service, exhaustion, multiple locomotives, reverse-order requests, malformed ownership, failure rollback, queue timing, pause/game-over, structured state, mouse/action parity, hit geometry, fast/fidelity pixels, and unchanged protocol/task identities.

Important warning: removing automatic assignment intentionally changes historical `create_path` outcomes. The plan must choose an explicit legacy replay/migration boundary rather than claiming the frozen lifecycle differential remains current-game equivalent.

No files were edited by this research lane.

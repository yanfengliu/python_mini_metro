# GM-05c live scope audit

Read-only audit complete. GM-05c is a small product slice, but its interaction contract is not yet fully specified.

## Hard roadmap contract

- Add ergonomic endpoint extension/shortening and interior insertion handles after GM-05a's atomic replacement and GM-05b's full redraw.
- Preserve manual/structured equivalence.
- Preserve metro/passenger continuity and fail closed on unsafe edits.
- Cover linear and loop routes with replay/checkpoint regressions.

Sources: `docs/threads/current/game-maturity/2026-07-11/1/PLAN.md:138-154`, `DECISIONS.md:111-121`.

At audit time, `main == origin/main == 0d6f5b9` (`[GM-05b:B]`), with only `.agents/` untracked. GM-05c remained closed until that commit's exact workflow was green and reconciled by GM-05c's opening Commit A.

## Recommended smallest coherent GM-05c contract

Keep selection transient and reuse the existing assigned-button hold gesture:

1. Holding an assigned line button displays handles for that line.
2. Linear lines expose two endpoint handles.
3. Every logical station-to-station edge exposes an insertion handle; loops include the closing edge.
4. Before ordinary station capture begins, moving into a handle selects that operation: endpoint to new station extends; endpoint to the adjacent interior station removes exactly one endpoint; interior handle to a station not already on the route inserts it between that edge's stations.
5. Release dispatches the existing `replace_path(...)` hook exactly once, after clearing transient state.
6. Original endpoint, invalid duplicate, off-station, malformed, too-short, or unsafe releases cancel/reject without effects.
7. Existing full redraw and click deletion remain unchanged.

This avoids a persistent click-to-select mode, deletion-gesture migration, new structured action, checkpoint migration, or low-level RL action change. Completed handle edits remain equivalent to existing structured `replace_path`.

## Production and evidence targets

- Extend the immutable redraw value or add a companion handle-edit value; use a new pure shared geometry/derivation module; add thin input/facade wiring; extend preview layout for arbitrary insertion; add deterministic handle rendering; reuse the bounded preview and atomic replacement transactions.
- Do not extend the 495-line `path_replacement.py` or 498-line `recursive_checkpoint.py`.
- Add focused pure, converted-input, rendering, PlayerPixel, and state-equivalence modules; rerun the GM-03f differential, historical checkpoint/replay regressions, full suite, changed-file Ruff/hooks, and content fingerprint.

## Important risks

- The roadmap has no accepted activation, persistence, loop-endpoint, shortening-range, or precedence contract yet.
- Render and hit geometry must share one pure source, especially for centered parallel lanes.
- Loop lines have no endpoints; the minimal rule is insertion handles only, including the closing edge. Full redraw remains the way to open or shorten a loop.
- Existing redraw duplicate/loop semantics cannot simply seed handle candidates.
- The converter still discards button identity; strict left-button modeling remains outside scope.
- Source changes advance the environment-content fingerprint while protocol/task fingerprints should remain exact.

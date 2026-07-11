# Correctness review

- **High — `rebuild_geometry()` leaves existing metros attached to stale segments.** `src/entity/path.py` replaces every segment object but did not remap `metro.current_segment`. A live reproduction after moving a station showed the rebuilt segment ended at `(200, 0)`, while the metro still referenced the old segment ending at `(100, 0)` and was no longer present at `path.segments[metro.current_segment_idx]`.
- **Medium — paused wall time can leak into the first resumed update.** `GameSession.advance()` advanced the accumulator before checking pause, while `FixedStepClock` retained a sub-step remainder. A verified `advance(16)` while paused followed by `advance(1)` after resuming produced a 17 ms simulation update.
- **Medium — `Mediator.render()` no longer preserved arbitrary-surface behavior.** Rendering to 800x600 retained default 1920x1080 path-button and game-over hitboxes off-surface.
- **Medium — legacy `Path.draw(surface, path_order)` silently ignored its ordering contract.** Direct callers received overlapping centerlines.

## Re-review

No important findings remain. All four fixes are present and the prior reproductions now pass. Verification: 94 related tests passed across `test_game_clock`, `test_path`, `test_mediator`, and `test_render_layout`, including dedicated regressions for each finding.

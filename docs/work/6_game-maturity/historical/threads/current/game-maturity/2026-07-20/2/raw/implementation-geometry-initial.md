# Geometry, topology, and atomicity implementation review - initial and corrective outputs

## Output 1

Preliminary current-live repros (before your latest geometry split/build-candidate move, and still structurally applicable): patched fresh candidate with fresh list storage but `segments/path_segments/padding_segments[:]` copied from another live path is accepted; target then shares every mutable segment object and mutations propagate. A patched candidate that changes every `segment.line.width` to 1 is also accepted. I’m re-reading the now-changing live files and will rerun after they stabilize.

## Output 2

Also note current `test/test_gm05a_passenger_transitions.py` is exactly 500 lines; the replaced AGENTS rule says files stay under 500 (hard ceiling 1000), and the approved PLAN explicitly required splitting that suite before adding coverage. This is independently actionable even though outside my geometry focus.

## Output 3

Your geometry fix is only half-wired in the current live tree: `validate_path_geometry` now returns one bool and requires `lane_spacing`/`stroke_width`, while `path_replacement.py:267-275` still destructures `(valid_geometry, lane_shift)` and calls without keywords; `build_candidate` now requires lane/stroke/live_geometry params while `path_replacement.py:417-425` still passes the old args. Focused calls currently raise TypeError until the caller is updated.

## Output 4

New concrete hole in revised exact validator: `path_replacement_geometry._point()` coerces values with `float(...)`, while `_line_is_consistent` and segment order use equality only. A malformed live/candidate path with `segment_start.left='0'`, `line.width=10.0`, and `segment.path_order=0.0` still validates `True`; then `Path.move_metro` raises TypeError on string arithmetic. Direct repro confirmed. Require canonical numeric coordinate types (non-bool int/float, finite) before conversion, exact-int line width, and exact-int segment path_order (or equivalent canonical checks).

## Output 5

Final-current remaining concrete finding: MEDIUM fail-closed hole in `src/path_replacement.py:112-125`. `_is_on_segment` performs unchecked arithmetic on `metro.position`; unlike segment geometry, metro coordinates are not canonical-type validated/caught. Repro: `_build_network(); metro.position = Point('100', 100); mediator.replace_path(path,[0,1,3,2])` raises `TypeError` instead of returning `False` with zero effects. Given the plan’s unsafe/inconsistent-edit rejection contract and explicit type checks for metro index/direction, validate finite non-bool int/float metro coordinates or catch arithmetic errors.

## Output 6

BLOCKING regression from that fix: normal `Path.move_metro()` produces `numpy.float64` Point coordinates (via NumPy-based `direction()`), so exact `type in (int,float)` rejects legitimate moving trains. Fresh 40-test GM05a run now has 7 failures: linear/loop/reversed/padding/two-station/backward/replay successes all return False. Direct: after `_move_partway`, metro.position is `(np.float64(160.0), np.float64(100.0))` and `_target_motion` returns None. Use `numbers.Real` excluding bool (plus finite), or explicitly support production NumPy reals while rejecting strings/bools.

## Output 7

One remaining malformed-candidate alias hole after the current 40/40 pass: `validate_path_geometry` checks padding junctions by coordinate equality only and does not enforce canonical internal Point identity. Repro patched `Path.rebuild_geometry`: set second path segment’s `segment_start`/`line.start` and padding `segment_end`/`line.end` to the first path segment’s `segment_end`; `replace_path(target,[3,0,1])` returns True and the live path has `path_segments[0].segment_end is path_segments[1].segment_start` (production `Path` creates distinct path-endpoint Points joined through padding). This introduces extra mutable aliasing entirely within the candidate, evading candidate-vs-live IDs. Enforce all path-segment endpoint Points are identity-unique and padding endpoints are the exact adjacent endpoint objects; line identity uniqueness is also canonical.

## Output 8

Latest functional pass is green (22/22 metro/transaction/rollback; earlier current 40/40), but the newest guards pushed `src/path_replacement.py` to 505 physical lines. That now violates AGENTS/PLAN’s under-500 target (hard ceiling remains 1000). Please shave/split at least 6 lines, then I can give final CLEAN.

## Output 9

One last tiny but concrete fail-closed edge introduced by shared validation: `is_canonical_point()` catches AttributeError/TypeError/ValueError but not `OverflowError`, while `_point()` converts any `Real` to float. Repro `metro.position = Point(10**10000, 100)` then replace raises `OverflowError: int too large to convert to float` instead of False. Geometry validator already catches OverflowError; add it to `is_canonical_point` and a bounded regression, then CLEAN.

# API, action, replay, and architecture implementation review - initial and corrective outputs

## Output 1

API/replay/architecture review is NOT CLEAN: HIGH at src/path_replacement.py:332-365 (commit at 412-418). `_build_candidate` validates only `candidate.metros` and exact station sequence after `rebuild_geometry`; it never validates that logical geometry was actually rebuilt (and the `live_lists` alias set is checked only against `candidate.stations`). Reproducer: build a no-metro target path [0,1], create `candidate = Path(target.color)`, set `candidate.rebuild_geometry = MagicMock()` (effect-free no-op), patch `mediator_module.Path` to return it, then `mediator.replace_path(target,[3,0,1],False)` returns True and commits 3 stations with `segments == path_segments == padding_segments == []`. `canonical_checkpoint` remains schema-v2 and `reference_errors(checkpoint) == []`, so current replay/oracle tests falsely report clean state. This violates PLAN.md:23 (candidate geometry built off-live) and :67 (success geometry equals topology). Add fail-closed post-build structural/alias validation and a regression proving malformed/no-op geometry cannot commit. Current validation otherwise: 38 GM tests PASS, 89 adjacent contracts PASS, full 620 PASS (12 skipped), Ruff check + format check of 11 changed Python files PASS; exact signatures/selectors/no-time/fresh-process replay/no schema change/dependency-light imports/method counts/line caps all checked clean.

## Output 2

NOT CLEAN.

- HIGH — [src/path_replacement.py](C:\Users\38909\Documents\github\python_mini_metro\src\path_replacement.py:332): candidate validation checks only metros and station order, allowing an effect-free no-op `rebuild_geometry()` to commit three stations with all geometry lists empty. `canonical_checkpoint` and `reference_errors()` still report clean. Validate candidate geometry and all topology-list aliases before commit, with a regression.

Otherwise clean: 620 tests passed (12 skipped); focused GM-05a and adjacent contracts passed; Ruff check/format passed; API, replay, schema, imports, counts, and line caps matched the plan.

## Output 3

Fresh re-review NOT CLEAN.

1) MEDIUM functional — src/path_replacement_geometry.py:145-153 (called for every live path at src/path_replacement.py:267-275). The validator requires every edge's projected lane shift to stay within `0.75 * abs(path_order)` of the first edge. Real `PathSegment` geometry rounds the x/y offset per edge, so genuine shifts can differ by >0.75 by orientation. Reproducer: `_build_network(route=(0,1,2), path_order=1, metro_count=0)`; set station positions to `(0,0),(27,-41),(123,43),(180,70)`, call `path.rebuild_geometry()`. The genuine offsets are `(8,5)` and `(-7,8)`; `validate_path_geometry(path,path.stations,False)` returns `(False,0.0)`, and `mediator.replace_path(path,[0,1,2,3],False)` returns False. This rejects a valid real-Path edit. The same block also rejects a genuine all-zero-length path when path_order != 0 (`not observed_shifts`). Validate against the actual rounded per-edge construction envelope rather than a first-edge scalar.

2) LOW gate — exact Ruff format check currently fails: `src/path_replacement_geometry.py` and `test/test_gm05a_passenger_transitions.py` would be reformatted. Ruff check passes.

3) LOW architecture/size — current physical lines: `src/path_replacement.py` 524 (over under-500 target), `test/test_gm05a_passenger_transitions.py` 500 (not under 500). New `src/path_replacement_geometry.py` is absent from ARCHITECTURE.md source tree (around lines 76-77) and helper ownership prose (line 279), which currently names only transaction and snapshot helpers.

Confirmed fixed: prior no-op `rebuild_geometry` candidate now raises ValueError with live topology unchanged; broad relevant list-storage aliases (host topology, all live path lists, holder lists, plan node lists, and all candidate lists pre/post rebuild) are guarded. Exact action semantics/signatures, no-time rejection, replay/checkpoint schema, import isolation, and method counts remain clean. Current focused GM tests: 39/39 pass; adjacent API/checkpoint/import slice: 56/56 pass.

## Output 4

Live refresh after concurrent edits: zero-length nonzero-order case is now covered/fixed, and path_replacement.py is down to 464. The angled-edge false rejection still reproduces unchanged on current geometry helper lines 141-149: genuine real-Path validation returns `(False, 0.0)` and replace returns False for positions `(0,0),(27,-41),(123,43),(180,70)` at path_order=1. Current passenger transition test is 501 lines, and ARCHITECTURE still omits path_replacement_geometry.py.

## Output 5

Geometry math detail for the fix: each endpoint offset is the real PathSegment's independently rounded 10px normal, so one edge's projected-shift rounding error can be ~0.707px/order; two valid orientations can therefore differ by ~1.414px/order. Keeping ~0.75/order for within-edge perpendicular consistency is reasonable, but cross-edge and old-vs-candidate scalar comparisons need a separate >=sqrt(2)*abs(path_order) envelope (plus epsilon), or should validate each edge directly against the rounded construction rule.

## Output 6

NOT CLEAN.

- MEDIUM — [path_replacement_geometry.py](C:\Users\38909\Documents\github\python_mini_metro\src\path_replacement_geometry.py:141): genuine nonzero-order `PathSegment` offsets vary by edge because production rounds each normal component. Comparing all projected shifts with only `0.75 * abs(path_order)` rejects valid geometry. Reproducer positions `(0,0) → (27,-41) → (123,43)` at `path_order=1`; validation returns false and replacement is rejected.
- LOW — [test_gm05a_passenger_transitions.py](C:\Users\38909\Documents\github\python_mini_metro\test\test_gm05a_passenger_transitions.py:1) is 501 physical lines, above the under-500 target.
- LOW — [ARCHITECTURE.md](C:\Users\38909\Documents\github\python_mini_metro\ARCHITECTURE.md:76) omits the new `path_replacement_geometry.py` helper from both the tree and ownership description.

The original malformed-candidate finding is fixed, relevant collection-alias guards are comprehensive, and current focused tests and formatting pass.

## Output 7

CLEAN on the now-stable GM-05a API/action/replay/architecture tree. Fresh evidence: 40/40 focused GM-05a tests pass (including angled production-rounded path_order=1, zero-length path, malformed geometry, live geometry/object/list aliases, fresh-process replay); 89/89 adjacent input/lifecycle/passenger/checkpoint/oracle/replay contracts pass; Ruff check and format-check pass all 12 changed/new Python files. Exact Mediator signatures match; method counts are PathLifecycle 15, PassengerFlow 17, InputCoordinator 19. Sizes are all under 500 except explicitly justified Mediator 652 (<1000): path replacement 483, geometry helper 234, passenger test 499. ARCHITECTURE now lists/owns the geometry and snapshot helpers and records 40 methods/652 lines; README/GAME_RULES match exact selector, unique-station/trailing-loop, atomic failure, extras, and no-time semantics. No checkpoint/schema or hidden persistent state change; helper imports remain dependency-light/stateless. Prior candidate corruption and orientation findings are refuted by current code/tests.

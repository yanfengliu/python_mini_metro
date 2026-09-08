# GM-09b implementation review — harness lane (verbatim), verdict CLEAN

Method: read every changed file HEAD-vs-working-tree, then ran py313 Python to PROVE behavior — including an independent OLD-code mirror built from `git show HEAD:`, not just trusting the committed tests.

## 1. CLASSIC determinism (highest lock) — SOLID
- Independent OLD mirror (HEAD get_entity.py+mediator.py, pre-spawn_regions): diffed a full fingerprint (every station repr() float position + shape, complete post-construction python_random.getstate() AND numpy bit_generator.state, plus path colors) across seeds 0,1,2,7,42 → BYTE-IDENTICAL, zero diff.
- Full-frame render hash (GameRenderer.draw on a CLASSIC Mediator) IDENTICAL old-vs-new (f48cf51c…).
- test_gm09a_maps (_CONSTRUCT_FP/_TRAJ_FP seeds 0/1) + test_gm07b_save_determinism (frozen save-v1.json) both PASS.
- Falsy fast path correct (get_entity.py:45 `if not spawn_regions or …` returns the first draw for CLASSIC's empty tuple, one get_random_position call, no extra RNG). get_random_position untouched.
- Independent old run: seed-0 Triangle(1232,318),Rect(1132,474),Rect(1213,375) == the test's hardcoded pre-change fingerprint.

## 2. RIVER spawn — SOLID
40 seeds × 20 stations: zero off-bank, zero glyph-overlaps-water. Deterministic. Termination: 13.8% single-draw rejection, max 6 consecutive in 200k draws vs the 64 bound; P(all 64 fail)≈1e-55. Geometry exact: all 7 shape half-extents ≤ station_size; banks eroded by station_size, glyph touches the waterline at most, never the true water region [883.2,1036.8].

## 3. Save guard structural — SOLID
serialize_game: default-CLASSIC serializes; forged MapDefinition("classic",1,rivers=…) RAISES; RIVER RAISES; divergent-palette classic@1 RAISES. Does NOT over-reject: a reconstructed classic-identical map (== CLASSIC) and map_definition=None both serialize. The frozen-dataclass __eq__ (save_game.py:42 `map_def == CLASSIC`) does real work.

## 4. Render hook — SOLID
draw_terrain first at game_renderer.py:101, before network (:103) and stations (:115+) — terrain under the network. RL path (player_env.py:280) passes the Mediator as state and fills before draw → PlayerPixelEnv observation DIFFERS classic-vs-river and is reproducible; CLASSIC RL frame byte-identical. getattr guards safe for attr-less/None states; test_headless_render + test_game_renderer pass.

## 5. Import safety — SOLID
Fresh-process `import maps` pulls only config + geometry/geometry.type; no pygame/shapely/geometry.polygon/mediator/entity/numpy.

## 6. Validation — SOLID
_coerce_rects rejects right≤left, bottom≤top, zero-area, wrong-length, NaN, ±inf, each with a named ValueError quoting the rect; nested lists coerced to tuples. Rejection-loop error named + includes regions=….

## 7. Regressions — NONE
Full suite 1372 OK (12 skipped). ruff + format clean; pre-commit all-pass, modified nothing. No CLASSIC RNG-order/draw-count change.

## 8. Scope (defer save-v2 to GM-09f) — SOUND
No code path serializes a river Mediator (human loop builds default CLASSIC; player_env/training make no save_game call; guard rejects a river Mediator anyway).

## NITs (non-actionable): benign 1-pixel waterline share; mediator.py 844 LOC pre-existing.

## Verdict: CLEAN

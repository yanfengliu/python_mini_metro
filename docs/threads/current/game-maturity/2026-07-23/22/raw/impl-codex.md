CRITICAL — no findings.
MAJOR — no findings.

### Findings

- MINOR — [src/maps.py:166](C:/Users/38909/Documents/github/python_mini_metro/src/maps.py:166), [get_entity.py:24](C:/Users/38909/Documents/github/python_mini_metro/src/entity/get_entity.py:24) — `Mediator(seed=1295, map_definition=DELTA)` places a Triangle at `(1218,147)`; its vertex `(1248,121)` overwrites river-2 water from `(176,196,222)` to black → the promised whole-glyph separation is false at an inclusive raster boundary → add a DELTA-local one-pixel/render-aware gutter and a pixel regression. The same seam pre-exists on RIVER seed 1379, so changing shared sampling here would violate the required RIVER byte identity.

- MINOR — [src/maps.py:145](C:/Users/38909/Documents/github/python_mini_metro/src/maps.py:145) — `screen_width=200, station_size=30` produces a zero-width middle bank and raises during `maps` import, preventing even CLASSIC from loading; width 201 creates a positive 0.3-px bank with no integer spawn coordinate and seed 0 exhausts 64 attempts → lazily construct alternate maps or explicitly validate/document the supported config lattice. Current 1920×1080 geometry is healthy; this is a future-config/global-blast-radius hazard.

- MINOR — [test_gm09d_delta.py:45](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09d_delta.py:45) — registering the planned next map makes this DELTA test fail despite DELTA remaining correct → use membership assertions, matching the GM-09b test that was loosened for exactly this reason.

- MINOR — [test_gm09d_delta.py:85](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09d_delta.py:85) — burning one extra Python RNG draw after DELTA construction still passes the determinism test while changing the next draw and subsequent trajectory → fingerprint all stations, colors, Python/NumPy RNG states, and a stepped trajectory.

- MINOR — [test_gm09d_delta.py:197](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09d_delta.py:197) — `RuntimeError("delta failure")` satisfies `assertRaisesRegex(Exception, "delta")` even though the required fail-closed save diagnostic is gone → require `ValueError` and match `delta@1` plus the v1 map-identity limitation.

- MINOR — [terrain_renderer.py:37](C:/Users/38909/Documents/github/python_mini_metro/src/rendering/terrain_renderer.py:37) — a `draw_crossings` regression using only `rivers[:1]` passes the current DELTA suite while omitting the second portal → add a full-span DELTA render test asserting two distinct portal pixels.

### Verified clean

- Actual rivers: `556.8–672.0` and `1248.0–1363.2`; bank widths: `526.8 / 516 / 526.8`. Mid width is `0.30W - 2S = 516`.
- Across 10,000 seeds all 27 initial bank sequences occurred. Every three-station open/loop permutation needs at most four crossings. Four is meaningful: seed 2 accepts a four-crossing route, permits same-bank construction at zero remaining, and rejects the next crossing inertly.
- Three-region sampling and two-river crossing/gating/rendering are genuinely N-ary; no single-river indexing assumption was found. Both portal pixels render.
- CLASSIC and RIVER MapDefinitions, complete construction/RNG projections, and initial frame hashes matched HEAD for seeds 0, 1, and 4207. Frozen `save-v1` pins pass.
- DELTA at saturation observes `{"total":4,"consumed":4,"available":0}`, produces a valid canonical checkpoint, and save attempts raise the correct named `ValueError`.
- The live test file changed from 12 to 13 tests during review; the newly added budget-ceiling test is sound. Current validation: 13/13 focused, full suite 1415 passed with 12 skips, and Ruff check/format passed.

The external CLI lanes were blocked by data-egress policy; three independent in-environment review lanes were used instead. The CLI refresh left only two Windows-locked executables in npm’s `.codex-fZlJfXfn` temporary directory; they can be removed after this Codex host exits.

FIX-FIRST

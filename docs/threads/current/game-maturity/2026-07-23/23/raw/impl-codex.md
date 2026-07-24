FIX-FIRST — one MAJOR and two MINOR product defects.

### Findings

1. MAJOR — [src/maps.py:203](</C:/Users/38909/Documents/github/python_mini_metro/src/maps.py:203>) / [src/entity/get_entity.py:31](</C:/Users/38909/Documents/github/python_mini_metro/src/entity/get_entity.py:31>) — `Mediator(seed=74, map_definition=LAKE)`; build `[0,1]` three times, consuming all tunnels, then set `deliveries=10` and unlock station 3 at `(1261,687)` → every edge from station 3 to stations 0–2 crosses the lake and every creation is rejected. Lines can bend only at stations, so bounded water does not guarantee a zero-tunnel detour; the budget gates this station’s connectivity until a tunnel is reclaimed → ensure the generated station visibility graph remains connected using crossing-free edges, or add automatic dry-land waypoints/shoreline routing. Add this exhausted-budget unlock regression.

2. MINOR — [src/crossings.py:31](</C:/Users/38909/Documents/github/python_mini_metro/src/crossings.py:31>) — seed `17184`, stations 13 `(1152,259)` and 14 `(1152,909)` form a vertical line exactly along the lake’s right edge. After three other crossings exhaust the budget, `path_crossings` returns portal `(1152,367)` and rejects `[13,14]` → rendered water occupies only `x=768..1151`, so this centerline is entirely on dry land but is charged as a tunnel → intersect against the rectangle’s strict interior; positive-length edge-collinear tangency must be zero.

3. MINOR — [src/maps.py:212](</C:/Users/38909/Documents/github/python_mini_metro/src/maps.py:212>) / [src/entity/get_entity.py:24](</C:/Users/38909/Documents/github/python_mini_metro/src/entity/get_entity.py:24>) / [terrain_renderer.py:31](</C:/Users/38909/Documents/github/python_mini_metro/src/rendering/terrain_renderer.py:31>) — seed `5680` starts with a Rect station at `(777,337)`. The inclusive top strip accepts it because its limit is `337.2`; rasterized water begins at `y=367`, and the 60-pixel Rect overwrites 40 water pixels on that row → violates “never in or touching the water” → use a strict, raster-aligned margin—practically `station_size + 1` on every shore—and test glyph pixels against the rendered water mask.

### Test-quality findings

- MINOR — [test_gm09e_lake.py:134](</C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09e_lake.py:134>) — the test named “budget limits shortcuts but never connectivity” creates only one crossing and immediately returns → it never exhausts the budget, rejects a fourth crossing, or constructs a zero-budget detour, so the MAJOR defect remains green → replace it with the seed-74 state above.

- MINOR — [test_gm09e_lake.py:65](</C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09e_lake.py:65>) — the sweep combines both side strips as `"S"` and requires only top/bottom coverage. Replacing the right strip with a duplicate left strip would leave the central-height right flank unreachable while this test still passes → assert top, bottom, left, and right independently and add raster-level glyph clearance.

The test correctly avoids both prior mistakes: registry checks use membership rather than an exact forward-hostile `KNOWN_MAP_IDS` tuple, and the save test uses `assertRaisesRegex(ValueError, r"lake'@1")`.

### No additional findings

- BLOCKER/CRITICAL: none.
- Ordinary enter-and-exit counts exactly one; corner-only contact and outside-to-boundary contact count zero. Both-inside geometry counts one but is unreachable for valid LAKE stations.
- Budget arithmetic is meaningful: three shortcuts consume three tunnels, a fourth is rejected, and a genuine dry route remains allowed at zero. Only the universal detour/connectivity claim is false.
- LAKE observation, canonical checkpoint, save rejection, filled terrain, and entry portal all worked.
- CLASSIC’s seed-0 fingerprint passed. Live-versus-HEAD CLASSIC/RIVER/DELTA definitions, RNG projections, and full-frame hashes matched.
- Remaining coverage gaps: no LAKE-specific observation/checkpoint/portal test; LAKE determinism is repeatability-only rather than a frozen fingerprint.

Validation: GM-09e `11/11`, combined GM-09 suites `102/102`, and save determinism `6/6` passed. Review was read-only.

FIX-FIRST

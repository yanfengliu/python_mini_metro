# Independent GM-06a HUD and PlayerPixel plan review

Result: not clean on first pass.

1. P1 - legacy renderer-state compatibility was unspecified. `_draw_hud` must not assume every facade has `available_locomotives`; define and test fallback derivation from complete `num_metros` and `metros` surfaces, safely defaulting to zero when unavailable.

2. P1 - whole-frame fresh/create/remove comparisons can false-pass because routes, trains, handles, and cursor pixels also change. Both registered profiles must use genuine low-level PlayerPixel station-drag creation and path-button removal actions, mask both cursor regions, isolate the projected third-line count-glyph crop, and prove exact `4 -> 3 -> 4` glyph changes in actual `step_result[0]`.

3. P2 - the HUD exclusion needed an exact tuple and supported count envelope. Tests must use the configured rectangle and prove all feasible route draft kinds remain present, canonically clear, quantized clear in both profiles, and hit-test reachable because the builder can silently omit a draft when no candidate fits.

4. P2 - `src/rendering/game_renderer.py` was already 477 physical lines against the repository's 500-line target. Add a post-change line-count gate and extract a helper if implementation crosses 500.

The planned cache/purity coverage and GM-06b/GM-06c scope boundary otherwise looked sound. No files were edited by the reviewer.

# GM-09d implementation — dual adversarial review synthesis

GM-09d is a PURE additive `MapDefinition` (DELTA) with no new machinery, so the review surface is: geometry/solvability/determinism/byte-identity + whether the reused GM-09b/GM-09c spawn/render/crossing/gate/save code actually generalizes to 3 regions / 2 rivers.

- Harness (`raw/impl-harness.md`, **SHIP**): verified all 7 checklist items end-to-end (byte-additivity via unchanged CLASSIC/RIVER fingerprints, generality of every reused loop, save-guard-by-name, `canonical_checkpoint` across schema v1-v4 on a DELTA env, `PlayerPixelEnv` threading so `--map delta` trains on DELTA, and the real RL frame showing exactly 2 water bands). No BLOCKER/MAJOR; 3 MINOR test-hardening + NITs.
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST**, MINOR-only): no CRITICAL/MAJOR. Verified across 10,000 seeds (all 27 initial bank sequences; every 3-station permutation needs <=4 crossings; budget 4 meaningful), CLASSIC/RIVER byte-identity at seeds 0/1/4207 + frozen `save-v1`, N-ary spawn/crossing/render, `tunnels`+checkpoint on a saturated DELTA env, save guard raises the named `ValueError`, and both portals render. 6 MINORs.

## Findings + dispositions (harness H, Codex C)
- MINOR (H) — `test_terrain_paints_two_channels` only asserted "something changed". **FOLDED**: `test_terrain_paints_both_channels_and_not_the_mid_bank` asserts RIVER_COLOR at both channel centers + background between.
- MINOR (H) — no DELTA over-budget REJECTION test. **FOLDED**: `test_budget_four_is_a_real_ceiling` (L-M + M-R + full-span L-R = 4 consumed; a 5th crossing rejected inertly).
- MINOR (C-3) — `test_delta_is_registered` used an EXACT `KNOWN_MAP_IDS` tuple (the same brittleness I'd just fixed in GM-09b — repeated here). **FOLDED**: membership assertion.
- MINOR (C-4) — determinism test only checked stations, so a spurious extra RNG draw would pass. **FOLDED**: `test_delta_construction_and_trajectory_are_deterministic` fingerprints construction + a 60-step RNG-driven passenger-destination trajectory.
- MINOR (C-5) / NIT (H) — save-guard `assertRaises(Exception)` too broad (a `RuntimeError` would pass). **FOLDED**: `assertRaisesRegex(ValueError, r"delta'@1")` pins the fail-closed diagnostic by type + exact identity.
- MINOR (C-6) — a `draw_crossings` regression marking only `rivers[:1]` would drop the second portal untested. **FOLDED**: `test_full_span_line_renders_a_portal_at_each_channel` (two distinct portal pixels).
- MINOR (C-1) — a Triangle glyph VERTEX can touch a channel edge by ~1px (`seed 1295`), so "whole glyph clears the water" is off at the inclusive raster boundary. This PRE-EXISTS on RIVER (same station_size erosion, `seed 1379`); a DELTA-local gutter would diverge from the delivered RIVER for a 1-pixel cosmetic seam. **RE-DISPOSITIONED**: accept as a shared pre-existing property; the maps.py comment corrected to say the station CENTER (not the whole glyph) clears by station_size.
- MINOR (C-2) / MINOR (H) — mid-bank degenerate at `screen_width <= ~201` → import-time `_coerce_rects` raise (blast radius: breaks CLASSIC too). Shared latent property (RIVER at ~65); current 1920×1080 far clear. **DOCUMENTED** in the maps.py comment (bands assume a screen wide enough); a lazy-map-construction refactor is out of GM-09d's additive scope.

## Result
Both lanes: no BLOCKER/MAJOR — DELTA is byte-additive and the GM-09b/GM-09c layer proven to generalize to 3 banks / 2 rivers (verified through the live budget gate, save guard, checkpoint across schema versions, and the real RL pixel frame). All six substantive test-hardening MINORs folded (14 tests, up from 12); the two latent/cosmetic geometry MINORs re-dispositioned as pre-existing/shared and documented. Full suite 1416 OK.

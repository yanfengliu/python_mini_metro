# Harness impl review (GM-09d DELTA) — SHIP

Verdict: **SHIP**. No BLOCKER, no MAJOR. Verified all 7 checklist items end-to-end; full 1414-test suite green; 12 GM-09d tests pass; ruff clean.

## MINOR (test-hardening, all folded)
1. `test_terrain_paints_two_channels` asserted only "something changed" — a regression dropping ONE band would still pass. Implementation verified correct (both centers paint RIVER_COLOR, mid stays background, RL frame shows exactly 2 bands). FOLD: assert water at both channel centers + background between.
2. No DELTA-specific over-budget REJECTION test — budget-4 test proves sufficiency, not that 4 is a ceiling; would pass with budget 100. Enforcement verified manually (L-M+M-R+L-R = 4 consumed, 5th rejected, removal refunds). FOLD: add a 5th-crossing-rejected test.
3. Mid-bank width = `0.30*screen_width - 60`, degenerate at `screen_width <= 200` → `_coerce_rects` would raise at import, breaking every map. Shared latent property (RIVER degenerates at ~65); current config (1920) far clear. Robustness note, no action.

## NIT (folded where cheap)
- `test_delta_map_is_not_serializable` used `assertRaises(Exception)` (broad) → tightened to `assertRaisesRegex(..., "delta")`.
- mid-bank overlap test asymmetry (left/right + channel-channel left to `_coerce_rects`/spawn) — fine.
- float residues (`1248.0000000000002`) harmless — erosion preserves the residue, gap is exactly `station_size`.

## Verified CORRECT (per checklist)
1. Geometry — 3 banks positive-area (L=526.8, M=516.0, R=526.8), no overlap; erosion exactly `station_size` on both mid-bank sides.
2. Solvability — 3 banks need >=2 crossings; budget 4 always suffices with 2 spare; enforcement real (5th rejected, refund works).
3. Determinism — DELTA fingerprints reproduce across processes (seeds 0/7); `KNOWN_MAP_IDS` sorted, NO `src` consumer depends on order/length (only tests).
4. Byte-identity — registry addition is additive (new key + new constants, no `_RIVER_*`/CLASSIC mutation); CLASSIC seed-0 fingerprint `(1232,318),(1132,474),(1213,375)` matches; RIVER stable; full suite green.
5. Generality — `_point_in_rects` (3 regions), `path_crossings`/`within_tunnel_budget` (2 rivers), `draw_terrain`/`draw_crossings` (2 bands) all iterate generically; both channels paint.
6. Save/obs/checkpoint — save guard rejects DELTA by name; `tunnels` observation valid (total=4); `canonical_checkpoint` succeeds for schema v1-v4 on a DELTA env with cross-river lines; `PlayerPixelEnv` threads the map so `--map delta` genuinely trains on DELTA.
7. Test quality — 12 pass, budget test non-vacuous (seed 4 has all 3 banks). Gaps noted above (folded).

**Single most important thing verified:** DELTA is byte-additive (CLASSIC/RIVER fingerprints unmoved, 1414-test suite green) AND the GM-09b/GM-09c layer genuinely generalizes to 3 banks / 2 rivers end-to-end — through the live budget gate (5th crossing rejected), the save guard (rejects delta by name), the canonical checkpoint (all 4 schema versions), and the real RL pixel frame (2 water bands).

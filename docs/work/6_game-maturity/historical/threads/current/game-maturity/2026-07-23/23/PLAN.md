# GM-09e plan — third alternate map (LAKE)

## Goal
A third map that adds VARIETY and proves the ONE map-layer generality dimension RIVER/DELTA never tested: a PARTIAL band (bounded on all four sides).

## Design (D-037)
`LAKE`: a single central lake rect (x∈[0.40,0.60]·width, y∈[0.34,0.66]·height) that spans NO screen edge; `spawn_regions` = a FRAME of four overlapping land strips (top/bottom full-width, left/right full-height, each eroded from the lake by station_size); `tunnel_budget=3`. `KNOWN_MAP_IDS == ("classic","delta","lake","river")`.

Distinct mechanic: because the lake spans no edge, a line can be DETOURED around it, so crossing is OPTIONAL — the budget caps SHORTCUTS (a straight line through the water saves distance) rather than gating connectivity. A soft strategic constraint, unlike the channels' mandatory crossings.

## Why a lake (not a rotated/extra channel)
RIVER/DELTA proved full-height channels + multi-band. Unproven: a band bounded in BOTH x and y. A lake is the cheapest test of `segment_crosses_band` on a bounded rect (a line enters+exits = one crossing; a detour = zero) — the geometry a future coastline/island relies on.

## Additivity
Same as GM-09d: the reused spawn (`_point_in_rects` accepts any region), render (`draw_terrain`/`draw_crossings` loop all bands), `path_crossings`, gate, `tunnels` observation, and save guard already handle a bounded band + a 4-region frame with no code change. CLASSIC/RIVER/DELTA byte-identical.

## Empirical validation (pre-code)
- Lake bounded on all 4 sides; 4 strips positive-area covering the frame.
- 800 stations across 40 seeds, 0 in the lake; top/bottom/left/right all reached.
- Line THROUGH the lake crosses 1; line AROUND (over the top) crosses 0.

## Tests (`test/test_gm09e_lake.py`, 11)
Registry/resolve (membership); one bounded water + 4-strip frame positive-area; partial-band (spans no edge); spawn around/never-in + glyph clearance; RNG-trajectory determinism; through=1 / detour=0 optional crossing; budget limits shortcuts not connectivity; CLASSIC/RIVER/DELTA unchanged + CLASSIC first-station guard; LAKE non-serializable (ValueError + lake@1); terrain paints the lake interior but not the dry corners.

## Review
Dual adversarial impl review (harness + Codex ultra). Focus: partial-band crossing edge cases (corner clip, tangent, boundary), spawn-frame coverage gaps, the optional-crossing/budget semantics, determinism, byte-identity.

## Deferred
GM-09f integrates map selection (in-game menu + save-schema map field + high-score mapDefinitionVersion) — next.

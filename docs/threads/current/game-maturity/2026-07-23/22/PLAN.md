# GM-09d plan — second alternate map (DELTA)

## Goal
Add a second map that proves the GM-09b/GM-09c map layer generalizes with NO new machinery — a pure `MapDefinition` addition.

## Design (D-036)
`DELTA`: two vertical rivers (channels at 0.32·width and 0.68·width, half-width 0.03·width) splitting the play area into THREE `station_size`-eroded banks (left/mid/right); `tunnel_budget=4`. Registered so `KNOWN_MAP_IDS == ("classic", "delta", "river")`.

Why two channels rather than a rotated single river: it stresses the newly-proven MULTI-band crossing count (a full-span line = two tunnels) and the finite budget across three banks — a horizontal river would only re-test a rotation `segment_crosses_band` already handles.

## Additivity (the load-bearing claim)
The reused machinery already handles N regions/rivers with NO code change:
- spawn: `_sample_position` accepts a candidate inside ANY of the regions (loop);
- render: `draw_terrain`/`draw_crossings` loop over all bands;
- crossings: `path_crossings` loops over all rivers;
- count/gate: `consumed_tunnels`/`within_tunnel_budget` sum over all crossings;
- save: `_require_classic_map` rejects any non-CLASSIC map.
So CLASSIC and RIVER stay byte-identical (unchanged `test_gm09a_maps` fingerprints + frozen `save-v1.json`).

## Empirical validation (pre-code)
- Three banks positive-area (left 527, mid 516, right 527 px at 1920×1080), non-overlapping the two channels.
- A full-span line crosses both channels (2 tunnels); a left-mid line crosses 1.
- Stations spawn on all three banks across 40 seeds, never in a channel.
- Budget 4 connects a left-mid-right network (2 tunnels used, 2 spare).

## Tests (`test/test_gm09d_delta.py`, 12)
Registry/resolve; three banks + two rivers positive-area; mid-bank between the channels; spawn on all three banks + never in water; determinism; full-span=2 / left-mid=1 crossings; budget-4 connects three banks; CLASSIC/RIVER unchanged + CLASSIC first-station guard; DELTA non-serializable; terrain paints two channels.

## Review
Dual adversarial impl review (harness + Codex ultra) — src/maps.py is a high-risk config change. Focus: geometry/solvability/determinism/byte-identity + generality of the reused spawn/render/crossing machinery for 3 regions / 2 rivers.

## Deferred
In-game map-menu selection + save-schema/high-score map fields → GM-09f. GM-09e (third map) next.

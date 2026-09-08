# GM-09b RIVER spawn feasibility (verified pre-plan-review)

Candidate RIVER geometry: a central vertical river band, x in [0.46, 0.54]·screen_width (8% wide), with the usual 0.1 padding inset; two land banks left/right.

Prototyped region-aware spawn = rejection-sample within [pad, 1-pad] bounds, reject if x is in the river band, bounded at 100 tries. Verified against the seeded `SimulationContext.python_random`:
- DETERMINISTIC: seed 0 sampled twice → identical positions.
- CONFINED: all 20 stations land on a bank, NONE in the river.
- TERMINATES fast: 20 stations need 20-26 rng draws across seeds 0-49 (~8% rejection), well under the 100-try bound (never hit).

So the additive integration is sound: `get_random_position` gains an optional river-exclusion (default None → no exclusion → CLASSIC byte-identical); the existing 8-candidate weighted-centroid structure in `get_station_spawn_position` is preserved (each candidate rejection-sampled onto a bank for RIVER). RIVER's stream diverges from CLASSIC's after the first excluded draw — expected (different map); CLASSIC (no exclusion) is unchanged. The 100-try bound guarantees termination and a fixed determinism contract.

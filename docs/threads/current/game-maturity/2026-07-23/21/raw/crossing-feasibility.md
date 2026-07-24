# GM-09c crossing-test feasibility (verified pre-plan-review)

A pure Liang-Barsky segment-vs-axis-aligned-band test (`segment_crosses_band(ax,ay,bx,by,band) -> entry Point | None`) verified against the live `RIVER.rivers[0]` band `(883.2, 0.0, 1036.8, 1080.0)`:
- left-bank→right-bank segment: CROSSES, entry `(883.2, 500.0)` (the band's left edge).
- entirely-left-bank / entirely-right-bank: `None` (no crossing).
- both-endpoints-inside-band: crosses, entry at start (won't occur — stations spawn on banks, never in the river — but handled).
- diagonal clipping the band: crosses, entry `(883.2, 433.2)`.
- deterministic (same inputs → same result).

So the pure test (no shapely, no pygame) works and returns the entry point the renderer needs. Determinism of a path's crossing count is structural: it walks CENTERLINES (`stations[i].position → stations[i+1].position` + loop closure), which are `path_order`-INDEPENDENT (only the lane-offset `PathSegment` geometry shifts with `path_order`). So a line's crossing count depends only on its logical route, and `available_tunnels = num_tunnels - Σ live-path crossings` is deterministic and stable — the derived-count design gives free rollback/refund.

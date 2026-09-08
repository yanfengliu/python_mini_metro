# Harness re-review (round 3) — GM-09c abort/pre-check-removal rework

Verdict: **FIX-FIRST**. Confirmed HEAD's pre-GM-09c `abort_path_creation` had no blip-clearing (via `git show`) — the new blip-clearing is a genuine behavior change. Named tests 48/48, full suite 1403 OK.

## MAJOR — `abort_path_creation` color-matched blip clearing is not inert + breaks CLASSIC byte-identity
The abort identifies "the draft's own blips" by COLOR equality, but the premise "color is unique" is false across time: `release_color_for_path` frees a removed line's color and `start_path_on_station` reclaims the first-free color, so a removed line's color can equal a live draft's while its snap-blips linger. `snap_blips` is serialized RAW into the canonical checkpoint (pruned only in `draw()`), so in headless/RL the lingering blips persist indefinitely.
- RIVER seed 0: build 3 `[2,0]` lines (line-1 leaves a C0 blip on `_RIGHT`); remove line1 (frees C0, blip lingers); start a draft that reclaims C0 and crosses twice; over-budget abort strips ALL C0 blips → deletes line-1's committed-then-removed blip → checkpoint before != after.
- **CLASSIC byte-identity broken even without reclaim**: HEAD's abort never touched `snap_blips`; the new abort clears them, so a CLASSIC drag-then-cancel yields a different checkpoint + frame than pre-GM-09c. Abort trigger is ordinary (mouse-up off a station mid-draft).
- Fix: remove exactly the blips the draft appended (capture `(station, blip)` as they fire, or snapshot `len(snap_blips)` per touched station), not all color-matched ones.

## Verified CORRECT (no findings)
- create gate (end/finish only): open within/over-budget correct; explicit-closure `[X,Y,X]` resolves to a 1-crossing 2-station loop, accepted; mid-repeat `[0,1,0,2]` counted at the finish commit boundary, cannot commit over budget. Distinct-color rejected creation IS inert.
- abort re-read after the release hook honors the live-rebind contract.
- `assign_paths_to_buttons` skip: a draft is always last in `host.paths`, so committed order/zip alignment is preserved; commit reassigns after clearing the flag; no ghost button.
- `num_tunnels` derived, commit-boundary gate, `within_tunnel_budget` reads `map_definition.tunnel_budget` — all hold. No over-budget commit found across open/loop/mid-repeat.

BLOCKER/MINOR/NIT: none. **Verdict FIX-FIRST** — the count invariant is intact; the one defect is `abort_path_creation` clearing blips by color, non-inert + CLASSIC-byte-breaking. (Resolved by reverting abort to pre-GM-09c; the blip/ghost-button are pre-existing and deferred.)

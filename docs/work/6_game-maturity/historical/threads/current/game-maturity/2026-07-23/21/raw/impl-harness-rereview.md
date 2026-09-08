# Harness re-review (round 2) — GM-09c fixes

Verdict: **FIX-FIRST**. Read live code + 3 probes + full suite (1401 OK).

## MAJOR — `path_lifecycle.py` create-path pre-check double-counts a 2-station there-and-back
The pre-check fed the RAW index list to `within_tunnel_budget` with no dedup, on the false claim that "the duplicate closing index a loop may carry is count-equivalent." A 2-station loop's closure RETRACES the single segment (charged once), but an explicit closing index makes the raw count a round trip `(X→Y)+(Y→X)` = 2.
- RIVER, budget 3: build `[2,0]`, `[2,1]` (consumed 2). `create_path_from_station_indices([2,0,2], loop=True)` → REJECTED, but the committed line would be the 2-station loop `[2,0]` consuming 1 (total 3 ≤ 3, within budget).
- The create pre-check DISAGREES with the no-dup create form, the interactive `end_path→finish` gates, and `replace_path` (which dedups in `_normalize`). Strictly over-STRICT: the pre-check count is always ≥ committed, so it never false-accepts an over-budget line — only false-rejects a buildable one.
- Fix: mirror `_normalize` (drop the trailing closing index; treat a there-and-back as the loop it becomes), or count the resolved centerline.

## MINOR — over-budget abort leaks a snap_blip (rejection not inert)
`add_station_to_path` fires `start_snap_blip` unconditionally; the finish/`end_path` gates run after and call `abort_path_creation`, which frees color + removes the path but does NOT clear the already-fired blip. Snap-blips are in the canonical checkpoint + save file, so the rejected commit isn't fully inert. Reachable in interactive play (drag a 4th crossing when budget exhausted → destination blip) and via direct bypass. Low impact: decays in 400ms, never affects gameplay/consumed-count, replay-deterministic. Fix: drop blips added during the aborted draft.

## No findings: BLOCKER none.
FIX 1 (`num_tunnels` derived property) clean — nothing writes it; save/load/checkpoint/RL never reference tunnels; `available_tunnels`/observation/map-swap all read live.

## Verdict: FIX-FIRST
The MAJOR is a real correctness regression on a supported input (a gate disagreement rejecting a within-budget line). Most important thing that held: the over-budget invariant — no path ever commits an over-budget crossing (pre-check count always ≥ committed), CLASSIC byte-identical, normal `end→finish` never over-rejects.

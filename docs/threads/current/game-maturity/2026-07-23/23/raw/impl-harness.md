# Harness impl review (GM-09e LAKE) — SHIP

Verdict: **SHIP**. No BLOCKER/MAJOR. Read live code + geometry/spawn/budget/save/render probes; 11/11 GM-09e, full suite 1427 OK, ruff+pre-commit clean.

## MINOR
1. `test_budget_limits_shortcuts_but_never_connectivity` (line 134) under-tests its contract — builds ONE line + returns; never fills the budget, rejects a 4th, or builds a zero-budget detour. CODE verified correct (3 committed → 4th rejected, detour allowed). FOLD: fill budget + reject 4th + non-crossing at zero.

## NIT
2. `crossings.py:32-37` "collinear edge unreachable" docstring now imprecise for LAKE — its vertical edges are integer x (768/1152), top/bottom banks eroded only in Y, so a station CAN spawn at x=768/1152 (sweep saw 2 at 768, 3 at 1152); a vertical line between two such stations runs collinear along the edge and counts 1 (probe). Measure-zero + defensible (x=768 is a water pixel), so soften the "unreachable" wording.
3. determinism-test comment says it catches "a spurious extra draw"; `project(0)==project(0)` catches non-determinism, not a deterministic spurious draw. Trivial.

## Verified NO findings (checklist)
- Partial-band crossing: enter+exit=1; diagonal-through-center=1; 1px interior clip=1; corner single-point=0; tangent/graze=0; segment ending on an edge=0; both-inside(geometry)=1; in-out-in=2; 2-station loop closure once. Robust.
- Spawn frame: 0 of 6000 stations (300 seeds) in the lake or overlapping; min center-to-lake gap exactly station_size(30). The 4 strips are the exact complement of the eroded lake; erosion axes compose correctly with get_random_position's 0.1 padding.
- Optional crossing/budget: through=1, detour=0; over-budget through rejected; detour allowed at full budget. tunnel_budget=3 intentionally loose (can always detour) — documented, acceptable [NOTE: Codex later refuted the "always detourable" claim — a station's only routes can all cross].
- Determinism/byte-identity: CLASSIC seed-0 fingerprint exact; maps.py diff = two pure-insertion hunks, zero deletions → RIVER/DELTA/CLASSIC byte-identical; LAKE seed-reproducible.
- Save/obs/checkpoint/render: serialize rejects `lake'@1` (structural guard); tunnels obs correct `{total:3,consumed:0,available:3}`; canonical_checkpoint v2/v3/v4 succeed; terrain fills [768,1152)x[367,712] corners dry.
- Test quality: avoided both traps — `assertIn` membership + `assertRaisesRegex(ValueError, r"lake'@1")`.
- Pre-existing/out-of-scope: `MiniMetroEnv.__init__` accepts no `map_definition` (RIVER/DELTA share this; full env-map integration is GM-09f); `--map lake` auto-accepted by the trainer via `KNOWN_MAP_IDS`/`map_by_id`.

**Single most important thing verified:** the PARTIAL-band crossing geometry (new generality dimension) counts correctly across the full adversarial matrix, and the 4-strip spawn frame left 0/6000 swept stations in the water with min clearance exactly station_size.

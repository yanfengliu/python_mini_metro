# Harness impl review (round 1) — GM-09c

Verdict: **SHIP** (with M1 acknowledged). No BLOCKER, no MAJOR.

Verification: read all live files; ran GM-09c 26/26 + full suite 1398/12-skip; wrote 3 probe scripts attacking determinism, rejection cleanliness, loop double-count, checkpoint leakage.

- **Determinism holds** — `consumed_tunnels`/`path_crossings` read only `station.position` + `is_looped`, never `path_order`/lane-offset/`PathSegment` geometry. Overlapping `[L,R]` lines with different lane offsets each count 1 → total 2. The `round()` is applied only to the returned marker Point; the count decision (`t_enter >= t_exit`) is made in float BEFORE the round, so rounding can never flip a count.
- **CLASSIC byte-identity holds** — `num_tunnels is None` → gate returns True with zero work; `consumed_tunnels` early-returns 0 on no-rivers; draws early-return. A rejected creation left BOTH Python + NumPy RNG states unchanged (probe). `_normalize_observation` rebuilds `structured` from an explicit key list omitting `tunnels`, so the checkpoint is untouched.
- **Counting correct** — 2-station loop closure = 1 (retrace guard `len>=3`); 3-station loop = 2, open = 1; multi-band each counted. Gate candidate contribution == the finishing/rerouted path's post-commit `consumed_tunnels` contribution for finish/extend/loop and reroute.
- **Gate-before-mutation** in `replace_path` (after read-only normalize + no-op short-circuit, before `build_candidate`/`snapshot_state`) — rejected reroute fully inert.

## MINOR — M1 (fixed in this change)
A rejected MULTI-station programmatic `create_path_from_station_indices([2,0,1])` at budget 0 leaks a snap-blip on intermediate station 1 (`snap_blips 3→4`) because that API drives the interactive machinery — `add_station_to_path` fires `start_snap_blip` before the `end_path_on_station` gate. Bounded (no tunnel consumed, no ghost path, no RNG draw, replay-deterministic), but contradicts the docstring's "mutates nothing" for the 3+-station path. Fix: preflight the budget in `create_path_from_station_indices` before `start_path_on_station`.

## NIT
- N1 — `TestGM09cCreationGate` only exercised 2-station lines; add a 3-station over-budget rejection asserting snap-blips/RNG unchanged.
- N2 — observation adds `tunnels` to CLASSIC's `structured` (`None/0/None`); by-design sibling block, suite-green.

**Single most important thing that could have been wrong but wasn't:** the determinism of the derived count (round() is post-count, station-centerline based, lane-offset-independent).

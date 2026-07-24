# GM-09c PLAN — Adversarial Review (harness lane, verbatim), verdict NOT CLEAN

## VERIFIED CORRECT (the two highest-risk claims hold)
1. DERIVED-COUNT ROLLBACK/REFUND — SOUND. `replace_path` rollback restores `path.stations`/`is_looped` (path_replacement_snapshot.py:38 path_names incl "stations"; restore_state 134-137) + `host.paths` (host_names 28); `consumed_tunnels = Σ path_crossings(p.stations, p.is_looped, rivers)` is a pure function of that restored state → restores free. `remove_path` rollback re-extends host.paths (path_removal_snapshot.py:181-184); the removed Path's .stations is never cleared → re-inserting restores its crossings. `available_locomotives = max(0, num_metros - len(self.metros))` (mediator.py:235) is the exact analogue. No new snapshot field required. A reroute reducing crossings refunds automatically. Transaction is atomic; consumed_tunnels only read outside it → no partial desync.
2. DETERMINISM via CENTERLINES — CORRECT. PathSegment.segment_start = start_station.position + buffer_vector*path_order (path_segment.py:47-48), buffer_vector round()-quantized (point.py:56-57) → shifts with path_order (changes as other lines add/remove) + integer-snapped. Station centerlines are path_order-independent + unrounded. Banks eroded so no station in [883.2,1036.8]; same-bank segment x < 883.2 never crosses; bank-to-bank crosses once. Deterministic. REFINEMENT: the reroute gate doesn't need build_candidate — replace_path already holds resolved `stations: list[Station]` from _normalize (path_replacement.py:432) + loop; `path_crossings([s.position for s in stations], loop, rivers)` is the candidate count directly.

## MAJOR — observation change breaks v4 checkpoint for ALL maps incl CLASSIC
env.py:222-230 fleet dict → recursive_checkpoint.py:150-156 _normalize_observation → recursive_checkpoint_carriages.py:20-25 (v4 pass-through all keys) → recursive_checkpoint_schema.py:242 `if set(fleet) != fleet_keys: raise` with _FLEET_KEYS_V4 (7 keys). Adding tunnels_* to the fleet dict → 10 keys → raise, on the DEFAULT CLASSIC env (test_recursive_checkpoint.py:22-45, gm06c contracts, the recursive-loop evidence path). Falsifies "no checkpoint change / CLASSIC unaffected". save_game unaffected (own doc + _require_classic_map). FIX: emit tunnels as a SIBLING structured["tunnels"] block; _normalize_observation reconstructs from a fixed whitelist + never copies unknown top-level keys → sibling ignored, fixtures valid. Add RIVER-env checkpoint coverage.

## MINOR
- M1: reroute gate can't live in _preflight (no `loop` param, path_replacement.py:232-238) — looped reroute would miscount. Put it in replace_path after _normalize/preflight (stations+loop in scope 432-439), guard `if self.num_tunnels is not None` (CLASSIC no-op). Place after the no-op short-circuit (440-445).
- M2: consumed_tunnels vs in-creation paths unpinned — start_path_on_station appends the draft while is_being_created (path_lifecycle.py:287-288). Decide: include drafts (finish gate reads directly) or exclude is_being_created (finish gate adds finishing path's crossings). Abort is clean (abort_path_creation discards draft 396-401; create_path_from_station_indices returns None on abort 325-327).
- M3: MapDefinition.tunnel_budget lacks __post_init__ validation (other fields validated maps.py:75-85). Validate None-or-nonnegative-nonbool-int. Structural equality in _require_classic_map stays correct.

## NIT
- N1: pin the tangency/collinear tie-break (t_enter==t_exit doesn't consume). Unreachable for vertical RIVER; pins a future diagonal river.
- N2: per-crossing (not per-line) — a loop spanning both banks consumes 2. Make explicit in Acceptance.
- N3: budget=3 solvability is a balance risk — verify empirically a seed-representative RIVER game is winnable within budget (no early cross-bank soft-lock). Keep tunable.
- Baseline refs: raw/recon.md doesn't exist (→ crossing-feasibility.md).

## Verdict: NOT CLEAN — the derived-count + centerline decisions are verified correct; resolve the checkpoint MAJOR (sibling tunnels block) + fold M1-M3/N1-N3.

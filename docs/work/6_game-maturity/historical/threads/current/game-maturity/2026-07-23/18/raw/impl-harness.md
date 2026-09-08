# GM-09a Implementation Review — Classic Map Abstraction (harness lane, verbatim)

**Verdict: CLEAN.** No MAJOR or MINOR defects. The highest-risk aspect (determinism byte-identity) is definitively proven; the save guard is correct and fail-closed. Only NITs.

## Determinism byte-identity — PROVEN, not asserted
Reconstructed the pre-change (HEAD) code in a scratch tree (reverted mediator.py/get_entity.py/save_game.py to HEAD, removed maps.py) and independently recomputed the test's fingerprints:
- Pre-change HEAD: CONSTRUCT {0: f6d2bee9a40b4ba1, 1: b7ca00b3088be0ec}, TRAJ {0: b98dcd7043a525d7, 1: 53f13c55d4e5b448}
- Post-change working tree: identical; both match the pinned values (test_gm09a_maps.py:43-44).
This proves the pinned fingerprints are genuine pre-change values (non-circular lock) AND the refactor reproduces them byte-for-byte.
Root cause of safety: random.Random.choice is `seq[self._randbelow(len(seq))]` — the draw depends only on len(seq), not type. Ran 20,000 seeds x 60 draws of choice(list) vs choice(tuple) on the real station_shape_type_list: 0 mismatches incl. post-draw RNG state. The idx>=10 short-circuit draws random() only at idx>=10 (unchanged). The unique-shape filter is a list comprehension in both, choice receives a list either way.

## Test sufficiency — the two seeds cover the critical paths
Seed 1 exercises the retry loop in get_initial_station_pool (retries=1 → extra full pool's RNG); both seeds hit the unique-shape branch (3 unique draws each). numpy position draws untouched by the refactor and pinned anyway. Sufficient.

## Remaining vectors (all clean)
- SAVE GUARD (save_game.py:30-46, called :215): fail-closed + correct. Classic passes; a map_definition-less Mediator returns early; deserialize_game rebuilds Mediator(seed=0)→CLASSIC so reload-then-resave passes; runs first among _require_* as a pure read; adds no bytes to raw; save-v1.json unmodified (frozen-fixture test passes).
- IMPORT SAFETY / CYCLES: maps.py imports only config + geometry.type (leaf enum); no path back to mediator, no cycle; subprocess import-safety test meaningful and passes; full 1336-test suite (which imports mediator→maps everywhere incl. env.py, rl/player_env.py) passes.
- IMMUTABILITY: CLASSIC deeply immutable — frozen + tuple fields + decoupled from the mutable config list (verified appending to config.station_shape_type_list does not bleed into CLASSIC).
- resolve_map: (classic,1)→CLASSIC singleton (is); (atlantis,1)→"unknown map id 'atlantis'; known maps: ['classic']"; (classic,2)→"unsupported version 2 for map 'classic'; supported versions: [1]". No wrong-map path.
- BEHAVIOR PRESERVATION: all get_random_stations callers (test_station/test_path/test_graph/test_gameplay) pass no palette kwargs → config globals → byte-identical. All Mediator sites (env.py, main.py, save_load.py, rl/player_env.py) use the CLASSIC default. Only the 4 stated files changed.

## Gates
Full suite 1336 passed / 12 skipped; ruff check + format clean on all 5 changed files.

## NITs (non-blocking; folded)
- MapDefinition had no __post_init__ tuple coercion (a future list-passer would get a mutable "frozen" instance). [FOLDED: added __post_init__ coercing palettes to tuple.]
- Test didn't document which seed covers which path. [FOLDED: added a coverage assertion that a fingerprinted seed reaches the unique-shape path.]
- The empty-available-uniques sub-branch is covered by the full-RNG-stream fingerprint but not specifically asserted. [No action required.]

**Bottom line: NOT a determinism or persistence risk. CLEAN.**

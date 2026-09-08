## Findings

- BLOCKER — none.

- MAJOR — [src/path_lifecycle.py:408](C:/Users/38909/Documents/github/python_mini_metro/src/path_lifecycle.py:408), [src/mediator.py:578](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:578) — the public `finish_path_creation()` commit boundary has no budget check. After spending all three tunnels, `start_path_on_station(2) → add_station_to_path(0) → finish_path_creation()` commits a fourth crossing: `consumed_tunnels == 4`, four paths remain live, and `available_tunnels` merely clamps to zero. Enforce `within_tunnel_budget` inside the final commit primitive, while retaining earlier preflight to avoid side effects.

- MAJOR — [src/path_lifecycle.py:307](C:/Users/38909/Documents/github/python_mini_metro/src/path_lifecycle.py:307), [src/path_lifecycle.py:381](C:/Users/38909/Documents/github/python_mini_metro/src/path_lifecycle.py:381) — rejected multi-station creation is not atomic. With three tunnels spent, creating `[0,1,2]` returns `action_ok=False` and leaves no path, but station 1’s `snap_blips` changes from empty to populated before the gate at line 433. Consequently, the canonical checkpoint changes and interactive audio can play a false snap. Preflight complete structured routes before creating a draft; keep provisional interactive feedback out of canonical station/audio state or roll it back exactly.

- MAJOR — [src/mediator.py:121](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:121), [src/crossings.py:100](C:/Users/38909/Documents/github/python_mini_metro/src/crossings.py:100) — the map-owned budget is duplicated into mutable `num_tunnels`, and missing/`None` fails open. Changing a live `Mediator(seed=1)` from `CLASSIC` to `RIVER` leaves `num_tunnels=None`; four crossing `[0,2]` lines are accepted despite `map_definition.tunnel_budget == 3`, producing `consumed=4, available=None`. A finite-map duck host lacking `.num_tunnels` fails identically. Make `num_tunnels` read-only and derived from `map_definition.tunnel_budget`; distinguish a missing attribute from an explicitly unbounded map.

- MINOR — [src/crossings.py:40](C:/Users/38909/Documents/github/python_mini_metro/src/crossings.py:40) — positive-length boundary grazing is charged. Against `(10,0,20,100)`, both `(0,0)→(30,0)` and `(10,-10)→(10,110)` return crossings although they never enter the band interior. A zero-length segment wholly inside also returns a crossing. Use nonzero, strict-interior intersection semantics and add edge-collinearity regressions.

- MINOR — [src/input_coordinator.py:445](C:/Users/38909/Documents/github/python_mini_metro/src/input_coordinator.py:445), [src/env.py:131](C:/Users/38909/Documents/github/python_mini_metro/src/env.py:131), [README.md:142](C:/Users/38909/Documents/github/python_mini_metro/README.md:142) — tunnel exhaustion returns only `{"action_ok": false}`, indistinguishable from malformed input, and the documented create/replace failure conditions omit the budget. Surface the offending route, tunnels required, and tunnels available, then document this rejection mode.

- NIT — none.

No further refutation was found for path-order independence, two-station-loop de-duplication, L→R→L counting, derived removal/reroute refunds, CLASSIC RNG/save/render compatibility, checkpoint fleet-key placement, budget-three solvability, or requested import discovery safety.

Relevant tests all passed: GM-09c 26/26, GM-09a/b compatibility 23/23, and save/render/checkpoint compatibility 18/18. The failing states above are uncovered by those tests.

Overall verdict: **REJECT** until the commit-boundary bypass, rejected-action mutation, and duplicated-budget fail-open are fixed.

# GM-09f3 Adversarial IMPLEMENTATION review — harness general-purpose lane (agentId a69a9827fc99171fc)

**Verdict: SHIP** (one MINOR test-strength gap noted, non-blocking — the code is correct and behavior is comprehensively proven).

Read live code, drove a real `AppController` through every path, empirically probed the gate and render geometry, ran the targeted suite (50 tests) and the full suite (1472 passed, 12 skipped), and mutation-tested the load-bearing seams. Ruff check + format clean.

## Attack-by-attack
1. RESTART-PRESERVES-MAP (the MAJOR) — NO FINDING. New Game surfaces (new_game :302 + K_RETURN :295) pass `current_map_id`; all three RESTART surfaces (pause :281, game-over R :321, game-over click :331) go through `_restart_current_game` → `_start_new_game(self.mediator.map_definition.map_id)`. Probe: played=river with picker on lake/delta → both pause-Restart and game-over-R rebuild river; Continue a river save then game-over-R → river. Production mediators always carry map_definition (fresh Mediator defaults CLASSIC; deserialize_game sets it via resolve_map).
2. SEAM ARITY — NO FINDING. Uniform `Callable[[str], GameTriple]`; no zero-arg call remains; all 11 factory fakes updated; the `_title_build_game(mediator=None)` collision fixed to `_title_build_game(map_id="classic", mediator=None)`; `map_by_id` always gets a registered id.
3. CYCLE — NO FINDING. Wraps KNOWN_MAP_IDS; `.index` can't fail; classic→delta→lake→river→classic.
4. RENDER — NO FINDING. Appending "map" keeps the five earlier rects byte-identical; the map rect (810,868,300,64) is on-screen; labels fit 300px ("Map: Classic" 174px); deterministic; the GM-07a `lambda surface, **kwargs` stub is compatible.
5. CONTINUE + TUTORIAL — NO FINDING. Continue installs the saved map via build_from, never the picker; tutorial stays Classic.
6. GATE COMPOSITION — NO FINDING. Mediator(seed=0, map_definition=map_by_id("river")) + create_path_from_station_indices([2,0]) → consumed_tunnels 0→1.
7. BLAST — NO FINDING. env.py/rl/player_env.py/recursive_playtest.py/scripts construct Mediator(...) directly, zero references to the picker; TRAINING_SOURCE_PATHS excludes the three touched files so the pinned RL training fingerprint doesn't rotate; the content-fingerprint test computes on a synthetic temp tree; menu_screens layout tests use subset checks. Fake surgery complete.
8. TEST STRENGTH — ONE FINDING. (a) restart-uses-picker CAUGHT; (b) new-game-uses-played-map CAUGHT; (c) drops map_by_id resolution NOT CAUGHT.

## MINOR — main.run_game's build_game map_by_id resolution not mutation-covered
Mutated main.py:221 to `map_by_id("classic")` and re-ran the run-loop + gm09f3 + gate suites — all 36 still passed. No test exercises main.run_game's real build_game with a non-classic selection (controller tests use fake spies; run-loop tests patch main.Mediator; the gate test builds Mediator directly). The feature's final end-to-end link could silently regress to "always Classic" with a green suite. Fix: add an integration test driving main.run_game with a non-classic selection, asserting the constructed mediator's map_definition.

## Severities: BLOCKER none; MAJOR none; MINOR one; NIT none. Verdict SHIP.

## Process note
During mutation-testing the reviewer ran `git checkout -- src/main.py`, which discarded the UNCOMMITTED GM-09f3 changes; it restored from a pre-mutation copy and verified the tree back to the exact original diff (19 files, 119 insertions / 37 deletions, no stray artifacts). Reminder: `git checkout -- <file>` is unsafe against uncommitted work; `git stash` or an explicit copy is the safe revert.

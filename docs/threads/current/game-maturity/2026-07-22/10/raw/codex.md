The unit is not ready to commit. I found one reachable blocker plus several fail-open validation and evidence gaps, despite all tests passing.

## Findings

1. **BLOCKER — ordinary gameplay can create a save that writes successfully but cannot load.**

   Evidence: service processing is sequential in [src/passenger_flow.py:321](/C:/Users/38909/Documents/github/python_mini_metro/src/passenger_flow.py:321). A later metro can consume a passenger referenced by an earlier metro’s cached service action. The saver’s preflight at [src/save_game.py:30](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:30) does not validate that cache, while loading rejects persisted timers without a derivable action at [src/save_load.py:296](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:296).

   Reproduction: seed 127, route `[0,1,2]`, assign one locomotive, 17 noops, assign another, then 94 noops. The first metro retains timers `(500, 0)` and a stale `BOARD` cache after the second metro takes its passenger. `serialize_game()` succeeds; `deserialize_game()` raises `ValueError`.

   Fix: canonicalize service caches after cross-metro effects/end-of-step, and add a pure saver preflight that refuses any non-canonical service state before opening the destination. Add this exact public-action round-trip regression.

2. **MAJOR — malformed RNG domains pass schema validation, sometimes raising non-contract exceptions or loading invalid values.**

   Evidence: [src/save_schema.py:176](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:176) checks RNG shape and integer types but not numeric domains. Native setters receive those values at [src/save_load.py:54](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:54).

   Reproductions:

   - Python state word `-1`: validation succeeds; loading raises `OverflowError`.
   - Python state index `999`: validation succeeds; loading raises native `ValueError`.
   - NumPy state `-1`: validation succeeds; loading raises `OverflowError`.
   - NumPy `has_uint32=2`: validation succeeds and the save loads.

   This also contradicts the malformed-RNG/`ValueError` promise in [README.md:217](/C:/Users/38909/Documents/github/python_mini_metro/README.md:217).

   Fix: validate MT words, terminal index, PCG64 state/inc bounds, `has_uint32 ∈ {0,1}`, and cached `uinteger`; normalize setter failures to `ValueError` before constructing a `Mediator`.

3. **MAJOR — station-reference validation accepts topology the loader/runtime cannot support.**

   Evidence: reference validation builds its station set from the entire 20-station pool at [src/save_schema_records.py:327](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema_records.py:327), but loading exposes only the active prefix at [src/save_load.py:83](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:83). Graph construction indexes only active nodes at [src/graph/graph_algo.py:14](/C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:14).

   Reproductions:

   - Replacing a path station with a locked station passes validation and then produces a raw `KeyError` during graph construction or the first step.
   - A metro’s `currentStationId` can be removed from its owning path while the document remains valid; loading produces an impossible off-route service state.
   - The saver also derives activity solely from list position at [src/save_game.py:58](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:58), silently normalizing a non-prefix active-station list.

   Fix: require path stations to be active, require current stations to be active and consistent with their owning path/segment, validate other graph-consumed references similarly, and reject non-prefix live station collections during serialization.

4. **MAJOR — loader silently changes persisted metro speed.**

   Evidence: speed is restored at [src/save_load.py:212](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:212), service reconciliation forces bound metros to speed zero at [src/passenger_capacity.py:258](/C:/Users/38909/Documents/github/python_mini_metro/src/passenger_capacity.py:258), and the loader then reapplies only service timers at [src/save_load.py:292](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:292).

   Reproduction: change a valid mid-stop metro’s serialized speed from `0` to `0.123`. Validation accepts it, loading returns speed `0`, and re-saving emits `0`. This is silent normalization rather than exact restoration or rejection.

   Fix: require persisted speed zero whenever a bound service action is derivable, or validate post-reconciliation speed against the record and fail closed.

5. **MAJOR — duplicate JSON object keys bypass strictness.**

   Evidence: [src/save_load.py:331](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:331) uses default `json.loads`, which collapses duplicate keys before exact-key validation.

   Reproduction: a document containing an early `"schemaVersion":999` and a later `"schemaVersion":1` loads successfully.

   Fix: use an `object_pairs_hook` that rejects duplicate keys at every object level before schema validation.

6. **MAJOR — the required atomic-failure and partial-reconstruction tests do not exercise their claimed seams.**

   Evidence:

   - The atomicity test at [test/test_gm07b_load_reconstruction.py:365](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_load_reconstruction.py:365) enables path creation, so saving exits at [src/save_game.py:33](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:33), before `mkstemp`, `fsync`, or `os.replace` at [src/save_game.py:234](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:234).
   - The “mid-way load failure” test at [test/test_gm07b_load_reconstruction.py:316](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_load_reconstruction.py:316) creates a schema contradiction rejected before `Mediator` construction at [src/save_load.py:314](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:314).

   A cleanup or reconstruction regression could therefore retain a green suite.

   Fix: inject failures after temporary-file creation at write/flush/fsync/replace, covering existing and absent destinations. For reconstruction, use schema-valid data that fails after construction, then prove no partial state or RNG effects escape.

   Manual fault injection against the current implementation found both `fsync` and `replace` cleanup sound; this finding concerns the missing binding regression.

7. **MAJOR — cross-process trajectory evidence is paused and does not test hash-seed independence.**

   Evidence: fixture creation holds the menu at [test/test_gm07b_save_determinism.py:163](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:163); the worker steps without releasing it at [test/test_gm07b_save_determinism.py:79](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:79). Both workers are also assigned `PYTHONHASHSEED=0` at [test/test_gm07b_save_determinism.py:233](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:233).

   Ten paused no-op checkpoints cannot prove active replay, and identical seed zero runs cannot prove hash-seed independence.

   Fix: release the menu, run far enough to exercise movement and spawning, compare against a never-saved control, and use distinct hash seeds. Narrow [red-evidence.md:18](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-22/10/red-evidence.md:18) until then.

8. **MINOR — the isolation regression omits half the new modules and the checkpoint boundary.**

   Evidence: `SAVE_MODULE_NAMES` lists only `save_game` and `save_schema` at [test/test_gm07b_save_determinism.py:27](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:27), excluding `save_load` and `save_schema_records`. Scan targets at [test/test_gm07b_save_determinism.py:274](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:274) omit `recursive_checkpoint.py`.

   Fix: forbid imports of all four modules—or the `save_*` namespace—and include the checkpoint verifier in the scan.

9. **MINOR — documentation overstates current evidence and API reachability.**

   Evidence:

   - [PROGRESS.md:153](/C:/Users/38909/Documents/github/python_mini_metro/PROGRESS.md:153) still says two red assertions remain open, although the focused suite is now 48/48.
   - [README.md:221](/C:/Users/38909/Documents/github/python_mini_metro/README.md:221) and [ARCHITECTURE.md:386](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:386) imply all stable entity IDs are structured-action selectors. Live action handling accepts path IDs at [src/fleet_input.py:19](/C:/Users/38909/Documents/github/python_mini_metro/src/fleet_input.py:19); station, metro, carriage, and passenger IDs currently support observation/reference identity, not equivalent action selection.

   Fix: remove the obsolete red-status sentence and distinguish observation/reference IDs from presently accepted action selectors.

## Claims attacked and confirmed sound

- Focused GM-07b suite: **48/48 passed**.
- Full suite: **1,129 tests passed, 12 skipped**.
- Valid Python and NumPy RNG states round-trip exactly, including deep tuple reconstruction, without changing host-global RNG state.
- A stronger manual active-play probe remained checkpoint-identical for 100 ticks under hash seeds 0, 1, and 777.
- Construction order, post-construction IDs, empty-fleet segment generation, manual metro binding, segment rebinding, direct station-queue restoration, metro-overfill rejection, node path-set reconstruction, ordered color maps, blink restoration, and button-lock equality are correct for canonical inputs.
- Serialization remained pure in the tested canonical states, including direct `TravelPlan.next_station` access.
- Current atomic writer behavior survived injected `fsync` and `os.replace` failures: the old destination remained intact and temporary files were removed.
- Live runtime, RL, recursive-playtest, and checkpoint modules have no save imports; frozen replay fixtures were unchanged.
- No gameplay files changed beyond the new configuration constant, and no files were edited during this review.

NOT CLEAN

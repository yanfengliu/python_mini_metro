## Verdict

NOT CLEAN. The core legacy-hash mechanism is sound, but several surrounding paths would violate it or execute a different map than the recorded identity.

Live verification: the existing descriptor is serialized by sorted, compact JSON at [src/rl/protocol.py:347](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/protocol.py:347). The real v1 manifest reconstructs through [src/rl/training.py:264](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/training.py:264) to exactly `c2ef342f9cedfc3b7292ec2517ec7ccca7b2dcf9b49811c6dec529c25e73933e`. Its descriptor is 645 bytes; adding the three planned Classic keys produces 710 bytes and `efec72daa45f34215d76eb0c02631e2f3d2e09718ae52f1d3c1b522938619d03`.

Therefore, adding keys exclusively in the map-bound branch does preserve map-absent bytes. Sorting only sorts keys that exist. This remains true only if `(map_id, map_definition_version)` stays exactly `(None, None)` throughout every legacy path.

## Findings

1. **MAJOR — `--map classic` as a parser default rejects legacy resume.**

   Evidence: training constructs its requested `TaskSpec` before reading the resume manifest at [scripts/train_rl.py:223](/C:/Users/38909/Documents/github/python_mini_metro/scripts/train_rl.py:223), then compares that fingerprint at [scripts/train_rl.py:257](/C:/Users/38909/Documents/github/python_mini_metro/scripts/train_rl.py:257). Evaluation instead reconstructs directly from the manifest at [scripts/evaluate_rl.py:217](/C:/Users/38909/Documents/github/python_mini_metro/scripts/evaluate_rl.py:217).

   Failing scenario: `train_rl.py --resume legacy.zip` with omitted `--map` creates a map-bound Classic spec and compares `efec72da…` against stored `c2ef342f…`, failing before legacy reconstruction. In evaluation, the default would either be ignored or cause the same incompatibility.

   Fix: parse omission as `None`. Resolve omitted map to Classic only for fresh training. For resume/evaluate, omission means “inherit manifest identity”; an explicitly supplied map is a post-reconstruction compatibility assertion. Keep `TaskSpec()` and default `PlayerPixelEnv()` map-absent; only the operational Mediator defaults legacy absence to Classic.

2. **MAJOR — the promised real-manifest regression is unavailable in a clean checkout.**

   Evidence: the test source is [output/rl/recurrent-final-smoke-20260711/training-manifest.json:1](/C:/Users/38909/Documents/github/python_mini_metro/output/rl/recurrent-final-smoke-20260711/training-manifest.json:1), but [.gitignore:13](/C:/Users/38909/Documents/github/python_mini_metro/.gitignore:13) ignores `/output/`.

   Failing scenario: CI or a fresh worktree cannot run the highest-risk regression despite the plan requiring it.

   Fix: commit sanitized exact v1 bytes under `scripts/fixtures/`, or embed equivalent frozen bytes in the test. Assert both canonical descriptor bytes and the full `c2ef342f…` hash.

3. **MAJOR — “seed-N station bytes” cannot prove deterministic compatibility.**

   Evidence: every station first consumes a base-shape choice, then possibly a unique-chance and ordered unique choice at [src/entity/get_entity.py:79](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/get_entity.py:79). Position generation consumes two NumPy draws for station zero and sixteen NumPy draws plus a Python weighted choice thereafter at [src/entity/get_entity.py:22](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/get_entity.py:22). The Mediator discards complete pools until the initial shapes qualify at [src/mediator.py:343](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:343), after which path colors and spawn intervals consume more Python draws at [src/mediator.py:132](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:132) and [src/passenger_flow.py:92](/C:/Users/38909/Documents/github/python_mini_metro/src/passenger_flow.py:92).

   Station bytes are themselves unusable because IDs contain unseeded short UUIDs at [src/entity/station.py:23](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/station.py:23). A live probe found seed `1` rejects two full pools before accepting the third; seed `0` exercises all three unique shapes.

   Failing scenario: the rewrite skips the otherwise-unused base choice when a unique wins, stops drawing unique chances after exhaustion, or inserts one post-pool draw. Initial shapes may look correct while path colors, spawn intervals, and the training trajectory diverge.

   Fix: preserve the exact call, list, filter, arithmetic, and retry order. Pin an ID-free station projection plus both RNG states, ordered path colors, spawn intervals, and a short canonical trajectory—the existing checkpoint already captures these at [src/recursive_checkpoint.py:436](/C:/Users/38909/Documents/github/python_mini_metro/src/recursive_checkpoint.py:436). Test seeds `0` and `1` under distinct `PYTHONHASHSEED`s. Snapshot the mutable config shape lists at [src/config.py:29](/C:/Users/38909/Documents/github/python_mini_metro/src/config.py:29) into ordered tuples; a frozen dataclass containing the original lists is not actually immutable.

4. **MAJOR — ID-only lookup does not enforce `map_definition_version`.**

   Evidence: workers currently rebuild solely from thunk fields at [src/rl/training.py:95](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/training.py:95), and evaluation permits explicit content drift at [src/rl/manifest.py:210](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest.py:210). The plan supplies only `map_by_id(map_id)`.

   Failing scenario: a manifest self-consistently claims `classic@2`, but the ID lookup returns current `CLASSIC@1`; conversely, after Classic advances, an old `classic@1` manifest silently executes v2.

   Fix: resolve or validate the exact `(map_id, map_definition_version)` pair before model access and again in the spawned environment. Legacy `(None, None)` should operationally resolve to Classic without changing its map-absent task identity. Test direct thunk and spawned-process version mismatches.

5. **MAJOR — manifest v3 needs stronger schema and identity invariants than the plan specifies.**

   Evidence: the current “latest” alias is also the explicit v2 branch at [src/rl/manifest_schema.py:14](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest_schema.py:14). Both history emission and v2 parsing compare against that alias at [src/rl/manifest_schema.py:219](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest_schema.py:219) and [src/rl/manifest_schema.py:252](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest_schema.py:252).

   Failing scenarios:

   - Changing `TRAINING_MANIFEST_SCHEMA` to v3 without explicit v2 branches makes v2 parsing unsupported and causes v2 `to_dict()` to omit its required history keys.
   - `TaskSpec(None, version=1)` aliases genuine legacy bytes, while `TaskSpec("classic", None)` can mint a descriptor containing `null`.
   - Optional map fields can remain hidden inside v1/v2 objects or be absent in v3.
   - `create_training_manifest` currently accepts task fields and fingerprint independently at [src/rl/manifest.py:61](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest.py:61), allowing map fields and fingerprint to disagree.

   Fix: retain explicit V1, V2, and V3 constants; use `_V3_KEYS = _V2_KEYS | {...}`; emit history for v2/v3 and maps only for v3. Require exactly `(None, None)` or `(nonempty canonical ASCII ID, positive non-bool version)` in `TaskSpec`; require v1/v2 mapless and v3 map-bound in `TrainingManifest.__post_init__`. Derive schema, task fields, map fields, and fingerprint from one `TaskSpec` in the factory. Test complete v1/v2/v3 object round-trips, not just parsing.

6. **MAJOR — high-score identity is incomplete, and the normal promotion seam would silently lose map access.**

   Evidence: D-009 requires both map ID and definition version in high-score identity at [DECISIONS.md:57](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:57). The live schema and grouping contain only `(map, rulesVersion)` at [src/highscores.py:32](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:32) and [src/highscores.py:94](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:94).

   Additionally, normal promotion passes only `deliveries` through [src/app_controller.py:134](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:134), and `main` wraps it in a `SimpleNamespace` containing only that scalar at [src/main.py:241](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:241). Replacing the hardcoded map access at [src/main.py:119](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:119) with `mediator.map_definition` would raise and then be swallowed, silently stopping normal score recording.

   Fix: introduce a backward-compatible high-score v2 keyed by `(map, mapDefinitionVersion, rulesVersion)`, normalizing v1 `"classic"` entries to version `1`. Pass the active map pair through the promotion seam and test both promotion and window-close races. `HIGHSCORES_MAP_CLASSIC == "classic"` at [src/highscores.py:35](/C:/Users/38909/Documents/github/python_mini_metro/src/highscores.py:35) is correct and must remain the exact wire map value.

7. **MAJOR — save deferral is sound only with a fail-closed Classic-only boundary.**

   D-026 explicitly supports map absence while there is one implicit map at [DECISIONS.md:165](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:165). Save v1 has no map key at [src/save_schema.py:53](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:53), serialization accepts any Mediator at [src/save_game.py:193](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:193), and loading always constructs the default Mediator at [src/save_load.py:305](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:305).

   Failing scenario: once the public `MapDefinition`/Mediator path accepts a non-Classic definition, save v1 records it without identity and reloads it as Classic. Therefore “GM-09b or GM-09f” is too loose.

   Fix: without changing serialized bytes, reject save-v1 serialization unless the active definition is exactly `classic@1`, or keep non-Classic definitions unconstructible through save-capable Mediators. The schema migration must land before the first alternate map becomes constructible, no later than GM-09b. With that guard, deferral is valid, the frozen `save-v1.json` should remain byte-identical, and neither the present RL nor high-score path needs to read map identity from a save.

8. **MAJOR — the proposed `maps.py` ownership contradicts its import-isolation requirement.**

   Evidence: current generation requires `Station`, `Metro`, and shape construction at [src/entity/get_entity.py:14](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/get_entity.py:14); those entity modules import pygame at [src/entity/station.py:3](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/station.py:3) and [src/entity/metro.py:4](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/metro.py:4). Meanwhile, [src/rl/protocol.py:1](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/protocol.py:1) deliberately defines a dependency-free boundary.

   Failing scenario: `maps.py` wraps `get_entity` and therefore pulls gameplay/pygame; if `get_entity` also imports `MapDefinition`, the modules cycle.

   Fix: keep `maps.py` data/registry-only and deeply immutable. Let `entity/get_entity.py` consume a `MapDefinition` one-way and retain station materialization. Do not import the map registry from `rl/protocol.py`; TaskSpec should validate primitive identity fields only. Add fresh-process blocked-module checks and both import orders.

9. **MINOR — map-owned station counts are not actually authoritative.**

   `Mediator` constructs progression from global counts before generation at [src/mediator.py:103](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:103), then slices using those values at [src/mediator.py:132](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:132).

   Failing scenario: a MapDefinition’s `num_stations` differs from globals, so generation, unlock milestones, and active slicing disagree.

   Fix: resolve the definition before progression and derive all count-dependent state from it, or omit those fields until the progression integration unit. Classic/default/context-injected construction should be equivalent.

10. **MINOR — session identity, profiling, and documentation are additional omitted surfaces.**

   `MiniMetroEnv.reset()` recreates a bare Mediator at [src/env.py:46](/C:/Users/38909/Documents/github/python_mini_metro/src/env.py:46), and its structured observation has no map identity at [src/env.py:164](/C:/Users/38909/Documents/github/python_mini_metro/src/env.py:164), despite the roadmap’s structured-session requirement at [PLAN.md:217](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/PLAN.md:217). The profiler still uses mapless `TaskSpec()` at [scripts/profile_rl_history_worker.py:358](/C:/Users/38909/Documents/github/python_mini_metro/scripts/profile_rl_history_worker.py:358), while [README.md:256](/C:/Users/38909/Documents/github/python_mini_metro/README.md:256) says every fresh artifact is v2.

   Fix: preserve the selected definition across structured resets and either expose its pair now or record a second explicit GM-09f deferral. Bind new profiling evidence to `classic@1`, and update README, architecture, progress, and public signatures.

The milestone is conceptually coherent, but it should be implemented as two separately reviewed units: first the immutable Classic abstraction plus full RNG/checkpoint parity, then task/manifest/CLI/env/high-score identity. That isolates deterministic behavior changes from persistence/versioning failures, especially with `mediator.py` already at 831 lines and the train/main entry points near the 500-line target.

**NOT CLEAN — 8 MAJOR defects and 2 MINOR omissions; blockers are legacy resume rejection, incomplete RNG proof, unenforced map versions, and incomplete persisted identity.**

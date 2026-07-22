## 2026-02-08

- Added programmatic play in `src/env.py` with structured and NumPy observations.
- Added high-level actions in `src/mediator.py` (create/remove paths, pause/resume, step time).
- Added agent playthrough logging and replay helpers in `src/agent_play.py`.
- Added game-over rules for passengers waiting too long in manual and programmatic play.
- Added game-over overlay with final score and stopped the main loop on game-over.
- Added clickable restart/exit buttons and keyboard shortcuts on the game-over screen.
- Added unlock blink for newly available stations and metro-line buttons (3 blinks in 1 second).
- Passed `time_ms` through rendering so blink timing is deterministic.

## 2026-02-14

- Added progressive metro line unlock milestones tied to cumulative travels handled: 1 line at start, then 2/3/4 at 100/250/500 travels.
- Switched line colors to runtime-randomized color allocation so each run can produce a different line color set.
- Added game rules documentation in `GAME_RULES.md` describing unlock thresholds and randomized line color behavior.
- Expanded `GAME_RULES.md` into a full implementation-aligned rules reference covering objective, stations/passengers, lines/metros, progression, routing, spawning, game-over, controls, and programmatic actions.
- Updated locked path button visuals to draw as empty ring outlines (edge-only) instead of filled circles, and synchronized lock state updates with unlock progression.
- Added station progression tied to cumulative travels: start with 3 stations, then unlock additional stations at 30, 80, 150, 240, ... travels (increment +20 each unlock) up to 10 stations.
- Added mediator logic to spawn newly unlocked stations from a pre-generated station pool while preserving existing station/path state.
- Updated `GAME_RULES.md` with station unlock progression details.
- Fixed path button color regression so unlocked line buttons keep the assigned metro line color instead of being reset to default gray on lock-state refresh.
- Fixed path rendering order centering so active paths are offset around zero based on current path count, preventing single-path geometry from self-crossing due to forced negative offsets.
- Switched passenger spawning from one global cadence to per-station rhythms by tracking station-specific spawn intervals/timers and spawning passengers independently per station.
- Changed station unlock baseline to 10 travels and updated `GAME_RULES.md` milestones.
- Added keyboard speed controls (1x/2x/4x via keys `1`/`2`/`3`) and wired simulation timing, metro movement, spawn-step progression, and wait-time updates to respect the selected speed.
- Updated controls docs in `README.md` and `GAME_RULES.md`.
- Fixed passenger route selection to prefer the shortest reachable destination route (with transfer-aware tie-breaking) so riders board eligible metros instead of waiting for longer alternatives.
- Updated boarding behavior so waiting passengers can board the first arriving metro with space when that metro can still lead to a valid destination route, even if their prior plan targeted another line.
- Increased station cap from 10 to 20 by updating `num_stations` in `src/config.py` (unlock milestones now generate up to 20 stations).
- Updated path unlock milestones to `[0, 90, 300, 650]` in `src/config.py`.
- Added pre-timeout passenger warning blink: passengers in the last 10 seconds before `passenger_max_wait_time_ms` now blink on/off in station queues.
- Threaded render-time wait thresholds through holder/station rendering so passenger warning blink is deterministic from mediator time.
- Added resolution-adaptive rendering via a virtual game surface + viewport transform (`src/ui/viewport.py`) with letterboxed scaling to resizable windows.
- Updated main-loop rendering/input flow to draw to virtual space, scale to the window, and remap mouse events from window coordinates back into virtual coordinates.
- Refactored game-over overlay and path-button layout to compute positions from render-surface dimensions instead of fixed screen constants.
- Updated `GAME_RULES.md` line/station progression and passenger spawning timing details to match current implementation.
- Added rare one-of-a-kind station shapes (diamond, pentagon, star) and shape rendering support.
- Added station-pool generation logic so unique shapes can only appear after the 10th station slot and at most once each per run.
- Updated `ARCHITECTURE.md` to reflect the latest project file structure.
- Fixed passenger wait blink logic so passengers at or past the max wait threshold also blink instead of only pre-timeout passengers.
- Fixed path segment offset direction to use a stable station-pair orientation so reversed A/B segments stay parallel and no longer cross each other.
- Added metro motion profiling with 1-second acceleration and 1-second deceleration, including graceful handling for short inter-station distances.
- Added conditional metro station stops so metros only dwell when there are eligible passengers to board that line.
- Added boarding-duration timing at stations so each boarding passenger consumes 0.5 seconds of dwell time.
- Fixed metro stop-planning crash on padding segments by guarding next-station lookup when a segment endpoint is not a station.
- Fixed zero-length direction vectors to return `(0, 0)` so metro rotation never receives NaN angles on collapsed/zero-distance segments.
- Fixed metro station-dwell deadlock by only scheduling boarding stops when metro capacity is available now or will be freed by alighting at that station.

## 2026-02-15

- Changed metro line unlocks to score purchases by clicking locked path buttons instead of auto-unlocking from travels.
- Kept unlock milestone economics by using incremental line purchase prices derived from `[0, 90, 300, 650]`.
- Added locked-button hover buy hints with two lines of text (`Buy` and price), using gray text when unaffordable and black text when affordable.
- Updated game rules docs for purchase-based line unlocks and the new locked-button hover/click behavior.
- Changed UI font usage to `courier` via shared `font_name` config.
- Expanded `README.md` programmatic play docs to list the `MiniMetroEnv` API, action schemas, valid input constraints, and observation/step return fields.
- Added programmatic `buy_line` action to purchase metro lines through `env.step(...)`, with optional `path_index` targeting and validation.

## 2026-02-16

- Improved random metro line color generation to prefer hues that are more distinct from already selected line colors.
- Added color-distance helper utilities and tests for hue wrap distance and distinct hue selection behavior.
- Changed station pool generation so new station positions are less likely to spawn far from the current station cluster center.
- Changed metro rendering so passenger icons are displayed inside each metro car in a 2x3 grid that moves with the car.
- Improved metro passenger icon spacing and rotated passenger icon placement to follow metro car orientation.
- Rebalanced metro passenger slot layout to a uniform 3x2 in-car grid to prevent overlap while preserving car-aligned rotation.
- Updated metro passenger slot spacing so row and column icon gaps match the side margins inside the metro car.

## 2026-02-17

- Added station snap blips: when a line endpoint snaps onto a station during path creation, the station emits a short outward ring in the line color.
- Triggered snap blips for both drag-snap station additions and direct line-complete snaps on mouse release.
- Added station and mediator tests covering snap blip lifecycle, rendering, and snap-trigger calls.
- Updated `GAME_RULES.md` to document the station snap-blip behavior during line creation.
- Added bottom-left simulation speed controls (`Pause`, `1x`, `2x`, `4x`) with clickable UI buttons wired to pause and speed state.
- Switched speed-control button labels to iconography: pause bars, single play, double play, and four-play symbols.
- Changed runtime-randomized metro line colors to a less saturated palette for softer visuals.
- Updated metro passenger rendering so passenger icon orientation rotates with the car instead of staying upright.

## 2026-04-28

- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added an initial review artifact directory.
- Moved review artifacts under the docs thread area and documented robust full-codebase Codex/Claude review commands.
- Ran the first full-codebase review, fixed terminal-state API mutation, malformed action handling, loop routing closure, stale travel-plan cleanup, the graph node hash contract, and the stale Ruff pre-commit hook, then added focused regressions.
- Renamed review artifacts into the broader `docs/threads/` lifecycle, with active work in `current/`, completed work in `done/`, and completed `full` and `agents-repo-fit` themes migrated under `done/`.

## 2026-07-10

- Onboarded the deterministic proposal-only recursive playtest with fresh-process verification, exact local and civ-engine runtime provenance, crash-recoverable manifest/ledger finalization, promoted regression coverage, and stable equal-cost BFS routing.
- Rebuilt the player presentation boundary around fixed 60 Hz updates, metro interpolation, immutable symmetric route layouts, bounded antialiased route caching, lazy headless-safe resources, prepared first-frame hitboxes, pure geometry drawing, and deterministic software-surface rendering; refreshed the warm minimal visual style and outlined line-colored metros without changing balance or mechanic constants.
- Added a player-equivalent Gymnasium pixel environment with isolated seeded simulations, a fingerprinted low-level mouse/keyboard protocol, exact fixed-step decisions, strict terminal metrics, and a deterministic positive-delivery curriculum; added a compact frame-stacked PPO training/evaluation stack with spawn-safe workers, content-compatible manifests, hashed artifacts, and opt-in cross-content evaluation.
- Finalized the RL setup with universal hashed core/RL locks, exact-byte artifact authentication, authoritative train/evaluation seeds, authenticated resume and drift-safe evaluation, real spawned PPO lifecycle coverage, pinned recursive compatibility evidence, and fresh/resume Windows CI smoke tests.

## 2026-07-11

- Researched visual RL architectures and evaluation practice, documented the model-selection rationale, and upgraded fresh training to an eight-frame SB3-Contrib RecurrentPPO policy with separate actor/critic LSTMs, delivery-total-aligned returns, recurrent evaluation state, manifest-bound resume settings, feed-forward PPO/frame-stack ablation controls, a measured lower-memory recurrent batch default, censoring-aware delivery reports, and authenticated pre-recurrent PPO compatibility coverage.
- Stabilized path-button gameplay tests after Linux CI exposed a global-random station-overlap flake; replacement stations now use each mediator's isolated seeded simulation context.
- Opened a persistent, adversarially reviewed game-maturity thread with an exact remote resume transaction, dependency-ordered product work units, canonical delivery/credit migration, reproducible initial overload evidence, a resource-estimated twelve-frame multiscale-history candidate pending live profiling, per-experiment durability, and explicit completion gates spanning gameplay, architecture, persistence, content, balance, and long-horizon RL evaluation.
- Separated lifetime passenger deliveries from spendable line credits, aligned structured rewards with the delivery objective, and versioned agent-play/checkpoint/recursive evidence with genuine v1 reconstruction, strict v2 contracts, fail-closed reward-mode checks, fresh-process verifier coverage, and sub-500-line recursive contract/checkpoint modules.
- Replaced ambiguous score presentation with a canonical deliveries/line-credits HUD and delivery-first game-over result, added compact-layout and pixel-sensitivity regressions with before/after evidence, and corrected the documented passenger cadence using executable 1x/2x/4x, full-station, and quantization tests.
- Raised the fresh-game overdue-passenger threshold from one to two so the first overdue station passenger warns and the second ends the game, retained writable compatibility aliases, and versioned recursive and agent-play evidence to v3 while replaying genuine v1/v2 records at the historical threshold.

## 2026-07-12

- Added immutable temporal-history descriptors and separately authenticated fingerprints in training-manifest v2, exact manifest-v1 contiguous-stack normalization and byte preservation, fail-closed pre-wrapper train/evaluation guards, and focused schema/legacy coverage while retaining the eight-contiguous-frame runtime default pending the vector-history and resource-profile stages.
- Added a bounded per-environment `uint8` temporal-history ring with exact multiscale chronology, zero pre-history, isolated terminal/reset stacks, fail-closed recovery, contiguous `VecFrameStack` equivalence, and pinned candidate memory accounting; runtime integration remains staged for GM-02c.
- Integrated exact manifest-declared temporal history across fresh training, resume, and evaluation; added mutually exclusive contiguous/named controls, recurrent and spawned multiscale coverage, genuine old-stack compatibility, model-space mismatch checks, evaluation history reporting, and a Windows multiscale lifecycle smoke while retaining eight contiguous frames as the unpromoted default.
- Added a test-first matched-history resource profiler with cyclic fresh-process campaigns, exact storage/padded-batch/MAC and promotion contracts, a production-horizon two-update RecurrentPPO worker, and a dependency-free Windows launcher/descendant working-set supervisor; the harness is staged for remote verification before any default-promotion measurements run.

## 2026-07-13

- Ran the remotely gated matched-resource campaigns, rejected the operationally invalid primary result, promoted the fully valid ten-frame multiscale fallback within the preregistered RAM/throughput gates, made that exact descriptor the fresh recurrent default while preserving explicit PPO's contiguous-eight behavior and persisted resume identity, and made invalid/incomplete/mismatched campaign aggregates fail closed.
- Reframed the ten-frame recurrent policy as the bounded player-pixel baseline and added a reviewed GM-12 research ladder for compact semantic strategy state, direct assisted hybrid policies, and pixel-only actors trained with privileged teachers/auxiliary critics; each lane keeps truthful protocol/task identity and is promoted only by matched held-out passenger deliveries.
- Split the 1,158-line mediator characterization suite into a shared fixture plus six behavior-focused modules under 500 lines, preserving all 57 test bodies, three helpers, and six explanatory comments exactly while leaving production code unchanged.
- Extracted line/station/economy progression into a dependency-free single-owner aggregate behind explicit writable `Mediator` facade properties and methods, with characterization coverage for cached unlocks, purchase rejection, entity/RNG identity, UI timing, checkpoint consumers, and delivery-hook order and no gameplay or public API change.
- Extracted dependency-free stateless route queries, selection, compression, and lazy planning proposals behind the `Mediator` facade while preserving public methods, RNG/BFS and mapping lookup order, live passenger-list mutation timing, travel-plan identity and ownership, and passenger-delivery behavior.

## 2026-07-14

- Extracted the 12 path-lifecycle transitions into a dependency-light stateless component behind unchanged real `Mediator` methods, retaining canonical facade-owned topology state, late public-hook and factory resolution, mutation/identity/partial-failure timing, focused direct plus facade characterization, and a reproducible archived-baseline differential while reducing `src/mediator.py` below 1,000 lines.
- Strengthened the repository delivery policy so each minimal coherent unit is reviewed, validated, scoped, and committed promptly while failing, in-flight, and partial checkpoint commits remain prohibited.

## 2026-07-19

- Extracted 16 passenger-flow and simulation-transition algorithms into a dependency-light stateless component behind unchanged `Mediator` methods, preserving late collaborator resolution, three fresh graph phases, live iterator and partial-failure timing, and deterministic gameplay while reducing `src/mediator.py` to 735 lines.
- Extracted 19 input, layout, compatibility-render, path-button UI, pause/speed, and structured-action algorithms into a dependency-light stateless coordinator behind unchanged `Mediator` methods, preserving canonical facade state, late dependency and public-hook resolution, subclass/evaluation-order behavior, and player-equivalent control semantics while reducing `src/mediator.py` to 605 lines.
- Replaced recursive execution's mutable sibling dependency with one descriptor-bound ignored `/.civ-engine-pin/` checkout, enforcing package/lock/CI parity plus physical package, `dist`, runtime-entry, Git commit, clean-status, and complete runtime-tree identity before execution.

## 2026-07-20

- Added a cross-platform, descriptor-authorized civ-engine setup and verification boundary with ownership-checked lock/transaction cleanup and exact manual crash recovery, immutable provenance captures, complete non-generated `HEAD` byte authentication, exclusive-copy no-clobber publication plus final-path reauthentication, a strict root install graph and missing-only exact root link without root npm extraction, Node-distribution npm plus pin-local TypeScript execution without shell/PATH lookup, an explicit trusted bootstrap with shared post-start taint detection, parser-shared canary selection, a fixed post-start zero-argument full-suite test guard, child-lifetime cooperative leases with pre/post-verification ownership checks, fail-closed shadow/tamper handling, and full-history Ubuntu/Windows CI dogfooding.
- Corrected production defects exposed after exact-link setup passed on both hosted platforms: controlled child and Git-planner paths now follow selected-platform rules, while publication verification observes each source directory, entry, byte sequence, and link target before its destination counterpart so concurrent destination-first snapshots cannot evade the fail-closed comparison.
- Completed the local GM-04c finalization proof without production changes: repeated setup remained stable, the canonical guarded Node suite passed 241 of 245 registered tests with four expected platform skips, a clean recursive run passed public fresh-process verification with no fix candidate, and an isolated fixture proved the categorical dependency guard exits before the engine body when resolution targets the independently fingerprinted 2.4.1 sibling.
- Added atomic programmatic line replacement with exact selector and station validation, off-live geometry, identity- and pose-preserving semantic metro rebinding, immediate scoped waiting-rider replanning, safe-alight onboard markers, and full topology/passenger/RNG rollback on any effect-phase failure.
- Added selected-line hold-drag-release redraw with an immutable off-live preview, deterministic selected/invalid feedback, preserved click/purchase/speed/create behavior, exact manual/structured canonical equality, and topology-aware interpolation that prevents a zero-step post-edit metro jump.
- Added collision-resolved selected-line endpoint and insertion handles with two-phase mouse activation, atomic extension/one-step shortening/interior and loop-closing insertion, cache-free lane-consistent feedback, fast/fidelity pixel reachability, outside-viewport and game-over cleanup, and unchanged structured/checkpoint/action identities.
- Added a conserved locomotive inventory as a read-only total-minus-assigned resource, exposed exact labeled structured counts and a third player HUD line, preserved automatic line assignment and every legacy lifecycle/failure seam, and proved genuine checkpoint v1/v2 reconstruction plus fast/fidelity low-level `4 -> 3 -> 4` pixel visibility without a schema or action change.
- Replaced automatic line allocation with explicit visible and structured locomotive assignment plus empty-train queued return, supporting multiple locomotives per line, delayed inventory refund at the next real station, no-boarding return trips, transactional ownership rollback, player-equivalent fast/fidelity controls, checkpoint v3 queue state, and replay-safe recursive/agent v4 contracts while preserving frozen v1/v2/v3 behavior through one shared legacy transition.

## 2026-07-21

- Added attached-only carriage composition with two derived fungible units, deterministic rollback-safe attach/detach and whole-consist lifecycle accounting, executable-action station timing, route-following consist rendering and player controls, structured composition, UUID-free checkpoint v4, and replay-safe recursive/agent v5 while preserving frozen legacy behavior and the GM-06d rider/removal deferrals.
- Bumped the deprecated Node 20 GitHub Actions in `.github/workflows/test.yml` (`actions/checkout` v4→v7, `actions/setup-python` v5→v7, `actions/setup-node` v4→v7) onto the Node 24 runtime, verifying against each action's v7 `action.yml` that every used input still exists and that the only removed inputs are unused ones; adversarially reviewed (Codex plus an independent harness reviewer; the Claude CLI reviewer was unreachable on an expired OAuth session) with the change gated on both hosted CI jobs passing.
- Hardened the same workflow by pinning all three v7 actions to immutable full commit SHAs (`actions/checkout` v7.0.1, `actions/setup-python` and `actions/setup-node` v7.0.0 — each also the current latest release) with `# vX.Y.Z` comments; the SHAs were independently re-resolved from the official `actions/*` repositories by an adversarial reviewer (overall PASS) and gated on green CI.
- Hardened the deferred fleet edge cases under owner-approved soft-cap alighting: occupied locomotives can be queued for return with empty-preference selection and a guaranteed oracle-quiet one-batch rider drain, queued returns gained a live-only `cancel_unassignment` action rejected across persisted v1-v5, line removal became a rider-conserving snapshot/rollback transaction that credits destination-shape deliveries and restores the complete progression/RNG footprint on failure, and a narrow unconditional reconcile seam repairs only provably-safe residual fleet shapes — with queue/cancel service-cache reconciliation closing a paused-window checkpoint crash found by adversarial review.

## 2026-07-22

- Fixed the recursive oracle's critical `invalid-reference` false positive on checkpoints taken while a metro traverses a `PaddingSegment`: the metroMotion current-segment station checks now accept the legitimately absent `None` endpoints exactly like the topology-segment checks, the GM-06d paused-queue pin asserts its scenario is finding-free end-to-end, a direct mid-padding reference-integrity regression covers the oracle, and the frozen v1-v5 fixture outcomes remain byte-exact.
- Extracted the human application shell (GM-07a): new `src/app_controller.py` screen-state machine (title, playing, pause menu, game over) with one factory-driven reconstruction path, new deterministic `src/ui/menu_screens.py` chrome, a rewritten `src/main.py` loop that auto-starts playing under `max_frames` and at the title otherwise, and a `Mediator` pause-reason model (`user`/`menu` behind the exact `is_paused` bool facade) so Escape opens a modal pause menu that Space can never dismiss; checkpoints, observations, and all frozen artifacts stay byte-identical.
- Fixed the GM-07a implementation-review findings: pause-menu controls now arm on press so a control fires only on a DOWN+UP pair inside its own rect (a drag released over Restart after a mid-drag Escape no longer discards the run), the `run_game` frame-composition branches are pinned by a mutation-checked loop suite driving the real controller (TITLE `advance(0)`, same-frame restart rebind to the new triple with `advance(0)`, gameplay-then-menu compositing under the held menu reason), and `GAME_RULES.md` no longer claims keyboard speed keys clear the user pause.
- Hardened both segment reference checks in the recursive oracle kind-aware: `None` endpoint stations are now accepted only for `PaddingSegment` records while `PathSegment` records require valid in-range station indices at the topology and metroMotion sites, restoring detection of a dangling traversed endpoint that the 83b62e5 blanket allowance made silent, with red-first regressions for both kinds at both sites and frozen v1-v5 fixture outcomes verified byte-exact.
- Implemented versioned save/load (GM-07b): strict fail-closed save schema v1 (`src/save_schema.py` + `src/save_schema_records.py` — exact keys, exact scalar types, ID grammar/global uniqueness, reference resolution, validate-equal derived fields, pinned ASCII canonical bytes), a pure attribute-only serializer with a save-local atomic writer (`src/save_game.py`), and the repo's first JSON-to-`Mediator` loader (`src/save_load.py` — RNG overwrite, post-construction ID assignment, segments-before-metros rebind, direct-append over-capacity queues, synchronous button restoration, RNG-neutral service reconcile with persisted-timer re-apply); loaded games are checkpoint-identical (RNG included), honor pre-save entity IDs in structured actions, and replay byte-identical trajectories in-process and when fresh processes reload the same save file; `saves/` is config-owned and git-ignored, `scripts/fixtures/save-v1.json` is frozen with length/SHA pins; the two originally red byte-identity assertions were re-aimed at strictly stronger honest oracles (cross-process load→re-save idempotence plus checkpoint-equal regeneration) because per-process `shortuuid` minting makes fresh-build byte identity impossible by design.
- Fixed the GM-07b adversarial-review findings (two independent NOT CLEAN lanes, one converging blocker): schema v1 now persists each metro's bound station-service action verbatim (nullable `serviceAction` record with fail-closed timing/speed invariants) and the loader restores it without re-deriving, closing the reachable save-cannot-load and silent-divergence windows (codex seed-127, harness seeds 4501/9001 — regression-locked in lockstep vs never-saved controls under a UUID-normalized save-document oracle, since `canonical_checkpoint` itself rejects those boundaries — a known pre-existing defect left for its own follow-up); RNG states are numeric-domain-pinned with residual setter failures normalized to `ValueError`, path/metro station references validate against the active prefix (plus the saver's non-prefix live-list rejection), duplicate JSON keys are rejected at every object level, consecutive duplicate path stations and out-of-range `pathOrder` are rejected, the atomic writer and the post-construction loader failure gained real fault-injection regressions, the cross-process proof now replays released active ticks under distinct hash seeds against an in-process control, the isolation scan covers all four save modules plus `recursive_checkpoint.py`, and the v1 fixture was refrozen with the new field.
- Retired the layout/render case from the frozen GM-03f input-coordinator differential (`scripts/verify_input_coordinator_differential.py`), which had been unable to run since GM-06c added the pre-mutation `validate_resource_control_layout` reserved-band check that its 200×100 and 10×20 `prepare_layout` probes trip but the archived GM-03e baseline (`7ff9d9c`) predates; kept the still-comparable input-dispatch, progression-purchase, and speed-action cases, deleted `scripts/input_coordinator_differential_layout.py`, dropped `rendering.game_renderer` from the loaded-origin assertion, bumped the scenario to `v2`, and regenerated the committed golden/summary to 3 cases / 11 records / 57 events (`a23179b6…`, baseline == candidate == expected), reconciling the ARCHITECTURE.md verifier description and its GM-03e-baseline / GM-03f-extraction naming.
- Fixed the GM-07b follow-up: `canonical_checkpoint` no longer raises (`checkpoint runtime carriage graph is malformed`, plus the sibling `checkpoint Metro service cache is stale`) on legitimately reachable multi-locomotive boundaries where a later metro consumes an earlier metro's boarding rider inside one tick, leaving that metro's bound `_station_service_action` no longer equal to the re-derivable oracle at the tick boundary — the exact real state GM-07b save/load already persists verbatim. The v4 checkpoint verifier now validates a bound service cache structurally (known kind, boarding-invariant timers, and a live passenger via the new `fleet_validation.service_action_passenger_is_live`) instead of demanding the oracle match, threaded through a new opt-in `allow_stale_bound` on `carriage_state_is_canonical`/`service_cache_is_canonical` that defaults strict so the carriage-lifecycle guards, fleet-management, and path-replacement callers are unchanged; `recursive_checkpoint_carriages._validate_service_cache` mirrors the same structural contract and also stops rejecting the stale-reset null cache. Corruption is still rejected (unknown kind, dangling passenger, off-invariant timers, bound-while-off-station, null-with-nonzero-timers), no simulation behavior or serialized checkpoint bytes change (the action tuple is never serialized), and the frozen v1-v5 fixture outcomes stay byte-exact — verified with a red-first two-locomotive (seed 4501) + stale-reset regression, an end-to-end `run_scenario` proof (finding-free), the full `py313` suite, and an independent adversarial review (35,200 fuzzed states, no refutations).
- Implemented atomic autosave, Continue, and menu integration (GM-07c, D-027): the human shell autosaves to a single `saves/autosave.json` slot on pause-menu entry and on Exit to Title (before releasing the menu hold), keeps it on a mid-run window close, deletes it at the `PLAYING`->`GAME_OVER` promotion and the game-over exits, and offers a title-screen Continue that resumes checkpoint-identically while releasing the menu pause and honoring a held user pause; `AppController` gained optional inert `build_from`/`autosave` seams (omitting both reproduces the GM-07a baseline exactly), `main.run_game` owns the patchable module-level `AUTOSAVE_PATH` plus the state-gated window-close save/delete, and `ui/menu_screens.py` gained the three-button title layout, `continue_available` painting, and a byte-stable `draw_notice` banner — no schema, observation, or isolation-scan change, and no headless/agent/recursive/RL surface imports the save modules. Also fixed a latent cross-`pygame`-cycle font-cache staleness in `menu_screens._font` (now a fresh per-call bundled font) that the newly-rendering title chrome exposed under the suite's per-class `pygame.init()/quit()` fixtures.

# GM-09f2 high-score map identity — implementation diff (post-fold)

New file: `test/test_gm09f2_highscore_map.py`. Source: highscores.py (schema v2), main.py (record_highscore + promotion seam), app_controller.py (seam). Tests: gm07d_highscores/recorder_controller/run_game_loop + gm07e surgery. Docs: D-039, README, GAME_RULES, ARCHITECTURE, PROGRESS.

```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index 729d8e0..fa80e50 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -376,6 +376,7 @@ python_mini_metro/
 - GM-09d (D-036) adds the SECOND alternate map, `DELTA`, with NO new machinery — it is a pure `MapDefinition` addition proving the GM-09b/GM-09c layer generalizes. Two vertical channels (`rivers` = 2 bands) split the play area into THREE `station_size`-eroded banks (`spawn_regions` = 3 rects), with `tunnel_budget=4`; a line spanning both channels consumes two tunnels, exercising the multi-band `path_crossings` count and the finite budget more than the single-river `RIVER`. Registered so `KNOWN_MAP_IDS == ("classic", "delta", "river")`. The addition is purely additive — the region-aware spawn (`_sample_position` accepts a candidate inside any of the three regions), the terrain/crossing renderers (loop over all bands), the derived tunnel count, and the fail-closed save guard all already handle N regions/rivers, so CLASSIC and RIVER stay byte-identical (the `test_gm09a_maps` fingerprints and `save-v1.json` are unmoved). The GM-09b exact-`KNOWN_MAP_IDS` test was loosened to membership so later maps do not break it.
 - GM-09e (D-037) adds the THIRD alternate map, `LAKE`, again with NO new machinery, but exercising a generality dimension the RIVER/DELTA channels never did: a PARTIAL band. `LAKE.rivers` is a single BOUNDED rect (a central lake spanning no screen edge), so `crossings.segment_crosses_band` is tested on a rect bounded in both x and y — a line's centerline that passes through the lake counts one crossing, and a line routed AROUND it counts none. `spawn_regions` is a FRAME of four overlapping strips (top/bottom full-width, left/right full-height, each eroded from the lake by `station_size`) whose union is the whole screen minus the lake; the region-accept spawn (`_point_in_rects`, any-region) needs no change. Because the lake is bounded, a line can OFTEN be routed around it (a line bends only at stations, so a dry detour needs an intermediate station beside the lake) instead of tunnelling through — so `tunnel_budget=3` mostly caps shortcuts, but still limits TOTAL crossings and a station whose only routes cross the lake is gated until a tunnel is freed, as on the channels (a re-review corrected an over-claim that the lake "never gates connectivity"). GM-09e also promoted `crossings.segment_crosses_band` to STRICT-interior semantics: a segment collinear with a band EDGE now counts zero — reachable on LAKE (integer vertical edges with no x-erosion of the top/bottom banks), which supersedes GM-09c's deferral; RIVER/DELTA never place a centerline on an edge, so their counts are unmoved. `KNOWN_MAP_IDS == ("classic", "delta", "lake", "river")`; CLASSIC/RIVER/DELTA stay byte-identical.
 - GM-09f (D-038) begins the map/save integration (SPLIT into save-schema / high-score / menu) with the SAVE-SCHEMA v2 map field. `save_schema` gains `SAVE_SCHEMA_VERSION_V2 = 2` (`SUPPORTED = {1, 2}`, current = 2) with two additive top-level keys `mapId`/`mapDefinitionVersion`; `validate_save` is TWO-PHASE (read + support-check `schemaVersion` with a named error BEFORE choosing the version-aware exact-key set `_TOP_LEVEL_KEYS_V1`/`_V2`, so a v1-doc-with-map-keys and a v2-doc-without both fail closed), and the v2 identity is scalar-validated (`_validate_map_identity`). `save_game.serialize_game` replaces `_require_classic_map` with a fail-closed pair: STRUCTURAL `map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`, since a v2 save records only the identity and rebuilds terrain from the registry on load) and `save_load._require_legal_map_state` (every station on the map's `spawn_regions`; `consumed_tunnels <= num_tunnels`) — the latter shared by serialize and post-load so a forged illegal state (a Classic state relabeled `river@1`) is refused both ways. `save_load.deserialize_game` reads the map identity for v2 / synthesizes `classic@1` for v1, resolves via `resolve_map` (fail-closed on unknown id / unsupported version), and threads `map_definition` into the `Mediator`; tunnel counts stay derived. The byte-frozen `scripts/fixtures/save-v1.json` is unchanged and still loads as Classic; the deterministic v1→v2 header-only upgrade is pinned by a new frozen `scripts/fixtures/save-v2-classic.json` (15485 bytes) that the idempotence + cross-process determinism tests target. `stateContract`/`rulesVersion` unchanged; the RL manifest and recursive checkpoint are separate schemas. The high-score `mapDefinitionVersion` and the in-game map menu follow as the next two sub-units (menu last, so it cannot feed an alternate map to the still-classic-hardcoded score recorder).
+- GM-09f2 (D-039) is the second GM-09f sub-unit: the high-score leaderboard records the MAP identity. Both game-over surfaces now hand the recorder the LIVE mediator (the controller seam passes `self.mediator`, and `main.run_game`'s promotion closure drops its old `SimpleNamespace(deliveries=...)` wrapper), so `main.record_highscore` reads `mediator.map_definition.{map_id, map_definition_version}` (direct, fail-SAFE: a missing map records nothing rather than mislabelling — no `or classic`) instead of hardcoding `classic`. `highscores` bumps to schema **v2** keyed by the full `(map, mapDefinitionVersion, rulesVersion)` identity via one shared `_identity` helper (sort + cap + rank), with the `map` grammar tightened to the save's mapId. A legacy v1 board is NOT migrated — it starts empty — because its classic labels are not provably accurate. This lands BEFORE the in-game menu (GM-09f3) so the recorder is already map-aware when non-Classic maps become selectable; `highscores` stays gameplay-free (no `maps` import) and in the persistence isolation set.
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
@@ -385,7 +386,7 @@ python_mini_metro/
 - `scripts/verify_passenger_flow_differential.py` and its dependency-light support module apply the same non-mutating archived-baseline discipline to seeded spawning, pause/speed/waiting behavior, three fresh graph phases, metro delivery-transfer-boarding order, lazy arrival/route/fallback proposal effects, live-list mutation, and callable finalization timing. Exact-path `.gitattributes` rules keep the canonical artifact and summary LF-stable across Windows `core.autocrlf=true` checkouts so byte-level `--expected` replay remains portable.
 - `scripts/verify_input_coordinator_differential.py` and its three split case/support modules guard the GM-03f input-coordinator extraction against its archived pre-extraction GM-03e baseline (`7ff9d9c`) in isolated bytecode-disabled children, assert source origins and pre/post runtime/verifier hashes, freeze nonzero case/record/event cardinalities, and cover hit-test, mouse/keyboard, purchase, pause/speed, and structured-action order. The layout/render case was retired at scenario version `v2` because GM-06c's pre-mutation `validate_resource_control_layout` reserved-band check, which the frozen baseline predates, makes that case's small-surface `prepare_layout` probes no longer comparable across the baseline boundary. Exact-path LF attributes plus external-output `core.autocrlf=true` replay make the canonical artifact byte-portable.
 - `src/game_clock.py` owns the bounded deterministic `17, 17, 16` millisecond cadence, while `src/game_session.py` provides the shared player-event and fixed-update driver. The pygame window handles input before updates and uses one `Clock.tick(60)` pacing authority.
-- `src/app_controller.py` owns the human entry path's explicit screen-state machine (`TITLE`, `PLAYING`, `PAUSE_MENU`, `GAME_OVER`, the GM-08a `SETTINGS`, and the GM-08c `TUTORIAL`): it consumes already-converted virtual-coordinate events, decides which reach `GameSession.dispatch`, absorbs the historical loop-inline game-over branch, and owns the one shared reconstruction path through the construction callable `main.run_game` supplies, so the controller never constructs the triple or touches the display and headless/programmatic entries (`env.py`, `rl/player_env.py`, `recursive_playtest.py`, `agent_play.py`) never meet it. `src/ui/menu_screens.py` provides the deterministic title/pause-menu layouts (exposed hit-test rects — the title and pause stacks each append a `settings` entry after their prior controls, so those earlier rects stay byte-identical) and byte-stable draw functions the loop paints above or instead of the gameplay frame; `draw_title_screen(surface, continue_available=...)` paints Continue only when available, `draw_notice` renders the load-failure banner, and `draw_settings_menu(surface, settings)` paints the SETTINGS chrome. The GM-08a `SETTINGS` screen is reachable from both the title and pause menus (from pause it keeps the `menu` hold and Back returns to the opening screen) and edits `AppController.current_settings` through the optional inert `settings` seam. `Mediator` keeps pause ownership behind the retained `is_paused` bool facade over an internal per-instance lazily created pause-reason store (`user`, `menu`): the property setter, `set_paused`, structured `pause`/`resume`, speed actions, and the Space toggle touch only the `user` reason, while `hold_pause_reason`/`release_pause_reason` are the controller-only `menu` entry points, so a menu hold can never be cleared by gameplay input and reasons stay process-local runtime state outside checkpoints and observations. GM-07c wires GM-07b persistence into this shell only: `AppController` takes optional inert `build_from`/`autosave` seams and, per D-027, autosaves on pause-menu entry and Exit to Title (before releasing the menu hold), deletes the autosave at the `PLAYING`->`GAME_OVER` promotion and the game-over exits, and resumes a proven-loadable save via title Continue while surfacing a `notice` on load failure; `main.run_game` supplies that seam bound to the single `saves/autosave.json` slot behind a patchable module-level `AUTOSAVE_PATH` and applies the state-gated window-close save/delete, so autosave and Continue live only in `main` plus `app_controller` and no headless, agent, recursive, or RL surface imports the save modules. GM-07d adds a second optional inert seam beside it (D-028): `AppController` takes a `highscores` recorder that it invokes exactly once at the `PLAYING`->`GAME_OVER` promotion — reading `mediator.deliveries` only when the seam is present, so a seam-less controller reads nothing — and stores the result in public `last_highscore_result`; `main.run_game` binds the seam and the patchable `HIGHSCORES_PATH`/`record_highscore` to `src/highscores.py`, applies the same window-close game-over record (mutually exclusive with the promotion), and draws the best indicator with `menu_screens.draw_best_indicator` after the renderer's game-over frame so the near-ceiling `game_renderer` stays untouched. GM-07e makes that promotion frame-deterministic: the block is a public idempotent `AppController.reconcile_game_over()` (a no-op unless `PLAYING` and game over) that `handle_event` calls at its top and `main.run_game` calls once per frame after `session.advance` (re-reading the render state), so a tick-driven game over records, deletes the autosave, and shows the indicator the frame it ends independent of any incidental event; the state-gated window-close record stays mutually exclusive, now firing only for a game over still un-promoted at the QUIT. GM-08b hangs a pure gameplay-audio consumer off that same post-`reconcile_game_over` hook (`src/audio.py`, D-030): it reads the post-reconcile counters and plays one SFX tone per delta, entirely in `main.run_game` with no `AppController`/`Mediator` change, and defaults to an inert backend so only the interactive entry point ever opens a device. GM-08c adds the `TUTORIAL` screen and an optional inert `build_tutorial` seam beside the others: a menu-launched coached playthrough of a seeded, game-over-suppressed game whose per-frame `advance_tutorial` hook (beside the audio/reconcile hooks) drives the `src/tutorial.py` step machine, with no autosave/highscore and Escape skipping to the title (see the `tutorial.py` entry below).
+- `src/app_controller.py` owns the human entry path's explicit screen-state machine (`TITLE`, `PLAYING`, `PAUSE_MENU`, `GAME_OVER`, the GM-08a `SETTINGS`, and the GM-08c `TUTORIAL`): it consumes already-converted virtual-coordinate events, decides which reach `GameSession.dispatch`, absorbs the historical loop-inline game-over branch, and owns the one shared reconstruction path through the construction callable `main.run_game` supplies, so the controller never constructs the triple or touches the display and headless/programmatic entries (`env.py`, `rl/player_env.py`, `recursive_playtest.py`, `agent_play.py`) never meet it. `src/ui/menu_screens.py` provides the deterministic title/pause-menu layouts (exposed hit-test rects — the title and pause stacks each append a `settings` entry after their prior controls, so those earlier rects stay byte-identical) and byte-stable draw functions the loop paints above or instead of the gameplay frame; `draw_title_screen(surface, continue_available=...)` paints Continue only when available, `draw_notice` renders the load-failure banner, and `draw_settings_menu(surface, settings)` paints the SETTINGS chrome. The GM-08a `SETTINGS` screen is reachable from both the title and pause menus (from pause it keeps the `menu` hold and Back returns to the opening screen) and edits `AppController.current_settings` through the optional inert `settings` seam. `Mediator` keeps pause ownership behind the retained `is_paused` bool facade over an internal per-instance lazily created pause-reason store (`user`, `menu`): the property setter, `set_paused`, structured `pause`/`resume`, speed actions, and the Space toggle touch only the `user` reason, while `hold_pause_reason`/`release_pause_reason` are the controller-only `menu` entry points, so a menu hold can never be cleared by gameplay input and reasons stay process-local runtime state outside checkpoints and observations. GM-07c wires GM-07b persistence into this shell only: `AppController` takes optional inert `build_from`/`autosave` seams and, per D-027, autosaves on pause-menu entry and Exit to Title (before releasing the menu hold), deletes the autosave at the `PLAYING`->`GAME_OVER` promotion and the game-over exits, and resumes a proven-loadable save via title Continue while surfacing a `notice` on load failure; `main.run_game` supplies that seam bound to the single `saves/autosave.json` slot behind a patchable module-level `AUTOSAVE_PATH` and applies the state-gated window-close save/delete, so autosave and Continue live only in `main` plus `app_controller` and no headless, agent, recursive, or RL surface imports the save modules. GM-07d adds a second optional inert seam beside it (D-028): `AppController` takes a `highscores` recorder that it invokes exactly once at the `PLAYING`->`GAME_OVER` promotion — handing the seam the LIVE mediator only when present (GM-09f2/D-039: the recorder reads BOTH the deliveries objective and the map identity off it, so the controller itself touches no mediator attribute and a seam-less controller reads nothing) — and stores the result in public `last_highscore_result`; `main.run_game` binds the seam and the patchable `HIGHSCORES_PATH`/`record_highscore` to `src/highscores.py`, applies the same window-close game-over record (mutually exclusive with the promotion), and draws the best indicator with `menu_screens.draw_best_indicator` after the renderer's game-over frame so the near-ceiling `game_renderer` stays untouched. GM-07e makes that promotion frame-deterministic: the block is a public idempotent `AppController.reconcile_game_over()` (a no-op unless `PLAYING` and game over) that `handle_event` calls at its top and `main.run_game` calls once per frame after `session.advance` (re-reading the render state), so a tick-driven game over records, deletes the autosave, and shows the indicator the frame it ends independent of any incidental event; the state-gated window-close record stays mutually exclusive, now firing only for a game over still un-promoted at the QUIT. GM-08b hangs a pure gameplay-audio consumer off that same post-`reconcile_game_over` hook (`src/audio.py`, D-030): it reads the post-reconcile counters and plays one SFX tone per delta, entirely in `main.run_game` with no `AppController`/`Mediator` change, and defaults to an inert backend so only the interactive entry point ever opens a device. GM-08c adds the `TUTORIAL` screen and an optional inert `build_tutorial` seam beside the others: a menu-launched coached playthrough of a seeded, game-over-suppressed game whose per-frame `advance_tutorial` hook (beside the audio/reconcile hooks) drives the `src/tutorial.py` step machine, with no autosave/highscore and Escape skipping to the title (see the `tutorial.py` entry below).
 - `src/entity/path.py` owns logical centerline segments used by metro movement. `src/rendering/layout.py` derives immutable, symmetric visual lanes without rebuilding or re-identifying those simulation segments.
 - `src/rendering/network_renderer.py` owns separate bounded antialiased caches for the live network and one immutable selected-line preview, including arbitrary-slot temporary insertion, while sharing centered-lane geometry and the halo/color rasterizer. The cache-free `src/rendering/path_handle_renderer.py` draws primitive leader, marker, hit-envelope, and non-erasing removal feedback; `src/rendering/game_renderer.py` places leaders below entities, markers above stations/metros and below controls, projects endpoint-removal feedback onto the selected production lane, slices passengers locomotive-first across ordered bodies, outlines an entire queued consist, and renders available locomotives/carriages as the third/fourth HUD lines. The config-owned `(0, 0, 840, 250)` HUD exclusion keeps every route-handle descriptor and registered-profile action round trip outside all four lines. `src/rendering/consist_layout.py` samples route arclength with loop wrapping and terminal extrapolation from coherent endpoint poses. `src/rendering/interpolation.py` tracks exact live segment/station identity and rebase-safe previous/current snapshots, while `src/rendering/turnaround.py` supplies a continuous body-clearance-constrained terminal reversal for folded consists; ambiguous stale topology falls back to the live pose. Fonts and surfaces are renderer-owned and lazy so state-only and headless sessions do not require a display.
 - `Mediator.prepare_layout(width, height)` prepares all player hitboxes before input. Rendering consumes those prepared rectangles; drawing primitives never establish or move hitboxes.
@@ -402,7 +403,7 @@ python_mini_metro/
 - `src/rendering/flexible_draw.py` (GM-08a) holds the kwarg-filtering `_call_flexibly` dispatch extracted from `game_renderer` so the renderer can pass optional draw kwargs (`resources`, `reduced_motion`, ...) uniformly while each entity draw receives only what its signature declares; `reduced_motion` (D-029) rides that boundary to the `station`/`passenger`/`path_button` blink predicates (held steady) and the station snap blip (suppressed), defaulting False so every non-reduced path stays byte-identical, and the extraction keeps `game_renderer` under 500 lines.
 - `src/audio.py` (GM-08b, D-030) owns procedural gameplay sound effects, importing only `pygame`/`numpy` and holding all its own tone constants (never `config`). `_generate_tone` builds a deterministic MONO int16 sine (with a click-free envelope) against a parameterized sample rate; `ProceduralAudio` reads the mixer's ACTUAL negotiated rate/channels from `pygame.mixer.get_init()`, builds one channel-shaped `Sound` per event, and plays best-effort at gain `(master/100)*(sfx/100)`; `NullAudio` is the inert backend; `create_audio` initializes the mixer and builds every sound in one `try/except`, degrading to `NullAudio` on any failure so audio-init never blocks play. `snapshot_of`/`diff_and_play` are a pure, duck-typed, tolerant per-frame counter differ (a host missing counters reads 0/False) that plays one tone per newly-occurred `deliveries`/`unlocked_num_paths`/`unlocked_num_stations`/`is_game_over` (False→True)/snap-sum delta. Audio is a pure `main.run_game` loop-level consumer at the post-`reconcile_game_over` hook — NOT an `AppController` seam and no `Mediator`/`GameSession`/`rendering` change — that owns its OWN session reference and re-baselines the snapshot on a session change so Continue/New Game/Restart never replay a stored delta as a spurious burst. `run_game`'s `audio_backend` defaults to inert `NullAudio`; the real mixer is constructed ONLY at the `__main__` entry point, so no test or embedder (even one driving `run_game` unbounded) opens a device. `audio` lives outside `rendering/` (transitively imported by `rl/player_env.py`) and joins both persistence-isolation scans, so only `main` imports it.
 - `src/tutorial.py` (GM-08c, D-031) owns the coached-tutorial step machine — a pure, duck-typed, stdlib-only observer (the GM-08b snapshot pattern) that reads mediator attributes only. `TUTORIAL_STEPS` orders seven lessons (draw, reroute, train, deliver, overload, pause, speed); `tutorial_snapshot` tolerantly captures the signals; and `advance(progress, mediator, elapsed_ms, paused)` completes a `state` step on its predicate or a `dwell` step (overload) after `OVERLOAD_DWELL_MS` of unpaused play, re-baselining each transition. Reroute precedes the train (a metro mid-service persistently blocks `replace_path` under the strict path-lifecycle default), the reroute predicate accepts any route-topology change (a delete-and-redraw mints a fresh id), and train/pause/speed are current-state checks so they can never soft-lock at the metro cap or an already-used control. `AppController` gains an `AppScreen.TUTORIAL` state, an optional inert `build_tutorial` seam, `_start_tutorial`/`_handle_tutorial`/`advance_tutorial`/`tutorial_overlay` (Escape skips to the title with the letterbox-cancel; a cold start directly in TUTORIAL also builds the tutorial), and never autosaves or records. `main.run_game` supplies the seam over a seeded `Mediator(seed=42)` whose `overdue_passenger_threshold` is raised on the instance so the sim never game-overs or freezes (a per-instance write, not a `Mediator`/`config` change), calls `advance_tutorial` once per frame beside `reconcile_game_over`, and paints `menu_screens.draw_tutorial_overlay` over the real game frame — the controller exposes the overlay strings so `main` never imports `tutorial`. `tutorial` joins the isolation scan and is imported only by `app_controller`, so no headless/agent/recursive/RL surface constructs it; no `Mediator`/`GameSession`/`rendering`/schema/observation/checkpoint change.
-- `src/highscores.py` (GM-07d, D-028) owns the persistent high-score leaderboard, reusing `save_schema.canonical_save_bytes` and the scalar validators plus its own copy of the save-local atomic writer (`main` owns the `SAVE_RULES_VERSION` identity) — so it joins the save-module isolation set but imports no gameplay. The document is a strict versioned `{schemaVersion, stateContract, entries}` shape whose entries carry a `map`/`rulesVersion`/`deliveries` triple; `validate_highscores` checks exact keys before field access and rejects forward versions, bad types, and non-ASCII string content, `record_score` requires an explicit map/rulesVersion and validates its inputs, then returns a NEW board (pure) with the score inserted, all entries stored in the canonical map-asc/rulesVersion-asc/deliveries-desc order with stable tie-breaking and the recorded key capped at ten (other keys are never dropped), and a `RecordResult` carrying the new entry's rank and best flag. Unlike `load_game`, `load_highscores` is START-EMPTY tolerant: any failure — missing, non-ASCII, malformed, duplicate-key, forward-version, or pathologically nested (RecursionError) — yields the empty board and never raises, because a cosmetic leaderboard must never block play; `save_highscores` validates the board before writing and still RAISES on failure, and the best-effort swallow lives at `main`'s single patchable `record_highscore` recorder that both game-over surfaces funnel through.
+- `src/highscores.py` (GM-07d, D-028) owns the persistent high-score leaderboard, reusing `save_schema.canonical_save_bytes` and the scalar validators plus its own copy of the save-local atomic writer (`main` owns the `SAVE_RULES_VERSION` identity) — so it joins the save-module isolation set but imports no gameplay. The document is a strict versioned `{schemaVersion, stateContract, entries}` shape whose entries carry a full map-identity key — GM-09f2 (D-039) makes it schema **v2**, keying each entry by `map`/`mapDefinitionVersion`/`rulesVersion` with `deliveries` (so a future `classic@2` terrain revision ranks and caps separately from `classic@1`, mirroring the save's `(mapId, mapDefinitionVersion)` identity); the `stateContract` stays `mini-metro-highscores-v1` across the additive version. `validate_highscores` checks exact keys before field access and rejects forward versions, bad types, non-ASCII content, and a malformed `map` id (nonempty ASCII, no whitespace — the save's mapId grammar). `record_score` requires an explicit map/mapDefinitionVersion/rulesVersion and validates its inputs (`_positive_int` version, `_map_id` grammar), then returns a NEW board (pure) with the score inserted, all entries in the canonical identity-asc/deliveries-desc order (one shared `_identity` helper keys the sort, the per-key cap, AND the rank count) with stable tie-breaking and the recorded identity capped at ten (other keys never dropped), and a `RecordResult` carrying the new entry's rank and best flag. Unlike `load_game`, `load_highscores` is START-EMPTY tolerant: any failure — missing, non-ASCII, malformed, duplicate-key, forward-version, a **legacy v1 board** (NOT migrated: its classic labels are not provably accurate, since the recorder was classic-hardcoded while non-Classic saves became loadable, so it starts empty rather than synthesizing authoritative `classic@1`), or pathologically nested (RecursionError) — yields the empty board and never raises, because a cosmetic leaderboard must never block play; `save_highscores` validates the board before writing and still RAISES on failure, and the best-effort swallow lives at `main`'s single patchable `record_highscore` recorder that both game-over surfaces funnel through.

 - `src/recursive_checkpoint.py` converts observations and latent simulation state into UUID-free canonical JSON; `src/recursive_checkpoint_schema.py` owns version validation/normalization and `src/recursive_checkpoint_carriages.py` owns strict composition/topology correspondence so every module remains below 500 lines. Checkpoint v4 records exact locomotive/carriage inventory, queue booleans, derived capacities, ordered attachment references, and the exhaustive global-plus-path motion/owner bijection without entity UUIDs. Generation validates the live ownership graph, exact entity types, service cache, capacity equations, and caller observation before serialization. Genuine v1-v3 generation rejects any forward carriage surface; normalization deep-copies and synthesizes only historically valid missing state while preserving frozen bytes/projections. Checkpoints also cover reward identity, topology, passengers/plans, progression/unlocks, spawning, dwell/service state, and Python/NumPy RNG state.
 - `src/recursive_oracles.py` checks reference integrity and non-finite values; `src/recursive_playtest.py` combines those checks with action-result, selected-contract reward, rejected-action, pause, terminal-state, topology, and transcript-cardinality oracles. Findings are born unverified and carry a stable class in `data.class`.
diff --git a/GAME_RULES.md b/GAME_RULES.md
index bcb7a79..2cdd1b9 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -130,7 +130,7 @@ This document summarizes the game rules currently implemented in code.
   - Simulation time and gameplay updates stop.
   - `MiniMetroEnv.step(...)` calls become stable no-ops until reset; `PlayerPixelEnv.step(...)` rejects further actions until its required reset.
   - The game-over overlay presents lifetime passengers delivered as the primary result and remaining line credits as a secondary value.
-  - The run's lifetime deliveries are recorded once to the high-score leaderboard at `saves/highscores.json` (ranked descending and capped at ten per map and rules version); if the run set a new best for its key, a compact indicator is shown on the game-over screen. A missing or corrupt leaderboard starts empty and never blocks play.
+  - The run's lifetime deliveries are recorded once to the high-score leaderboard at `saves/highscores.json`, keyed by the game's actual map identity `(map, mapDefinitionVersion, rulesVersion)` (ranked descending and capped at ten per key); a non-Classic run is recorded under its own map, and a future revision of a map's terrain (a new `mapDefinitionVersion`) ranks separately from the old. If the run set a new best for its key, a compact indicator is shown on the game-over screen. A missing, corrupt, or legacy (pre-map-identity) leaderboard starts empty and never blocks play.

 ## Controls

diff --git a/README.md b/README.md
index abaa85b..137d866 100644
--- a/README.md
+++ b/README.md
@@ -222,7 +222,7 @@ mediator = save_game.deserialize_game(document)             # reconstruct from a
 - Bytes on disk are the pinned canonical encoding (`save_schema.canonical_save_bytes`: sorted-key, ASCII, compact separators, trailing LF). Saves go through a save-local atomic writer (mkstemp, fsync, `os.replace`), so a failed save leaves an existing destination untouched and no temporary file behind. The default directory name is `config.save_dir_name` (`saves/`, git-ignored); all functions accept explicit paths.
 - Saving is permitted only at a quiescent input boundary: an active path-creation, redraw, or edit gesture raises `ValueError` (a bare pressed mouse button does not block).
 - The human application shell (`src/main.py`) drives one canonical autosave slot at `saves/autosave.json`: it writes on opening the pause menu and on Exit to Title, keeps that save on a mid-run window close, deletes it at game over, and offers Continue on the title screen. Every autosave is best-effort and never blocks play or exit; the isolation-scanned headless, agent, recursive, and RL surfaces gain no save import.
-- `src/highscores.py` owns a separate persistent high-score leaderboard at `saves/highscores.json` (a schema-v1 strict document validated before every write, using its own save-local copy of the reviewed canonical-ASCII atomic writer), recording lifetime deliveries keyed by map (`classic`) and rules version, ranked descending and capped at ten per key with each record isolated to its own key. The shell records exactly once at game over — at the `PLAYING`->`GAME_OVER` promotion and, mirroring the autosave delete, at the window-close game-over race — through an injected recorder seam funneling into the one patchable `main.record_highscore`. Unlike a save, a missing, corrupt, or forward-version leaderboard starts empty and never blocks play, and `highscores` joins the save modules in the isolation scan.
+- `src/highscores.py` owns a separate persistent high-score leaderboard at `saves/highscores.json` (a schema-v2 strict document validated before every write, using its own save-local copy of the reviewed canonical-ASCII atomic writer), recording lifetime deliveries keyed by the full map identity `(map, mapDefinitionVersion, rulesVersion)`, ranked descending and capped at ten per key with each record isolated to its own key. GM-09f2 keys the board by the game's real map: `main.record_highscore` reads the live `map_definition` (id + version) off the mediator instead of hardcoding `classic`, so a non-Classic run is recorded under its own map (`stateContract` stays `mini-metro-highscores-v1` across the additive version). The shell records exactly once at game over — at the `PLAYING`->`GAME_OVER` promotion and, mirroring the autosave delete, at the window-close game-over race — through an injected recorder seam funneling the live mediator into the one patchable `main.record_highscore`. Unlike a save, a missing, corrupt, forward-version, or legacy schema-v1 leaderboard starts empty and never blocks play (a v1 board is not migrated — its classic labels are not provably accurate — so it resets on upgrade), and `highscores` joins the save modules in the isolation scan.
 - `src/settings.py` owns typed, presentation-only settings persisted to `saves/settings.json` (a schema-v1 strict document, integer-percent volumes, validated before every write through the same save-local canonical-ASCII atomic writer). A **Settings** screen — reachable from both the title and pause menus (Back returns to whichever opened it; opening it from the pause menu keeps the game paused) — toggles fullscreen, steps the master/music/SFX volumes, and toggles reduced motion. Fullscreen applies to the live window and reduced motion holds the passenger-warning, station-unlock, and path-button blinks steady while suppressing the one-shot snap-blip rings; the master and SFX volumes scale the GM-08b audio cues. Unlike a save, a missing, corrupt, or forward-version settings file falls back to the typed defaults and never blocks play, and `settings` joins the save modules in the isolation scan, so headless, agent, and RL play never read or write it.
 - `src/audio.py` adds short, deterministic, procedurally-synthesized sound effects (no external audio files): a distinct tone plays when you complete a delivery, purchase a line, unlock a station, reach game over, or snap a line endpoint, each scaled by the master and SFX volumes. Audio is fail-safe — a missing or unavailable device degrades silently to a no-op backend and never blocks play. It is a main-only feature built solely at the interactive entry point, so headless, agent, recursive, and RL play open no audio device; `audio` joins the isolation scan and only `main` imports it.
 - A loaded game is checkpoint-identical to the saved one, both RNG streams included, and replays the identical seeded trajectory as a never-saved control, in the same process and across fresh processes replaying the same save file. Each metro's bound station-service action (with its fractional boarding timers) persists in the document and restores verbatim — including boundaries where the bound action is legitimately stale after a same-tick cross-metro effect — so post-load service resumes exactly like the never-saved game. Held pause reasons (`user`, `menu`) restore verbatim, so a game saved from the pause menu loads paused; `release_pause_reason("menu")` resumes it.
diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index f8331a2..d996813 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -239,3 +239,9 @@ Reason: with RIVER/DELTA the map layer was proven for full-screen-height channel
 Decision: GM-09f begins the map/save integration (roadmap GM-09f, SPLIT into save-schema (this) → high-score identity → menu, per the dual plan review) with the SAVE-SCHEMA v2 map field. The save schema gains `SAVE_SCHEMA_VERSION_V2 = 2` (a strict SUPERSET of v1) that adds two additive top-level keys `mapId`/`mapDefinitionVersion`, so a non-Classic game (river/delta/lake) can be saved and loaded; `SAVE_SCHEMA_VERSION` becomes 2 (new saves are v2) and `SUPPORTED_SAVE_SCHEMA_VERSIONS = {1, 2}`. `stateContract`/`rulesVersion` are STABLE across v1/v2 — only `schemaVersion` and the two map keys change. `validate_save` is TWO-PHASE: it reads + support-checks `schemaVersion` (named `ValueError`, never a `KeyError`) BEFORE choosing the version-aware exact-key set (`_TOP_LEVEL_KEYS_V1` vs `_V2`), so a v1 doc carrying map keys AND a v2 doc missing them both fail closed; the v2 map identity is scalar-validated (non-empty ASCII `mapId`, positive non-bool `mapDefinitionVersion`). `serialize_game` drops the old `_require_classic_map` guard for a fail-closed pair: (1) STRUCTURAL — `mediator.map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`), since a v2 save records only the IDENTITY and rebuilds terrain from the registry on load, so a forged/drifted `MapDefinition("classic", 1, rivers=...)` that would reload as the real terrain-free CLASSIC is rejected; and (2) STATE-LEGAL — `_require_legal_map_state` (every station on the map's `spawn_regions`, `consumed_tunnels <= num_tunnels`), applied on serialize AND after reconstruction on load, so a hand-forged v2 doc (a CLASSIC state relabeled `river@1`, whose stations sit in the water, or an over-budget state) is refused. `deserialize_game` reads `mapId`/`mapDefinitionVersion` for a v2 doc and SYNTHESIZES `classic@1` for a v1 doc (keys absent), resolves via `resolve_map` (fail-closed on unknown id / unsupported version — never a silent Classic fallback), and threads `map_definition` into the `Mediator`. Tunnel counts stay DERIVED (no persisted counter). The byte-frozen `scripts/fixtures/save-v1.json` is UNCHANGED on disk (its SHA/length pins hold) and still loads as CLASSIC; because a v1→v2 upgrade only changes the header, a v1 load RE-SAVES as exactly the new frozen `scripts/fixtures/save-v2-classic.json` (15485 bytes, SHA `60f2bc16…`) — a deterministic transform pinned by the idempotence + cross-process determinism tests, both committed LF (no `.gitattributes` eol pin, per the recursive-source-provenance guard).

 Reason: the map layer (GM-09a–e) built maps behind a fail-closed save guard that deferred persistence to "when map selection makes the field meaningful". Three maps now exist, so a save must record which one. The DUAL plan review (both lanes REVISE, direction + split confirmed) drove the two load-bearing choices: the guard must be STRUCTURAL (mere resolvability fails open into the GM-09b forged-Classic bug — verified: 2 of 20 seed-0 CLASSIC stations sit in RIVER's band), and identity alone is insufficient without STATE-legality (a valid identity + illegal state is still corrupt). Recording only `(mapId, version)` and rebuilding terrain from the import-safe registry keeps the save minimal and the tunnel budget derived; synthesizing `classic@1` for v1 keeps the frozen fixture valid, exactly as D-026 blessed. The high-score `mapDefinitionVersion` and the in-game map menu are the next two sub-units, IN THAT ORDER — the menu must land last so it can never expose an alternate map to the still-classic-hardcoded high-score recorder.
+
+## D-039
+
+Decision: GM-09f2 (second GM-09f sub-unit) makes the HIGH-SCORE leaderboard record the MAP identity, so the recorder is map-aware BEFORE the in-game menu (GM-09f3) makes non-Classic maps selectable. Both game-over surfaces are UNIFIED on the live mediator: `app_controller._record_highscore` hands the seam `self.mediator` (not `self.mediator.deliveries`), and `main.run_game`'s promotion closure drops its `SimpleNamespace(deliveries=...)` wrapper, so the frame-accurate reconcile and the window-close QUIT both call the IDENTICAL `record_highscore(mediator)`. `main.record_highscore` reads `mediator.deliveries` AND `mediator.map_definition.{map_id, map_definition_version}` — DIRECTLY (no `or classic` default): a real `Mediator` always has `map_definition` (default CLASSIC, GM-09a), and an exotic mediator lacking it records NOTHING (swallowed to None) rather than mislabelling a score. The `highscores` schema becomes v2: `HIGHSCORES_SCHEMA_VERSION = 2`, each entry keyed by the full `(map, mapDefinitionVersion, rulesVersion)` identity via ONE shared `_identity` helper used by the canonical sort, the per-key cap, AND the rank count (so no predicate keys on a subset and miscounts a score across definition versions); `record_score` gains a required `map_definition_version` (never defaulted) validated by `_positive_int`, and the entry `map` is tightened to the save's mapId grammar (`_map_id`: non-empty ASCII, no whitespace) in both `record_score` and `validate_highscores`. `stateContract` stays `mini-metro-highscores-v1` across the additive version (as the save kept `mini-metro-save-v1`). A legacy v1 board is NOT migrated: `load_highscores` (unchanged) validates as v2, so a v1 board fails and START-EMPTIES like any other unreadable format. `highscores` stays gameplay-free (no `maps` import — `record_score` takes the version as a plain int) and in the persistence isolation set.
+
+Reason: the leaderboard schema already keyed by `map` (GM-07d) but the recorder hardcoded `classic`, and `mapDefinitionVersion` was deferred here. Landing map-awareness NOW (while the human shell still only builds Classic) means GM-09f3 adds the menu with ZERO recorder change — the ordering the D-038 split mandated. The DUAL plan review (both lanes REVISE, design UPHELD) drove three load-bearing choices. (1) The whole-mediator seam is REQUIRED, not merely convenient: a minimal `(deliveries, map_id, version)` context would force the CONTROLLER to read `map_definition`, reintroducing the attribute access the GM-07d MAJOR-3 invariant forbids; passing the mediator lets the controller touch NOTHING (the recorder reads), satisfying MAJOR-3 more cleanly and making both game-over surfaces provably identical. (2) A v1 board START-EMPTIES rather than migrating to `classic@1`, because — UNLIKE the save, where GM-09a's `_require_classic_map` guard PROVED a v1 save was genuinely Classic — a v1 highscores `map="classic"` label is NOT provably accurate: GM-09f made non-Classic saves loadable (verified: `load_autosave → load_game → resolve_map → Mediator(map_definition=non-classic)`, `build_from` plays it), and the classic-hardcoded recorder would have labelled such a Continue run `classic`. Synthesizing `classic@1` would preserve that contamination and assert precision the data lacks; discarding a cosmetic, START-EMPTY-tolerant board is honest and also eliminates a migrate-before-validate normalization hazard (a forged `schemaVersion: true`/`1.0`/extra-key v1 board). (3) The leaderboard reads the map DIRECTLY with no `resolve_map` structural guard — a DELIBERATE asymmetry with the save: highscores stores identity only and reconstructs no terrain, so a syntactically-valid-but-unknown or drifted id recording under its claimed key is harmless (a save reloading wrong terrain is not). The `or DEFAULT` fail-open lesson from GM-09f is honored: defaulting to Classic on a missing map would MISATTRIBUTE the already-reachable non-Classic Continue run, so the read is direct + fail-safe. GM-09f3 (in-game map menu) is the final sub-unit.
diff --git a/src/app_controller.py b/src/app_controller.py
index 3f672fb..67dc327 100644
--- a/src/app_controller.py
+++ b/src/app_controller.py
@@ -132,15 +132,15 @@ class AppController:
             self._autosave.delete()

     def _record_highscore(self) -> None:
-        # Record the finished run's lifetime deliveries exactly once at the
-        # promotion (D-028). deliveries is read ONLY when the seam is present,
-        # so a seam-less controller never touches a mediator that lacks it
-        # (MAJOR-3). Every promotion (re)assigns the result -- to None when the
-        # seam is absent or minted nothing -- so a restart shows no stale best.
+        # Record the finished run exactly once at the promotion (D-028). The seam
+        # receives the LIVE mediator (GM-09f2) -- the recorder reads BOTH the
+        # deliveries objective and the map identity off it -- so a seam-less
+        # controller touches NO mediator attribute at all (MAJOR-3, now satisfied
+        # even more cleanly: the controller no longer reads .deliveries; the seam
+        # does). Every promotion (re)assigns the result -- to None when the seam is
+        # absent or minted nothing -- so a restart shows no stale best.
         if self._highscores is not None:
-            self.last_highscore_result = self._highscores.record(
-                self.mediator.deliveries
-            )
+            self.last_highscore_result = self._highscores.record(self.mediator)
         else:
             self.last_highscore_result = None

diff --git a/src/highscores.py b/src/highscores.py
index d0eef00..b02929b 100644
--- a/src/highscores.py
+++ b/src/highscores.py
@@ -1,13 +1,14 @@
 """GM-07d high-score leaderboard: strict versioned document, ranked insertion.

-The leaderboard persists lifetime deliveries keyed by ``(map, rulesVersion)``
-to ``saves/highscores.json`` (D-028). It reuses the GM-07b canonical-ASCII
-recipe and the save-schema scalar validators -- so it joins the persistence
-isolation set -- but it never imports gameplay. Unlike a save, loading is
-START-EMPTY tolerant: a missing, unreadable, non-ASCII, malformed,
-forward-version, or pathologically nested file yields the empty board and never
-raises, so a cosmetic leaderboard can never block play. Saving RAISES on
-failure; the best-effort swallow lives at the ``main`` recorder layer.
+The leaderboard persists lifetime deliveries keyed by the full map identity
+``(map, mapDefinitionVersion, rulesVersion)`` (schema v2, GM-09f2/D-039) to
+``saves/highscores.json`` (D-028). It reuses the GM-07b canonical-ASCII recipe
+and the save-schema scalar validators -- so it joins the persistence isolation
+set -- but it never imports gameplay. Unlike a save, loading is START-EMPTY
+tolerant: a missing, unreadable, non-ASCII, malformed, forward-version, legacy
+schema-v1 (NOT migrated), or pathologically nested file yields the empty board
+and never raises, so a cosmetic leaderboard can never block play. Saving RAISES
+on failure; the best-effort swallow lives at the ``main`` recorder layer.
 """

 from __future__ import annotations
@@ -26,16 +27,27 @@ from save_schema_records import (
     _int,
     _nonnegative_int,
     _object,
+    _positive_int,
     _string,
 )

-HIGHSCORES_SCHEMA_VERSION = 1
+# GM-09f2 (D-039): schema v2 keys each entry by the FULL map identity
+# (map, mapDefinitionVersion, rulesVersion), mirroring the save's map identity, so a
+# future terrain revision (classic@2) never ranks against classic@1. The
+# stateContract stays stable across the additive version (as the save kept
+# `mini-metro-save-v1` across schema v1->v2); the additive `mapDefinitionVersion`
+# lives in `schemaVersion`. A v1 board is treated like any other unreadable format
+# (START-EMPTY) rather than migrated, because a v1 `map="classic"` label is NOT
+# provably accurate -- the recorder was classic-hardcoded while non-Classic saves
+# became loadable (GM-09f), so a non-Classic Continue run was mislabeled `classic`;
+# synthesizing `classic@1` would preserve that contamination.
+HIGHSCORES_SCHEMA_VERSION = 2
 HIGHSCORES_STATE_CONTRACT = "mini-metro-highscores-v1"
 HIGHSCORES_PER_KEY_CAP = 10
 HIGHSCORES_MAP_CLASSIC = "classic"

 _TOP_LEVEL_KEYS = frozenset({"schemaVersion", "stateContract", "entries"})
-_ENTRY_KEYS = frozenset({"map", "rulesVersion", "deliveries"})
+_ENTRY_KEYS = frozenset({"map", "mapDefinitionVersion", "rulesVersion", "deliveries"})


 def _fail(label: str, message: str) -> None:
@@ -52,6 +64,20 @@ def _ascii_string(value: Any, label: str) -> str:
     return text


+def _map_id(value: Any, label: str) -> str:
+    # A map id is a non-empty ASCII string with no whitespace -- the exact grammar
+    # the save records (save_schema._validate_map_identity) and the RL manifest
+    # mirror, so the leaderboard key and the save identity share one shape. Unknown
+    # but well-formed ids are allowed (no registry import): highscores stores identity
+    # only and reconstructs no terrain, so a syntactically valid id is harmless.
+    text = _ascii_string(value, label)
+    if not text:
+        _fail(label, "must be a non-empty string")
+    if any(character.isspace() for character in text):
+        _fail(label, "must not contain whitespace")
+    return text
+
+
 def _empty_document() -> dict[str, Any]:
     """Return a fresh canonical empty leaderboard document."""

@@ -86,15 +112,23 @@ def validate_highscores(document: Any) -> None:
         label = f"entries[{index}]"
         entry = _object(item, label)
         _exact_keys(entry, _ENTRY_KEYS, label)
-        _ascii_string(entry["map"], f"{label}.map")
+        _map_id(entry["map"], f"{label}.map")
+        _positive_int(entry["mapDefinitionVersion"], f"{label}.mapDefinitionVersion")
         _ascii_string(entry["rulesVersion"], f"{label}.rulesVersion")
         _nonnegative_int(entry["deliveries"], f"{label}.deliveries")


-def _sort_key(entry: dict[str, Any]) -> tuple[str, str, int]:
-    # Canonical order: map ascending, rulesVersion ascending, deliveries
-    # descending; exact ties fall to the stable sort over append order.
-    return (entry["map"], entry["rulesVersion"], -entry["deliveries"])
+def _identity(entry: dict[str, Any]) -> tuple[str, int, str]:
+    # The FULL leaderboard key (GM-09f2): one helper shared by the sort, the per-key
+    # cap, AND the rank count, so no predicate can key on a subset and miscount a
+    # score across map-definition versions.
+    return (entry["map"], entry["mapDefinitionVersion"], entry["rulesVersion"])
+
+
+def _sort_key(entry: dict[str, Any]) -> tuple[str, int, str, int]:
+    # Canonical order: identity (map, mapDefinitionVersion, rulesVersion) ascending,
+    # then deliveries descending; exact ties fall to the stable sort over append order.
+    return (*_identity(entry), -entry["deliveries"])


 def record_score(
@@ -102,37 +136,46 @@ def record_score(
     *,
     deliveries: int,
     map: str,
+    map_definition_version: int,
     rules_version: str,
 ) -> RecordResult:
     """Return a NEW board with the score inserted; never mutate the input.

     All entries are stored in the pinned canonical order and the recorded
-    ``(map, rulesVersion)`` group is truncated to ``HIGHSCORES_PER_KEY_CAP``.
-    Entries under other keys are never dropped -- for the canonical boards the
-    recorder itself produces they are returned unchanged -- so a record is
-    isolated to its own key. The result carries the new entry's 1-based rank
-    within its key (``None`` if it fell outside the cap) and whether it became
-    that key's new best. ``map`` and ``rules_version`` are required, never
-    defaulted, so a caller can never record under the wrong key.
+    ``(map, mapDefinitionVersion, rulesVersion)`` group is truncated to
+    ``HIGHSCORES_PER_KEY_CAP``. Entries under other keys are never dropped -- for
+    the canonical boards the recorder itself produces they are returned unchanged
+    -- so a record is isolated to its own key. The result carries the new entry's
+    1-based rank within its key (``None`` if it fell outside the cap) and whether it
+    became that key's new best. ``map``, ``map_definition_version``, and
+    ``rules_version`` are required, never defaulted, so a caller can never record
+    under the wrong key.
     """

-    # Fail fast on misuse: a negative/non-int deliveries or a non-ASCII key must
-    # raise here rather than mint a bogus entry that a later save would persist
-    # into a board that reloads empty (codex MAJOR-2).
+    # Fail fast on misuse: a negative/non-int deliveries, a malformed map id, or a
+    # non-positive/non-int map version must raise HERE rather than mint a bogus entry
+    # that a later save would persist into a board that reloads empty (codex MAJOR-2,
+    # GM-09f2 codex MINOR-1). map grammar mirrors the save's mapId.
     _nonnegative_int(deliveries, "deliveries")
-    _ascii_string(map, "map")
+    _map_id(map, "map")
+    _positive_int(map_definition_version, "mapDefinitionVersion")
     _ascii_string(rules_version, "rulesVersion")

-    entry = {"map": map, "rulesVersion": rules_version, "deliveries": deliveries}
+    entry = {
+        "map": map,
+        "mapDefinitionVersion": map_definition_version,
+        "rulesVersion": rules_version,
+        "deliveries": deliveries,
+    }
     entries = [dict(existing) for existing in document["entries"]]
     entries.append(entry)
     entries.sort(key=_sort_key)
-    target = (map, rules_version)
+    target = (map, map_definition_version, rules_version)
     kept: list[dict[str, Any]] = []
     seen_target = 0
     for item in entries:
-        if (item["map"], item["rulesVersion"]) == target:
-            # Only the recorded key is capped; unrelated keys are never dropped,
+        if _identity(item) == target:
+            # Only the recorded identity is capped; unrelated keys are never dropped,
             # so recording one key cannot evict another's entries (codex MAJOR-3).
             if seen_target < HIGHSCORES_PER_KEY_CAP:
                 kept.append(item)
@@ -142,7 +185,9 @@ def record_score(
     rank: int | None = None
     position = 0
     for item in kept:
-        if item["map"] == map and item["rulesVersion"] == rules_version:
+        # Rank within the FULL identity (not map+rules only), or classic@2 would
+        # miscount against a classic@1 group (GM-09f2 review MAJOR).
+        if _identity(item) == target:
             position += 1
             if item is entry:
                 rank = position
diff --git a/src/main.py b/src/main.py
index 29a90c0..856a38e 100644
--- a/src/main.py
+++ b/src/main.py
@@ -21,7 +21,6 @@ from config import (
 from event.convert import convert_pygame_event
 from game_session import GameSession
 from highscores import (
-    HIGHSCORES_MAP_CLASSIC,
     RecordResult,
     load_highscores,
     record_score,
@@ -120,16 +119,23 @@ def record_highscore(mediator: object) -> RecordResult | None:
     # The single best-effort recorder BOTH game-over surfaces funnel through --
     # the controller promotion seam and the window-close race -- so patching this
     # one symbol (or HIGHSCORES_PATH) intercepts all recording (codex MINOR-4).
-    # It reads the objective off the mediator and must never crash or block the
-    # game loop: any failure (a corrupt board, an unwritable directory, or even a
-    # RecursionError from a pathologically nested file -- MAJOR-2) is swallowed to
-    # None, exactly as the proven autosave writer does.
+    # It reads the objective AND the live map identity off the mediator (GM-09f2) so
+    # a non-Classic run is keyed by its own map, and must never crash or block the
+    # game loop: any failure (a corrupt board, an unwritable directory, an exotic
+    # mediator lacking map_definition, or even a RecursionError from a pathologically
+    # nested file -- MAJOR-2) is swallowed to None, exactly as the autosave writer
+    # does. Reading the map directly (no `or classic` default) is fail-SAFE: a
+    # missing map records nothing rather than mislabelling a score (GM-09f `or
+    # DEFAULT` lesson). A real Mediator always has map_definition (default CLASSIC).
     try:
+        deliveries = mediator.deliveries
+        map_definition = mediator.map_definition
         document = load_highscores(HIGHSCORES_PATH)
         result = record_score(
             document,
-            deliveries=mediator.deliveries,
-            map=HIGHSCORES_MAP_CLASSIC,
+            deliveries=deliveries,
+            map=map_definition.map_id,
+            map_definition_version=map_definition.map_definition_version,
             rules_version=SAVE_RULES_VERSION,
         )
         save_highscores(result.document, HIGHSCORES_PATH)
@@ -239,12 +245,14 @@ def run_game(
     )

     # The controller records the high score at the PLAYING->GAME_OVER promotion
-    # and hands back the result for the best indicator (D-028). The promotion
-    # passes the deliveries scalar; route it through the one patchable
-    # record_highscore (looked up at call time) so both game-over surfaces share
-    # a single recorder and a single test seam (codex MINOR-4).
-    def _record_promotion(deliveries: int) -> RecordResult | None:
-        return record_highscore(SimpleNamespace(deliveries=deliveries))
+    # and hands back the result for the best indicator (D-028). The controller hands
+    # the seam the LIVE mediator (GM-09f2), so the promotion and the window-close
+    # race both call the IDENTICAL record_highscore(mediator) -- which reads the
+    # deliveries objective AND the map identity off it. record_highscore is looked
+    # up at call time (not bound) so a test patching main.record_highscore intercepts
+    # both surfaces through this one seam (codex MINOR-4).
+    def _record_promotion(mediator: object) -> RecordResult | None:
+        return record_highscore(mediator)

     highscores = SimpleNamespace(record=_record_promotion)

diff --git a/test/test_gm07d_highscores.py b/test/test_gm07d_highscores.py
index f3f14d1..2b81c59 100644
--- a/test/test_gm07d_highscores.py
+++ b/test/test_gm07d_highscores.py
@@ -41,16 +41,22 @@ def _symbol(testcase, name, module_name=HIGHSCORES_MODULE):


 def _empty_doc() -> dict:
-    return {"schemaVersion": 1, "stateContract": STATE_CONTRACT, "entries": []}
+    return {"schemaVersion": 2, "stateContract": STATE_CONTRACT, "entries": []}


-def _entry(map_id: str, rules: str, deliveries: int) -> dict:
-    return {"map": map_id, "rulesVersion": rules, "deliveries": deliveries}
+def _entry(map_id: str, rules: str, deliveries: int, version: int = 1) -> dict:
+    # GM-09f2 v2 entry: keyed by the full map identity (map, mapDefinitionVersion).
+    return {
+        "map": map_id,
+        "mapDefinitionVersion": version,
+        "rulesVersion": rules,
+        "deliveries": deliveries,
+    }


 def _valid_doc() -> dict:
     return {
-        "schemaVersion": 1,
+        "schemaVersion": 2,
         "stateContract": STATE_CONTRACT,
         "entries": [
             _entry("classic", "rules-v1", 7),
@@ -59,18 +65,31 @@ def _valid_doc() -> dict:
     }


-def _record(testcase, document, deliveries, map="classic", rules_version="rules-v1"):
+def _record(
+    testcase,
+    document,
+    deliveries,
+    map="classic",
+    rules_version="rules-v1",
+    map_definition_version=1,
+):
     record_score = _symbol(testcase, "record_score")
     return record_score(
-        document, deliveries=deliveries, map=map, rules_version=rules_version
+        document,
+        deliveries=deliveries,
+        map=map,
+        map_definition_version=map_definition_version,
+        rules_version=rules_version,
     )


-def _group(document, map="classic", rules="rules-v1"):
+def _group(document, map="classic", rules="rules-v1", version=1):
     return [
         entry
         for entry in document["entries"]
-        if entry["map"] == map and entry["rulesVersion"] == rules
+        if entry["map"] == map
+        and entry["rulesVersion"] == rules
+        and entry["mapDefinitionVersion"] == version
     ]


@@ -82,7 +101,7 @@ class TestGM07dHighscoresConstants(unittest.TestCase):
     def test_versioned_constants(self):
         module = _module(self)
         for name, expected in (
-            ("HIGHSCORES_SCHEMA_VERSION", 1),
+            ("HIGHSCORES_SCHEMA_VERSION", 2),
             ("HIGHSCORES_STATE_CONTRACT", STATE_CONTRACT),
             ("HIGHSCORES_PER_KEY_CAP", 10),
             ("HIGHSCORES_MAP_CLASSIC", "classic"),
@@ -107,11 +126,13 @@ class TestGM07dValidateHighscores(unittest.TestCase):
     def test_header_strictness(self):
         self._assert_rejected(
             {
-                "forward schemaVersion": lambda d: d.update(schemaVersion=2),
+                # 2 is now the SUPPORTED version (GM-09f2); 3 is the forward version.
+                "forward schemaVersion": lambda d: d.update(schemaVersion=3),
+                "legacy v1 schemaVersion": lambda d: d.update(schemaVersion=1),
                 "zero schemaVersion": lambda d: d.update(schemaVersion=0),
                 "bool schemaVersion": lambda d: d.update(schemaVersion=True),
-                "string schemaVersion": lambda d: d.update(schemaVersion="1"),
-                "float schemaVersion": lambda d: d.update(schemaVersion=1.0),
+                "string schemaVersion": lambda d: d.update(schemaVersion="2"),
+                "float schemaVersion": lambda d: d.update(schemaVersion=2.0),
                 "null schemaVersion": lambda d: d.update(schemaVersion=None),
                 "wrong stateContract": lambda d: d.update(stateContract="other"),
                 "empty stateContract": lambda d: d.update(stateContract=""),
@@ -140,12 +161,35 @@ class TestGM07dValidateHighscores(unittest.TestCase):
             {
                 "entry unknown key": lambda d: d["entries"][0].update(bonus=1),
                 "entry missing map": lambda d: d["entries"][0].pop("map"),
+                "entry missing mapDefinitionVersion": lambda d: d["entries"][0].pop(
+                    "mapDefinitionVersion"
+                ),
                 "entry missing rulesVersion": lambda d: d["entries"][0].pop(
                     "rulesVersion"
                 ),
                 "entry missing deliveries": lambda d: d["entries"][0].pop("deliveries"),
                 "entry not an object": lambda d: d["entries"].__setitem__(0, [1, 2]),
                 "non-string map": lambda d: d["entries"][0].update(map=1),
+                # GM-09f2 map grammar: non-empty ASCII, no whitespace (mirrors the save).
+                "empty map": lambda d: d["entries"][0].update(map=""),
+                "whitespace map": lambda d: d["entries"][0].update(map="a b"),
+                "non-ascii map": lambda d: d["entries"][0].update(map="rivér"),
+                # GM-09f2 mapDefinitionVersion: positive non-bool int (mirrors the save).
+                "zero mapDefinitionVersion": lambda d: d["entries"][0].update(
+                    mapDefinitionVersion=0
+                ),
+                "negative mapDefinitionVersion": lambda d: d["entries"][0].update(
+                    mapDefinitionVersion=-1
+                ),
+                "bool mapDefinitionVersion": lambda d: d["entries"][0].update(
+                    mapDefinitionVersion=True
+                ),
+                "float mapDefinitionVersion": lambda d: d["entries"][0].update(
+                    mapDefinitionVersion=1.0
+                ),
+                "string mapDefinitionVersion": lambda d: d["entries"][0].update(
+                    mapDefinitionVersion="1"
+                ),
                 "non-string rulesVersion": lambda d: d["entries"][0].update(
                     rulesVersion=2
                 ),
@@ -291,22 +335,55 @@ class TestGM07dRecordScore(unittest.TestCase):
                     _empty_doc(),
                     deliveries=bad,
                     map="classic",
+                    map_definition_version=1,
                     rules_version="rules-v1",
                 )

-    def test_record_score_requires_explicit_map_and_rules_version(self):
-        # The map and rules identity are required, never silently defaulted, so
-        # a caller can never record under the wrong key (codex MINOR-3).
+    def test_record_score_requires_explicit_map_identity_and_rules_version(self):
+        # map, mapDefinitionVersion, and rules identity are required, never silently
+        # defaulted, so a caller can never record under the wrong key (codex MINOR-3;
+        # GM-09f2 adds mapDefinitionVersion to that rule).
         record_score = _symbol(self, "record_score")
         with self.assertRaises(TypeError):
             record_score(_empty_doc(), deliveries=5)
+        with self.assertRaises(TypeError):
+            # map + rules given, but mapDefinitionVersion omitted -> still required.
+            record_score(
+                _empty_doc(), deliveries=5, map="classic", rules_version="rules-v1"
+            )
+
+    def test_record_score_rejects_invalid_map_identity(self):
+        # GM-09f2 codex MINOR-1: a malformed map id or a non-positive/non-int map
+        # version must fail fast here, not silently mint an entry that only breaks at
+        # save. map grammar mirrors the save's mapId (non-empty ASCII, no whitespace).
+        record_score = _symbol(self, "record_score")
+        for bad_map in ("", "a b", "rivér", 1):
+            with self.assertRaises(ValueError, msg=f"map={bad_map!r} must be rejected"):
+                record_score(
+                    _empty_doc(),
+                    deliveries=5,
+                    map=bad_map,
+                    map_definition_version=1,
+                    rules_version="rules-v1",
+                )
+        for bad_version in (0, -1, True, 1.0, "1"):
+            with self.assertRaises(
+                ValueError, msg=f"mapDefinitionVersion={bad_version!r} must be rejected"
+            ):
+                record_score(
+                    _empty_doc(),
+                    deliveries=5,
+                    map="classic",
+                    map_definition_version=bad_version,
+                    rules_version="rules-v1",
+                )

     def test_recording_one_key_never_drops_another_over_cap_key(self):
         # An externally authored board may hold an over-cap group that validation
         # accepts (it checks structure, not the cap); recording a DIFFERENT key
         # must never truncate that unrelated group (codex MAJOR-3).
         board = {
-            "schemaVersion": 1,
+            "schemaVersion": 2,
             "stateContract": STATE_CONTRACT,
             "entries": [_entry("beta", "rules-v1", d) for d in range(11, 0, -1)],
         }
@@ -351,7 +428,43 @@ class TestGM07dLoadHighscores(unittest.TestCase):
             "duplicate keys": b'{"schemaVersion":1,"schemaVersion":1,'
             b'"stateContract":"' + STATE_CONTRACT.encode("ascii") + b'","entries":[]}',
             "forward version": json.dumps(
-                {"schemaVersion": 2, "stateContract": STATE_CONTRACT, "entries": []}
+                {"schemaVersion": 3, "stateContract": STATE_CONTRACT, "entries": []}
+            ).encode("ascii"),
+            # GM-09f2 (D-039): a legacy v1 board (three-field entries, no
+            # mapDefinitionVersion) is NOT migrated -- its map labels are not
+            # provably accurate -- so it starts empty like any other unreadable
+            # format rather than synthesizing authoritative classic@1.
+            "legacy v1 board": json.dumps(
+                {
+                    "schemaVersion": 1,
+                    "stateContract": STATE_CONTRACT,
+                    "entries": [
+                        {"map": "classic", "rulesVersion": "rules-v1", "deliveries": 9}
+                    ],
+                }
+            ).encode("ascii"),
+            # A SUPPORTED-version (v2) board that is still malformed must START-EMPTY:
+            # the loader validates, it does not trust any v2 mapping (codex MINOR).
+            "malformed v2 (extra entry key)": json.dumps(
+                {
+                    "schemaVersion": 2,
+                    "stateContract": STATE_CONTRACT,
+                    "entries": [dict(_entry("classic", "rules-v1", 5), bonus=1)],
+                }
+            ).encode("ascii"),
+            "malformed v2 (bad mapDefinitionVersion)": json.dumps(
+                {
+                    "schemaVersion": 2,
+                    "stateContract": STATE_CONTRACT,
+                    "entries": [
+                        {
+                            "map": "classic",
+                            "mapDefinitionVersion": True,
+                            "rulesVersion": "rules-v1",
+                            "deliveries": 5,
+                        }
+                    ],
+                }
             ).encode("ascii"),
             "pathologically deep nesting": deep,
         }
diff --git a/test/test_gm07d_recorder_controller.py b/test/test_gm07d_recorder_controller.py
index dd1ad26..3e84598 100644
--- a/test/test_gm07d_recorder_controller.py
+++ b/test/test_gm07d_recorder_controller.py
@@ -127,14 +127,21 @@ def _factories(mediator_factory):


 class _SpyHighscores:
-    """Records each ``record(deliveries)`` and returns preloaded results."""
+    """Records each ``record(mediator)`` and returns preloaded results.
+
+    GM-09f2: the seam receives the live mediator (the recorder derives deliveries
+    AND the map identity from it), so the spy records ``mediator.deliveries`` to
+    keep pinning the recorded objective.
+    """

     def __init__(self, results=()):
         self.deliveries_seen = []
+        self.mediators_seen = []  # the RAW seam argument, to pin identity
         self._results = list(results)

-    def record(self, deliveries):
-        self.deliveries_seen.append(deliveries)
+    def record(self, mediator):
+        self.mediators_seen.append(mediator)
+        self.deliveries_seen.append(mediator.deliveries)
         if self._results:
             return self._results.pop(0)
         return None
@@ -172,6 +179,15 @@ class TestGM07dRecorderSeam(unittest.TestCase):
         self.assertEqual(
             spy.deliveries_seen, [42], "the promotion records mediator.deliveries once"
         )
+        # The seam must receive the LIVE mediator ITSELF (so the recorder can read
+        # its map identity), not a deliveries-only wrapper -- a regression that
+        # forwarded SimpleNamespace(deliveries=...) would still match deliveries_seen
+        # but drop the map, so pin identity (GM-09f2 review MAJOR).
+        self.assertIs(
+            spy.mediators_seen[0],
+            controller.mediator,
+            "the seam receives the live mediator, not a deliveries wrapper",
+        )
         self.assertIs(
             controller.last_highscore_result,
             result,
diff --git a/test/test_gm07d_run_game_loop.py b/test/test_gm07d_run_game_loop.py
index d7cb152..e5cc7d2 100644
--- a/test/test_gm07d_run_game_loop.py
+++ b/test/test_gm07d_run_game_loop.py
@@ -40,6 +40,11 @@ class _LoopMediator:
     def __init__(self, game_over: bool) -> None:
         self.is_game_over = game_over
         self.deliveries = 11
+        # GM-09f2: the recorder reads the live map identity off the mediator; a real
+        # Mediator always has map_definition (default CLASSIC). classic@1 here.
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held: list[str] = []

     def hold_pause_reason(self, reason: str) -> None:
@@ -207,26 +212,51 @@ class TestGM07dRecordHighscoreSwallowsFailures(unittest.TestCase):


 class TestGM07dRecordHighscoreIsReadOnly(unittest.TestCase):
-    def test_record_highscore_reads_deliveries_and_mutates_no_mediator_state(self):
-        # PLAN.md:27 / codex MINOR-5a: the single recorder both game-over
-        # surfaces call READS the objective off the mediator and mutates nothing,
-        # so the checkpoint it never touches stays identical.
-        mediator = SimpleNamespace(deliveries=7)
+    def test_record_highscore_reads_deliveries_and_map_and_mutates_no_mediator_state(
+        self,
+    ):
+        # PLAN.md / codex MINOR-5a: the single recorder both game-over surfaces call
+        # READS the objective AND the live map identity (GM-09f2) off the mediator
+        # and mutates nothing, so the checkpoint it never touches stays identical.
+        mediator = SimpleNamespace(
+            deliveries=7,
+            map_definition=SimpleNamespace(map_id="classic", map_definition_version=1),
+        )
         before = dict(mediator.__dict__)
         with tempfile.TemporaryDirectory() as directory:
             target = Path(directory) / "highscores.json"
             with patch("main.HIGHSCORES_PATH", target, create=True):
                 result = main.record_highscore(mediator)
                 self.assertTrue(target.exists(), "a first best writes the board")
+            entry = result.document["entries"][0]
             self.assertEqual(
-                result.document["entries"][0]["deliveries"],
+                entry["deliveries"],
                 7,
                 "the recorded deliveries are read off the mediator",
             )
+            self.assertEqual(
+                entry["map"], "classic", "the recorded map id is read off the mediator"
+            )
+            self.assertEqual(
+                entry["mapDefinitionVersion"],
+                1,
+                "the recorded map version is read off the mediator",
+            )
         self.assertEqual(
             mediator.__dict__, before, "the recorder must not mutate the mediator"
         )

+    def test_record_highscore_swallows_a_mediator_without_map_definition(self):
+        # GM-09f2 fail-safe: an exotic mediator lacking map_definition records
+        # NOTHING (swallowed to None) rather than mislabelling a score.
+        mediator = SimpleNamespace(deliveries=7)  # no map_definition
+        with tempfile.TemporaryDirectory() as directory:
+            target = Path(directory) / "highscores.json"
+            with patch("main.HIGHSCORES_PATH", target, create=True):
+                result = main.record_highscore(mediator)
+            self.assertIsNone(result, "a missing map_definition records nothing")
+            self.assertFalse(target.exists(), "a swallowed record writes no board")
+

 if __name__ == "__main__":
     unittest.main()
diff --git a/test/test_gm07e_game_over_reconcile.py b/test/test_gm07e_game_over_reconcile.py
index 0cbea27..7d4da76 100644
--- a/test/test_gm07e_game_over_reconcile.py
+++ b/test/test_gm07e_game_over_reconcile.py
@@ -87,8 +87,11 @@ class _SpyHighscores:
         self.deliveries_seen = []
         self._results = list(results)

-    def record(self, deliveries):
-        self.deliveries_seen.append(deliveries)
+    def record(self, mediator):
+        # GM-09f2: the seam now receives the live mediator; the recorder derives the
+        # deliveries objective (and the map identity) from it, so the spy records
+        # mediator.deliveries to keep pinning the recorded objective.
+        self.deliveries_seen.append(mediator.deliveries)
         if self._results:
             return self._results.pop(0)
         return None
@@ -432,16 +435,15 @@ class TestGM07eRunLoopEventlessReconcile(unittest.TestCase):
             1,
             "exactly one record across the reconcile and the QUIT gate",
         )
-        # The RECONCILE recorded, not the QUIT gate: the promotion seam passes a
-        # bare deliveries namespace, whereas the QUIT gate passes the mediator
-        # itself (which carries is_game_over). This pins WHICH surface fired --
-        # at baseline (no per-frame reconcile) the QUIT gate is the recorder and
-        # this assertion flips (TQ-1 / codex MINOR-5).
+        # The RECONCILE recorded, not the QUIT gate. Both surfaces now hand the
+        # recorder the live mediator (GM-09f2), so WHICH fired is pinned by the SIDE
+        # EFFECT rather than the argument shape: only the per-frame reconcile draws
+        # the best indicator (asserted below, best.call_count == 1); the QUIT gate,
+        # seeing GAME_OVER, records and draws nothing. At baseline (no per-frame
+        # reconcile) the QUIT gate would be the recorder and best would never draw,
+        # so this proof still flips there (TQ-1 / codex MINOR-5). The recorded arg
+        # is the game's mediator, carrying its lifetime deliveries.
         recorded_arg = driver.record.call_args.args[0]
-        self.assertFalse(
-            hasattr(recorded_arg, "is_game_over"),
-            "the frame-accurate reconcile is the recorder, not the window close",
-        )
         self.assertEqual(recorded_arg.deliveries, 11)
         self.assertEqual(
             driver.best.call_count,
```

## New: test/test_gm09f2_highscore_map.py
```python
"""GM-09f2 contract: the high-score leaderboard records the MAP identity (D-039).

The recorder threads the LIVE ``map_definition`` (id + version) off the mediator
instead of hardcoding ``classic``, and the leaderboard keys every entry by the full
``(map, mapDefinitionVersion, rulesVersion)`` identity -- so a non-Classic run is
recorded under its own map, and a future ``classic@2`` terrain revision ranks and
caps separately from ``classic@1``. A legacy v1 board is NOT migrated (its map labels
are not provably accurate); it starts empty like any other unreadable format.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main
from highscores import (
    HIGHSCORES_PER_KEY_CAP,
    HIGHSCORES_SCHEMA_VERSION,
    record_score,
    validate_highscores,
)
from maps import CLASSIC, RIVER


def _empty_board() -> dict:
    return {
        "schemaVersion": HIGHSCORES_SCHEMA_VERSION,
        "stateContract": "mini-metro-highscores-v1",
        "entries": [],
    }


def _mediator(deliveries: int, map_definition) -> SimpleNamespace:
    # The recorder reads deliveries + map_definition.{map_id, map_definition_version}.
    return SimpleNamespace(deliveries=deliveries, map_definition=map_definition)


class TestGM09f2RecorderThreadsLiveMap(unittest.TestCase):
    """main.record_highscore records the mediator's real map, not a hardcoded classic."""

    def _record_real(self, mediator):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            with patch("main.HIGHSCORES_PATH", target, create=True):
                result = main.record_highscore(mediator)
                stored = json.loads(target.read_bytes()) if target.exists() else None
        return result, stored

    def test_classic_run_records_under_classic_at_one(self):
        result, stored = self._record_real(_mediator(7, CLASSIC))
        entry = result.document["entries"][0]
        self.assertEqual(
            (entry["map"], entry["mapDefinitionVersion"], entry["deliveries"]),
            ("classic", 1, 7),
        )
        self.assertEqual(stored["entries"][0]["map"], "classic")

    def test_a_river_run_records_under_river_not_classic(self):
        # The load-bearing GM-09f2 behavior: a non-Classic game is keyed by ITS map.
        result, _stored = self._record_real(_mediator(9, RIVER))
        entry = result.document["entries"][0]
        self.assertEqual(entry["map"], "river", "a river run must record under river")
        self.assertEqual(entry["mapDefinitionVersion"], RIVER.map_definition_version)
        self.assertEqual(entry["deliveries"], 9)

    def test_a_non_one_map_version_is_read_not_hardcoded(self):
        # Both real maps are @1, so a regression forwarding a literal version 1 would
        # pass the classic/river tests; drive a synthetic non-1 version to PROVE the
        # recorder reads map_definition.map_definition_version (GM-09f2 review MAJOR).
        synthetic = SimpleNamespace(map_id="classic", map_definition_version=7)
        result, stored = self._record_real(_mediator(4, synthetic))
        entry = result.document["entries"][0]
        self.assertEqual(
            entry["mapDefinitionVersion"], 7, "the recorder reads the live map version"
        )
        self.assertEqual(
            stored["entries"][0]["mapDefinitionVersion"],
            7,
            "the persisted board preserves the live version",
        )

    def test_the_recorded_board_validates_as_v2(self):
        result, _stored = self._record_real(_mediator(5, RIVER))
        self.assertEqual(result.document["schemaVersion"], 2)
        self.assertIsNone(validate_highscores(result.document))


class TestGM09f2CrossDefinitionVersionIdentity(unittest.TestCase):
    """The full identity keys the rank AND the cap, so classic@2 is independent of @1."""

    def _board_with(self, entries) -> dict:
        board = _empty_board()
        board["entries"] = entries
        validate_highscores(board)
        return board

    def test_a_fresh_definition_version_ranks_first_not_against_the_old(self):
        # The rank-loop MAJOR (both plan lanes): a first classic@2 score must be rank 1
        # / is_best True even when a higher classic@1 group exists -- it is the best of
        # its OWN identity, not rank 2 behind classic@1.
        board = self._board_with(
            [
                {
                    "map": "classic",
                    "mapDefinitionVersion": 1,
                    "rulesVersion": "rules-v1",
                    "deliveries": 100,
                }
            ]
        )
        result = record_score(
            board,
            deliveries=1,
            map="classic",
            map_definition_version=2,
            rules_version="rules-v1",
        )
        self.assertEqual(result.rank, 1, "classic@2's first score ranks 1 within @2")
        self.assertIs(result.is_best, True)

    def test_a_new_version_cannot_evict_an_over_cap_old_version_group(self):
        # Cross-identity isolation: classic@1 holds an over-cap group (validation checks
        # structure, not the cap); recording classic@2 must not truncate it.
        over_cap = [
            {
                "map": "classic",
                "mapDefinitionVersion": 1,
                "rulesVersion": "rules-v1",
                "deliveries": d,
            }
            for d in range(HIGHSCORES_PER_KEY_CAP + 1, 0, -1)
        ]
        board = self._board_with(over_cap)
        result = record_score(
            board,
            deliveries=5,
            map="classic",
            map_definition_version=2,
            rules_version="rules-v1",
        )
        classic_v1 = [
            e
            for e in result.document["entries"]
            if e["map"] == "classic" and e["mapDefinitionVersion"] == 1
        ]
        self.assertEqual(
            len(classic_v1),
            HIGHSCORES_PER_KEY_CAP + 1,
            "recording classic@2 must not drop an over-cap classic@1 entry",
        )
        self.assertEqual((result.rank, result.is_best), (1, True))

    def test_two_definition_versions_sort_as_distinct_groups(self):
        board = _empty_board()
        for deliveries, version in ((5, 1), (9, 2), (3, 1), (7, 2)):
            board = record_score(
                board,
                deliveries=deliveries,
                map="classic",
                map_definition_version=version,
                rules_version="rules-v1",
            ).document
        ordered = [
            (e["mapDefinitionVersion"], e["deliveries"]) for e in board["entries"]
        ]
        # Canonical order: identity ascending (version 1 before 2), deliveries desc.
        self.assertEqual(ordered, [(1, 5), (1, 3), (2, 9), (2, 7)])


class TestGM09f2LegacyBoardStartsEmpty(unittest.TestCase):
    def test_a_v1_board_is_not_migrated_but_starts_empty(self):
        # D-039: a v1 board's map="classic" labels are not provably accurate (the
        # recorder was classic-hardcoded while non-Classic saves became loadable), so
        # it is discarded rather than synthesized to authoritative classic@1.
        from highscores import load_highscores

        v1_board = {
            "schemaVersion": 1,
            "stateContract": "mini-metro-highscores-v1",
            "entries": [
                {"map": "classic", "rulesVersion": "rules-v1", "deliveries": 42}
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            target.write_bytes(json.dumps(v1_board).encode("ascii"))
            loaded = load_highscores(target)
        self.assertEqual(loaded, _empty_board(), "a legacy v1 board starts empty")


if __name__ == "__main__":
    unittest.main()
```

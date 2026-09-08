# GM-09f save-schema v2 — implementation diff (post-fold)

New files: `test/test_gm09f_save_map.py`, `scripts/fixtures/save-v2-classic.json` (15485 bytes, SHA `60f2bc16c39610b8822288ebf08eea214cb2d0f54c9ac0208113a0892badbd84`).

Tracked changes vs HEAD (`fd49097` = GM-09e:B), repo-normalized (LF):

```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index 08c47dc..729d8e0 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -32,7 +32,8 @@ python_mini_metro/
 |  |  |- recursive-playtest-v3.json
 |  |  |- recursive-playtest-v4.json
 |  |  |- recursive-playtest.json
-|  |  \- save-v1.json
+|  |  |- save-v1.json
+|  |  \- save-v2-classic.json
 |  |- playtest-recursive.mjs
 |  |- playtest-verify.mjs
 |  |- input_coordinator_differential_actions.py
@@ -374,6 +375,7 @@ python_mini_metro/
 - GM-09c (D-035) makes the river a real obstacle via a finite tunnel budget. A new dependency-light `src/crossings.py` — importing ONLY `geometry.point`, reading duck-typed hosts by `getattr` — owns the pure geometry (`segment_crosses_band` Liang-Barsky slab returning the entry point, with a zero-length grazing touch deliberately NOT counted; `path_crossings` counts one entry per band on a path's CENTERLINE of consecutive `station.position` pairs plus the loop closure, where a 2-station loop's closure is skipped so it cannot double-charge) AND the single route-edit gate `within_tunnel_budget(host, stations, is_looped, *, exclude=)` shared by both edit paths. `MapDefinition` gains an additive `tunnel_budget: int | None` (validated non-negative-int-or-None in `__post_init__`); `RIVER` sets `3`, `CLASSIC` leaves `None` (unbounded). `Mediator` exposes `num_tunnels`, `consumed_tunnels`, and `available_tunnels` as three DERIVED properties — `num_tunnels` reads `map_definition.tunnel_budget`, `consumed_tunnels` sums `path_crossings` over every committed line, `available_tunnels` is `max(0, num_tunnels - consumed)` or `None` when unbounded. None is cached, so a swapped map stays consistent and a stale copy can never fail open, and removal/reroute refund for free with NO snapshot field (the `available_locomotives` pattern). The read-only gate `within_tunnel_budget` reads the budget and rivers from `map_definition` and counts the REAL resolved draft (`creating.stations`/`is_looped`), never a route predicted from raw indices — the construction dedups an explicit-closure `[X,Y,X]` to the 2-station loop `[X,Y]` and can loop-form on a repeated station, so a raw-index pre-check both false-rejects a valid loop and false-accepts a mid-repeat. It gates where the final draft is known, BEFORE any extend/loop mutation: `path_lifecycle.end_path_on_station` on release and `finish_path_creation` at the commit boundary (catching a direct `start/add/finish` bypass). An over-budget release adds no station and commits no crossing; the rejection is count-, path-, and RNG-inert. The shared `abort_path_creation`/`assign_paths_to_buttons` are UNCHANGED from pre-GM-09c (so CLASSIC, whose gates always pass, stays byte-identical) — a re-review showed that folding a snap-blip rollback or a draft-skipping button pass into them broke CLASSIC's bytes and mis-owned a reclaimed-color blip, so the pre-existing transient-blip-on-abort and ghost-button-after-mid-draft-removal are left to a follow-up. `path_replacement.replace_path` calls it in preflight (excluding the rerouted line) before `build_candidate`. `env.observe` adds a `tunnels` block (`total`/`consumed`/`available`) as a SIBLING of `fleet`, never a fleet key, so the canonical checkpoint's exact fleet-key whitelist and every save fixture stay valid. `rendering/terrain_renderer.draw_crossings` paints a tunnel-portal marker at each crossing ON TOP of the network (lazy-importing `crossings` inside the function, as `network_renderer` does with `config`, so `src.rendering` stays importable during test discovery); CLASSIC (no rivers) draws nothing, so its frame stays byte-identical. `crossings.py` stays import-safe (no pygame/mediator/shapely). `path_replacement.py` is 501 lines — one over the soft guideline on a pre-existing ~500-line file, far under the 1000 hard ceiling.
 - GM-09d (D-036) adds the SECOND alternate map, `DELTA`, with NO new machinery — it is a pure `MapDefinition` addition proving the GM-09b/GM-09c layer generalizes. Two vertical channels (`rivers` = 2 bands) split the play area into THREE `station_size`-eroded banks (`spawn_regions` = 3 rects), with `tunnel_budget=4`; a line spanning both channels consumes two tunnels, exercising the multi-band `path_crossings` count and the finite budget more than the single-river `RIVER`. Registered so `KNOWN_MAP_IDS == ("classic", "delta", "river")`. The addition is purely additive — the region-aware spawn (`_sample_position` accepts a candidate inside any of the three regions), the terrain/crossing renderers (loop over all bands), the derived tunnel count, and the fail-closed save guard all already handle N regions/rivers, so CLASSIC and RIVER stay byte-identical (the `test_gm09a_maps` fingerprints and `save-v1.json` are unmoved). The GM-09b exact-`KNOWN_MAP_IDS` test was loosened to membership so later maps do not break it.
 - GM-09e (D-037) adds the THIRD alternate map, `LAKE`, again with NO new machinery, but exercising a generality dimension the RIVER/DELTA channels never did: a PARTIAL band. `LAKE.rivers` is a single BOUNDED rect (a central lake spanning no screen edge), so `crossings.segment_crosses_band` is tested on a rect bounded in both x and y — a line's centerline that passes through the lake counts one crossing, and a line routed AROUND it counts none. `spawn_regions` is a FRAME of four overlapping strips (top/bottom full-width, left/right full-height, each eroded from the lake by `station_size`) whose union is the whole screen minus the lake; the region-accept spawn (`_point_in_rects`, any-region) needs no change. Because the lake is bounded, a line can OFTEN be routed around it (a line bends only at stations, so a dry detour needs an intermediate station beside the lake) instead of tunnelling through — so `tunnel_budget=3` mostly caps shortcuts, but still limits TOTAL crossings and a station whose only routes cross the lake is gated until a tunnel is freed, as on the channels (a re-review corrected an over-claim that the lake "never gates connectivity"). GM-09e also promoted `crossings.segment_crosses_band` to STRICT-interior semantics: a segment collinear with a band EDGE now counts zero — reachable on LAKE (integer vertical edges with no x-erosion of the top/bottom banks), which supersedes GM-09c's deferral; RIVER/DELTA never place a centerline on an edge, so their counts are unmoved. `KNOWN_MAP_IDS == ("classic", "delta", "lake", "river")`; CLASSIC/RIVER/DELTA stay byte-identical.
+- GM-09f (D-038) begins the map/save integration (SPLIT into save-schema / high-score / menu) with the SAVE-SCHEMA v2 map field. `save_schema` gains `SAVE_SCHEMA_VERSION_V2 = 2` (`SUPPORTED = {1, 2}`, current = 2) with two additive top-level keys `mapId`/`mapDefinitionVersion`; `validate_save` is TWO-PHASE (read + support-check `schemaVersion` with a named error BEFORE choosing the version-aware exact-key set `_TOP_LEVEL_KEYS_V1`/`_V2`, so a v1-doc-with-map-keys and a v2-doc-without both fail closed), and the v2 identity is scalar-validated (`_validate_map_identity`). `save_game.serialize_game` replaces `_require_classic_map` with a fail-closed pair: STRUCTURAL `map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`, since a v2 save records only the identity and rebuilds terrain from the registry on load) and `save_load._require_legal_map_state` (every station on the map's `spawn_regions`; `consumed_tunnels <= num_tunnels`) — the latter shared by serialize and post-load so a forged illegal state (a Classic state relabeled `river@1`) is refused both ways. `save_load.deserialize_game` reads the map identity for v2 / synthesizes `classic@1` for v1, resolves via `resolve_map` (fail-closed on unknown id / unsupported version), and threads `map_definition` into the `Mediator`; tunnel counts stay derived. The byte-frozen `scripts/fixtures/save-v1.json` is unchanged and still loads as Classic; the deterministic v1→v2 header-only upgrade is pinned by a new frozen `scripts/fixtures/save-v2-classic.json` (15485 bytes) that the idempotence + cross-process determinism tests target. `stateContract`/`rulesVersion` unchanged; the RL manifest and recursive checkpoint are separate schemas. The high-score `mapDefinitionVersion` and the in-game map menu follow as the next two sub-units (menu last, so it cannot feed an alternate map to the still-classic-hardcoded score recorder).
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
diff --git a/GAME_RULES.md b/GAME_RULES.md
index d3d71b8..bcb7a79 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -30,7 +30,9 @@ This document summarizes the game rules currently implemented in code.
   centre with dry land all around it. On any map with water, stations spawn only on the
   land — their centres are inset from the water by at least a station's size — and the
   water is drawn under the lines and stations. Map selection is available to the RL trainer (`--map river`/`--map delta`/`--map lake`)
-  and the programmatic API today; in-game menu selection arrives in a later unit.
+  and the programmatic API today; in-game menu selection arrives in a later unit. A
+  saved game records its map, so a non-Classic game saves and loads with its map (and
+  terrain) intact; an older save with no map recorded loads as `classic`.
 - On a map with water, lines cross it through a limited pool of tunnels. The
   `river` map has a budget of 3, `delta` a budget of 4, and `lake` a budget of 3: every
   place where a line's route crosses the water consumes one tunnel (so a `delta` line
diff --git a/PROGRESS.md b/PROGRESS.md
index 9d31190..8d225dc 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -176,3 +176,4 @@
 ## 2026-07-24

 - Added the third alternate map with GM-09e, `LAKE` (D-037) -- a single bounded central lake (spanning no screen edge), `tunnel_budget=3`, again a PURE `MapDefinition` addition with NO new machinery. It exercises the one map-layer generality dimension RIVER/DELTA never did: a PARTIAL band (bounded in x AND y). A line whose centerline passes through the lake spends a tunnel; a line routed around it (bending at an intermediate station beside the lake) spends none. The land is a frame of four overlapping strips whose union is the screen minus the lake, and the reused spawn/render/crossing/gate/save code handles it unchanged, so CLASSIC/RIVER/DELTA stay byte-identical (`test_gm09a_maps` fingerprints + frozen `save-v1.json` unmoved, verified at seeds 0/1/4207). Dual adversarial impl review: harness SHIP (6000-station spawn sweep, full partial-band crossing matrix), external Codex ultra FIX-FIRST with a MAJOR the harness endorsed the opposite of -- my load-bearing CLAIM that "the lake never gates connectivity" is FALSE (lines bend only at stations, so at an exhausted budget a station whose only routes cross the lake is gated until a tunnel is freed, exactly as on the rivers). The CODE was correct; the defect was my mischaracterization, corrected across the map comment, `GAME_RULES.md`, D-037, `ARCHITECTURE.md`, and the test (the lake makes crossing more often avoidable, not always). Codex also caught the edge-collinear crossing miscount GM-09c had DEFERRED as "unreachable" but LAKE made reachable (integer water edges); folded by promoting `crossings.segment_crosses_band` to STRICT-interior semantics (a segment along an edge counts zero), verified to leave RIVER/DELTA counts unmoved. All test-hardening folded (14 tests: strict-interior edge, real budget ceiling, four-strip-frame spawn). Full `py313` suite green (1428 tests, 12 skips); `maps.py` 292 lines. GM-09f (in-game menu + save-schema map field + high-score `mapDefinitionVersion`) is next -- the deferred map/save integration.
+- Began the map/save integration with GM-09f, the SAVE-SCHEMA v2 map field (D-038) -- the first of a plan-review-driven split (save-schema, then high-score identity, then the in-game menu). The save schema gains `SAVE_SCHEMA_VERSION_V2 = 2` (a superset of v1) with two additive top-level keys `mapId`/`mapDefinitionVersion`, so a non-Classic game (river/delta/lake) saves and loads with its map intact; `validate_save` is two-phase (read + support-check `schemaVersion` with a named error BEFORE choosing the version-aware exact-key set, so a v1-doc-with-map-keys and a v2-doc-without both fail closed). `serialize_game` replaces the old `_require_classic_map` guard with a fail-closed pair: STRUCTURAL `map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`, since a v2 save records only the identity and rebuilds terrain from the registry on load) and a shared `_require_legal_map_state` (stations on the map's land, `consumed_tunnels <= num_tunnels`) applied on serialize AND post-load, so a forged illegal state is refused both ways. `deserialize_game` synthesizes `classic@1` for a v1 doc (keys absent) and resolves the map fail-closed for v2 (unknown id / unsupported version raise), threading `map_definition` into the Mediator; tunnel counts stay derived. The byte-frozen `save-v1.json` is unchanged and still loads as Classic; the deterministic v1->v2 header-only upgrade is pinned by a new frozen `save-v2-classic.json` (15485 bytes, SHA `60f2bc16...` -- exactly Codex's prediction) that the idempotence + cross-process determinism tests target. HIGH-RISK, so escalated to a DUAL plan review (both lanes REVISE, direction + split confirmed) that drove the two load-bearing choices: the guard must be STRUCTURAL (mere resolvability fails open into the GM-09b forged-Classic bug -- verified: 2 of 20 seed-0 CLASSIC stations sit in RIVER's band) and identity alone needs STATE-legality (a valid identity + illegal state is still corrupt). Full `py313` suite green (1442 tests, 12 skips); the three GM-09b/d/e "not serializable" tests flipped to round-trips (the forged-classic rejection stays green). GM-09f2 (high-score `mapDefinitionVersion`) is next, then GM-09f3 (in-game menu, last so it can't feed an alternate map to the still-classic-hardcoded score recorder).
diff --git a/README.md b/README.md
index 7d32513..abaa85b 100644
--- a/README.md
+++ b/README.md
@@ -212,13 +212,13 @@ Any unknown `type`, malformed action payload, or rejected action returns `info["
 ```python
 import save_game

-document = save_game.serialize_game(env.mediator)   # strict schema-v1 dict, never mutates the game
+document = save_game.serialize_game(env.mediator)   # strict schema-v2 dict, never mutates the game
 save_game.save_game(env.mediator, "saves/slot1.save.json")  # atomic canonical write
 mediator = save_game.load_game("saves/slot1.save.json")     # read + validate + reconstruct
 mediator = save_game.deserialize_game(document)             # reconstruct from an in-memory document
 ```

-- Save documents are versioned strict JSON (`save_schema.SAVE_SCHEMA_VERSION == 1`, `stateContract "mini-metro-save-v1"`, `rulesVersion "rules-v1"`). `save_schema.validate_save(document)` rejects unknown/missing keys, wrong scalar types (including bool-as-int), forward versions, malformed or out-of-domain RNG state, ID-grammar violations, path or metro references to locked stations, inconsistent bound-service records, and duplicate or dangling entity references; `load_game` additionally rejects duplicate JSON object keys at every level. Every rejection raises `ValueError`.
+- Save documents are versioned strict JSON (`save_schema.SAVE_SCHEMA_VERSION == 2`, `stateContract "mini-metro-save-v1"`, `rulesVersion "rules-v1"`). `save_schema.validate_save(document)` rejects unknown/missing keys, wrong scalar types (including bool-as-int), forward versions, malformed or out-of-domain RNG state, ID-grammar violations, path or metro references to locked stations, inconsistent bound-service records, and duplicate or dangling entity references; `load_game` additionally rejects duplicate JSON object keys at every level. Every rejection raises `ValueError`.
 - Bytes on disk are the pinned canonical encoding (`save_schema.canonical_save_bytes`: sorted-key, ASCII, compact separators, trailing LF). Saves go through a save-local atomic writer (mkstemp, fsync, `os.replace`), so a failed save leaves an existing destination untouched and no temporary file behind. The default directory name is `config.save_dir_name` (`saves/`, git-ignored); all functions accept explicit paths.
 - Saving is permitted only at a quiescent input boundary: an active path-creation, redraw, or edit gesture raises `ValueError` (a bare pressed mouse button does not block).
 - The human application shell (`src/main.py`) drives one canonical autosave slot at `saves/autosave.json`: it writes on opening the pause menu and on Exit to Title, keeps that save on a mid-run window close, deletes it at game over, and offers Continue on the title screen. Every autosave is best-effort and never blocks play or exit; the isolation-scanned headless, agent, recursive, and RL surfaces gain no save import.
@@ -228,6 +228,7 @@ mediator = save_game.deserialize_game(document)             # reconstruct from a
 - A loaded game is checkpoint-identical to the saved one, both RNG streams included, and replays the identical seeded trajectory as a never-saved control, in the same process and across fresh processes replaying the same save file. Each metro's bound station-service action (with its fractional boarding timers) persists in the document and restores verbatim — including boundaries where the bound action is legitimately stale after a same-tick cross-metro effect — so post-load service resumes exactly like the never-saved game. Held pause reasons (`user`, `menu`) restore verbatim, so a game saved from the pause menu loads paused; `release_pause_reason("menu")` resumes it.
 - Entity ID strings survive save/load. Path IDs are structured-action selectors: a `path_id` observed before saving keeps selecting the same line against the loaded `Mediator`. Station, metro, carriage, and passenger IDs are stable observation/reference identity only — no structured action currently selects by them. IDs are minted per process, so two independently built games never share IDs (and their save files differ even under the same seed); determinism guarantees apply to reloading and replaying a given save file.
 - A save whose `numPaths`, `numMetros`, or `numCarriages` disagrees with the running config is rejected; any trajectory-affecting balance-config change bumps the save schema version (see D-026). The frozen v1 example lives at `scripts/fixtures/save-v1.json`.
+- Save schema v2 (GM-09f, D-038) records the MAP identity. A v2 document adds two additive top-level keys `mapId`/`mapDefinitionVersion`, so a non-Classic map (`river`/`delta`/`lake`) can be saved and loaded; new saves are v2, and `SUPPORTED_SAVE_SCHEMA_VERSIONS = {1, 2}`. A v1 document (no map keys) still loads by synthesizing `classic@1`, so the byte-frozen `save-v1.json` stays valid and loads as Classic; because the v1→v2 upgrade only changes the header, loading a v1 save and re-saving it produces exactly the frozen `scripts/fixtures/save-v2-classic.json` (its byte length + SHA are pinned). Serialization and load are fail-closed on two axes: the map definition must EQUAL its registered definition (a forged/drifted map is rejected — a save records only the map identity and rebuilds terrain from the registry on load), and the state must be LEGAL under that map (every station on the map's land, river crossings within the tunnel budget). Tunnel counts stay derived, so no crossing counter is persisted. Loading an unknown map id or an unsupported map version raises a clear, named error rather than silently falling back to Classic. `stateContract` and `rulesVersion` are unchanged across v1/v2.

 # Player-equivalent reinforcement learning

diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index e34a823..f8331a2 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -232,4 +232,10 @@ Reason: the map layer was designed in GM-09b (regions/rivers) and GM-09c (tunnel

 Decision: GM-09e adds the THIRD alternate map, `LAKE`, as another PURE `MapDefinition` addition with NO new machinery — but chosen to exercise the ONE generality dimension RIVER (one full-height channel) and DELTA (two full-height channels) never did: a PARTIAL band. `LAKE.rivers` is a SINGLE bounded rect — a central lake at x∈[0.40, 0.60]·width, y∈[0.34, 0.66]·height — that spans NO screen edge, so `crossings.segment_crosses_band` (axis-aligned Liang-Barsky) is exercised on a rect bounded in both x AND y: a line whose centerline passes through the lake counts one crossing; a line routed around it counts none. `spawn_regions` is a FRAME of four overlapping land strips — top/bottom (full-width), left/right (full-height), each eroded from the lake by `station_size` — whose union is the whole screen minus the lake vicinity; the region-accept spawn (`_point_in_rects`, accept a candidate inside ANY region) needs no change, and the strips' overlap at the corners is harmless. `tunnel_budget=3`. Registered so `KNOWN_MAP_IDS == ("classic", "delta", "lake", "river")`; CLASSIC/RIVER/DELTA stay byte-identical (unchanged `test_gm09a_maps` fingerprints + frozen `save-v1.json`).

-Reason: with RIVER/DELTA the map layer was proven for full-screen-height channels only; a bounded lake is the cheapest way to prove `segment_crosses_band`/`path_crossings` are correct for a band bounded on all four sides — the geometry a future irregular coastline or island would rely on. The lake is also mechanically DISTINCT: because it spans no edge, a line can OFTEN be DETOURED around it, so crossing is frequently a SHORTCUT (a line tunnelling straight through saves distance) rather than mandatory. But — a line bends only at STATIONS, so a dry detour needs an intermediate station beside the lake; the budget therefore still limits TOTAL crossings, and a station whose only routes all cross the lake is gated until a tunnel is freed by rerouting/removing a line, exactly as on the channels (re-review Codex MAJOR corrected an earlier over-claim that the lake "never gates connectivity"). `tunnel_budget=3` is a genuine constraint — the lake makes crossings MORE OFTEN avoidable than the full-screen channels, not always. This softer, more-routable flavour is the intended distinction, documented in `GAME_RULES.md`. The four-strip frame (rather than one land rect) is forced by the lake being interior; the strips are chosen to overlap so their union has no gap. The in-game map-menu selection and the save-schema/high-score map fields still defer to GM-09f, where map selection makes them meaningful; GM-09f (menu/save/high-score/RL integration) is next.
+Reason: with RIVER/DELTA the map layer was proven for full-screen-height channels only; a bounded lake is the cheapest way to prove `segment_crosses_band`/`path_crossings` are correct for a band bounded on all four sides — the geometry a future irregular coastline or island would rely on. The lake is also mechanically DISTINCT: because it spans no edge, a line can OFTEN be DETOURED around it, so crossing is frequently a SHORTCUT (a line tunnelling straight through saves distance) rather than mandatory. But — a line bends only at STATIONS, so a dry detour needs an intermediate station beside the lake; the budget therefore still limits TOTAL crossings, and a station whose only routes all cross the lake is gated until a tunnel is freed by rerouting/removing a line, exactly as on the channels (re-review Codex MAJOR corrected an earlier over-claim that the lake "never gates connectivity"). `tunnel_budget=3` is a genuine constraint — the lake makes crossings MORE OFTEN avoidable than the full-screen channels, not always. This softer, more-routable flavour is the intended distinction, documented in `GAME_RULES.md`.
+
+## D-038
+
+Decision: GM-09f begins the map/save integration (roadmap GM-09f, SPLIT into save-schema (this) → high-score identity → menu, per the dual plan review) with the SAVE-SCHEMA v2 map field. The save schema gains `SAVE_SCHEMA_VERSION_V2 = 2` (a strict SUPERSET of v1) that adds two additive top-level keys `mapId`/`mapDefinitionVersion`, so a non-Classic game (river/delta/lake) can be saved and loaded; `SAVE_SCHEMA_VERSION` becomes 2 (new saves are v2) and `SUPPORTED_SAVE_SCHEMA_VERSIONS = {1, 2}`. `stateContract`/`rulesVersion` are STABLE across v1/v2 — only `schemaVersion` and the two map keys change. `validate_save` is TWO-PHASE: it reads + support-checks `schemaVersion` (named `ValueError`, never a `KeyError`) BEFORE choosing the version-aware exact-key set (`_TOP_LEVEL_KEYS_V1` vs `_V2`), so a v1 doc carrying map keys AND a v2 doc missing them both fail closed; the v2 map identity is scalar-validated (non-empty ASCII `mapId`, positive non-bool `mapDefinitionVersion`). `serialize_game` drops the old `_require_classic_map` guard for a fail-closed pair: (1) STRUCTURAL — `mediator.map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`), since a v2 save records only the IDENTITY and rebuilds terrain from the registry on load, so a forged/drifted `MapDefinition("classic", 1, rivers=...)` that would reload as the real terrain-free CLASSIC is rejected; and (2) STATE-LEGAL — `_require_legal_map_state` (every station on the map's `spawn_regions`, `consumed_tunnels <= num_tunnels`), applied on serialize AND after reconstruction on load, so a hand-forged v2 doc (a CLASSIC state relabeled `river@1`, whose stations sit in the water, or an over-budget state) is refused. `deserialize_game` reads `mapId`/`mapDefinitionVersion` for a v2 doc and SYNTHESIZES `classic@1` for a v1 doc (keys absent), resolves via `resolve_map` (fail-closed on unknown id / unsupported version — never a silent Classic fallback), and threads `map_definition` into the `Mediator`. Tunnel counts stay DERIVED (no persisted counter). The byte-frozen `scripts/fixtures/save-v1.json` is UNCHANGED on disk (its SHA/length pins hold) and still loads as CLASSIC; because a v1→v2 upgrade only changes the header, a v1 load RE-SAVES as exactly the new frozen `scripts/fixtures/save-v2-classic.json` (15485 bytes, SHA `60f2bc16…`) — a deterministic transform pinned by the idempotence + cross-process determinism tests, both committed LF (no `.gitattributes` eol pin, per the recursive-source-provenance guard).
+
+Reason: the map layer (GM-09a–e) built maps behind a fail-closed save guard that deferred persistence to "when map selection makes the field meaningful". Three maps now exist, so a save must record which one. The DUAL plan review (both lanes REVISE, direction + split confirmed) drove the two load-bearing choices: the guard must be STRUCTURAL (mere resolvability fails open into the GM-09b forged-Classic bug — verified: 2 of 20 seed-0 CLASSIC stations sit in RIVER's band), and identity alone is insufficient without STATE-legality (a valid identity + illegal state is still corrupt). Recording only `(mapId, version)` and rebuilding terrain from the import-safe registry keeps the save minimal and the tunnel budget derived; synthesizing `classic@1` for v1 keeps the frozen fixture valid, exactly as D-026 blessed. The high-score `mapDefinitionVersion` and the in-game map menu are the next two sub-units, IN THAT ORDER — the menu must land last so it can never expose an alternate map to the still-classic-hardcoded high-score recorder.
diff --git a/src/save_game.py b/src/save_game.py
index 695018d..4977034 100644
--- a/src/save_game.py
+++ b/src/save_game.py
@@ -2,7 +2,7 @@

 serialize_game reads live state through attributes only (never through
 mutating getters), rejects mid-gesture boundaries, and returns a strict
-schema-v1 document; save_game writes its canonical ASCII bytes through a
+schema-v2 document (v2 adds the map identity; GM-09f); save_game writes its canonical ASCII bytes through a
 save-local mkstemp -> fsync -> os.replace atomic writer, so a failed
 save leaves the destination untouched and no temporary file behind.
 """
@@ -15,7 +15,7 @@ from pathlib import Path as FilesystemPath
 from typing import Any

 from recursive_checkpoint_schema import safe_checkpoint_value
-from save_load import deserialize_game, load_game
+from save_load import _require_legal_map_state, deserialize_game, load_game
 from save_schema import (
     SAVE_RULES_VERSION,
     SAVE_SCHEMA_VERSION,
@@ -27,26 +27,39 @@ from save_schema import (
 __all__ = ["serialize_game", "save_game", "deserialize_game", "load_game"]


-def _require_classic_map(mediator: Any) -> None:
-    # Fail-closed map guard (GM-09a, hardened GM-09b): the v1 save schema carries no
-    # map identity, so ONLY the canonical Classic map may be serialized. The check is
-    # STRUCTURAL equality against `maps.CLASSIC` (the frozen MapDefinition compares
-    # every field), not just map_id/version -- a forged `MapDefinition("classic", 1,
-    # rivers=..., spawn_regions=...)` would otherwise pass and be silently written as
-    # plain Classic, then reload wrong. The map/save integration lands in GM-09f;
-    # until then a non-Classic (or forged-Classic-with-terrain) Mediator is rejected.
-    # A Mediator without a map_definition is the default Classic.
-    from maps import CLASSIC
-
+def _require_serializable_map(mediator: Any) -> tuple[str, int]:
+    """GM-09f: the v2 save records only the map IDENTITY (`mapId`/version) and
+    reconstructs terrain from the registry on load, so serialization is fail-closed
+    on two axes and returns the identity to persist.
+
+    (1) STRUCTURAL: the map_definition must EQUAL the registered definition for its
+    own id@version (`resolve_map`, which raises a named error on an unknown id /
+    unsupported version). This rejects a forged/drifted `MapDefinition("classic", 1,
+    rivers=...)` that would otherwise persist as `classic@1` and reload as the real
+    terrain-free CLASSIC -- the GM-09b fail-open, now generalized past `== CLASSIC`.
+    (2) STATE-LEGAL: the live state must be legal under that map (below), so a CLASSIC
+    state relabeled `river@1` -- whose stations sit in the water -- cannot be saved.
+    A Mediator with no map_definition is the default Classic.
+    """
+    from maps import CLASSIC, resolve_map
+
+    # Default to Classic ONLY on a truly absent map_definition (is None) -- never via
+    # `or CLASSIC`, which would silently coerce a FALSEY MapDefinition (e.g. a subclass
+    # with __bool__ -> False) into classic@1 and lose its terrain, the very fail-open
+    # this guard exists to close (review Codex).
     map_def = getattr(mediator, "map_definition", None)
-    if map_def is None or map_def == CLASSIC:
-        return
-    identity = f"{getattr(map_def, 'map_id', '?')!r}@{getattr(map_def, 'map_definition_version', '?')}"
-    raise ValueError(
-        f"cannot serialize map {identity}: the v1 save schema has no map identity, so "
-        "only the canonical classic@1 map is serializable until the map/save "
-        "integration lands (a non-Classic or forged-Classic-with-terrain map is rejected)"
-    )
+    if map_def is None:
+        map_def = CLASSIC
+    registered = resolve_map(map_def.map_id, map_def.map_definition_version)
+    if map_def != registered:
+        raise ValueError(
+            f"cannot serialize map {map_def.map_id!r}@{map_def.map_definition_version}: "
+            "its definition does not match the registered map of that identity "
+            "(forged or drifted terrain); a save records only the map identity and "
+            "reconstructs terrain from the registry on load"
+        )
+    _require_legal_map_state(mediator, map_def)
+    return map_def.map_id, map_def.map_definition_version


 def _require_quiescent(mediator: Any) -> None:
@@ -213,15 +226,18 @@ def _spawn_timer_records(mediator: Any) -> list[list[Any]]:


 def serialize_game(mediator: Any) -> dict[str, Any]:
-    """Capture one strict v1 save document without mutating the Mediator."""
+    """Capture one strict v2 save document (adds the map identity) without mutating
+    the Mediator."""

-    _require_classic_map(mediator)
+    map_id, map_definition_version = _require_serializable_map(mediator)
     _require_quiescent(mediator)
     _require_canonical_fleet(mediator)
     raw = {
         "schemaVersion": SAVE_SCHEMA_VERSION,
         "stateContract": SAVE_STATE_CONTRACT,
         "rulesVersion": SAVE_RULES_VERSION,
+        "mapId": map_id,
+        "mapDefinitionVersion": map_definition_version,
         "timeMs": mediator.time_ms,
         "steps": mediator.steps,
         "gameSpeedMultiplier": mediator.game_speed_multiplier,
diff --git a/src/save_load.py b/src/save_load.py
index 179a44e..c721fa6 100644
--- a/src/save_load.py
+++ b/src/save_load.py
@@ -302,13 +302,48 @@ def _restore_buttons(mediator: Mediator, document: dict[str, Any]) -> None:
             _fail("pathButtons lock state disagrees with the derived lock state")


+def _require_legal_map_state(mediator: Any, map_def: Any) -> None:
+    """Reject a state ILLEGAL under its own map (GM-09f, review Codex): every station
+    (active + pool) must sit on the map's land, and committed river crossings must not
+    exceed the tunnel budget. Tunnel counts are DERIVED (no persisted counter), so this
+    needs no stored field -- it refuses a forged/tampered save that a legitimate game
+    could never reach (e.g. a CLASSIC state relabeled `river@1`, whose stations are in
+    the water). Shared by serialize (pre-save) and deserialize (post-load)."""
+    regions = map_def.spawn_regions
+    if regions:
+        for station in mediator.all_stations:
+            x, y = station.position.left, station.position.top
+            if not any(
+                left <= x <= right and top <= y <= bottom
+                for (left, top, right, bottom) in regions
+            ):
+                raise ValueError(
+                    f"map {map_def.map_id!r}: a station at ({round(x)}, {round(y)}) "
+                    "is not on the map's land"
+                )
+    num_tunnels = getattr(mediator, "num_tunnels", None)
+    if num_tunnels is not None and mediator.consumed_tunnels > num_tunnels:
+        raise ValueError(
+            f"map {map_def.map_id!r}: {mediator.consumed_tunnels} river crossings "
+            f"exceed the map's tunnel budget of {num_tunnels}"
+        )
+
+
 def deserialize_game(document: Any) -> Mediator:
-    """Reconstruct one Mediator from a validated v1 save document."""
+    """Reconstruct one Mediator from a validated v1 or v2 save document (GM-09f)."""
+
+    from maps import resolve_map

     validate_save(document)
     coerced = safe_checkpoint_value(document)
     _require_running_config(coerced)
-    mediator = Mediator(seed=0)
+    # v2 records the map identity; a v1 doc (no map keys) synthesizes classic@1, so the
+    # frozen save-v1.json still loads as CLASSIC. resolve_map fails closed on an unknown
+    # id / unsupported version -- never a silent fallback to Classic.
+    map_definition = resolve_map(
+        coerced.get("mapId", "classic"), coerced.get("mapDefinitionVersion", 1)
+    )
+    mediator = Mediator(seed=0, map_definition=map_definition)
     # Every construction-time draw precedes this overwrite.
     _restore_rng(mediator, coerced["rng"])
     stations_by_id = _restore_stations(mediator, coerced)
@@ -321,6 +356,8 @@ def deserialize_game(document: Any) -> Mediator:
         mediator, coerced, stations_by_id, paths_by_id, passengers_by_id
     )
     _restore_buttons(mediator, coerced)
+    # The reconstructed state must be legal under its own map (rejects a forged save).
+    _require_legal_map_state(mediator, map_definition)
     return mediator


diff --git a/src/save_schema.py b/src/save_schema.py
index de83875..4087f75 100644
--- a/src/save_schema.py
+++ b/src/save_schema.py
@@ -35,8 +35,15 @@ from save_schema_records import (
 )

 SAVE_SCHEMA_VERSION_V1 = 1
-SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V1
-SUPPORTED_SAVE_SCHEMA_VERSIONS = {SAVE_SCHEMA_VERSION_V1}
+# GM-09f: v2 is a strict SUPERSET of v1 -- it adds an additive map identity
+# (`mapId`/`mapDefinitionVersion`) so a non-Classic map (river/delta/lake) can be
+# saved/loaded. A v1 document (no map keys) still loads by synthesizing `classic@1`,
+# so the byte-frozen `save-v1.json` stays valid. New saves are v2. `stateContract`
+# and `rulesVersion` are STABLE across v1/v2 -- only `schemaVersion` and the two map
+# keys change (D-038).
+SAVE_SCHEMA_VERSION_V2 = 2
+SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V2
+SUPPORTED_SAVE_SCHEMA_VERSIONS = {SAVE_SCHEMA_VERSION_V1, SAVE_SCHEMA_VERSION_V2}
 SAVE_STATE_CONTRACT = "mini-metro-save-v1"
 SAVE_RULES_VERSION = "rules-v1"

@@ -50,7 +57,7 @@ _NUMPY_BIT_GENERATOR = "PCG64"
 _PCG64_STATE_BOUND = 2**128
 _UINT32_BOUND = 2**32

-_TOP_LEVEL_KEYS = frozenset(
+_TOP_LEVEL_KEYS_V1 = frozenset(
     """schemaVersion stateContract rulesVersion timeMs steps gameSpeedMultiplier
     isGameOver pauseReasons passengerSpawningStep passengerSpawningIntervalStep
     passengerMaxWaitTimeMs overduePassengerThreshold deliveries lineCredits
@@ -59,22 +66,65 @@ _TOP_LEVEL_KEYS = frozenset(
     stationUnlockMilestones numMetros numCarriages stations passengers paths
     metros travelPlans pathColors pathToColor spawnTimers pathButtons rng""".split()
 )
+# GM-09f: v2 adds exactly the two map-identity keys; the exact-key set is chosen by
+# the document's schemaVersion, so a v1 doc carrying map keys OR a v2 doc missing
+# them both fail closed.
+_MAP_IDENTITY_KEYS = frozenset({"mapId", "mapDefinitionVersion"})
+_TOP_LEVEL_KEYS_V2 = _TOP_LEVEL_KEYS_V1 | _MAP_IDENTITY_KEYS
+
+
+def _top_level_keys_for(version: int) -> frozenset[str]:
+    if version == SAVE_SCHEMA_VERSION_V2:
+        return _TOP_LEVEL_KEYS_V2
+    return _TOP_LEVEL_KEYS_V1
+
+
 _PATH_BUTTON_KEYS = frozenset("isLocked unlockBlinkStartTimeMs".split())
 _RNG_KEYS = frozenset("python numpy".split())
 _NUMPY_RNG_KEYS = frozenset("bit_generator state has_uint32 uinteger".split())
 _NUMPY_RNG_STATE_KEYS = frozenset("state inc".split())


-def _validate_header(document: dict[str, Any]) -> None:
+def _read_schema_version(document: dict[str, Any]) -> int:
+    """Read + validate `schemaVersion` BEFORE the exact-key set is chosen (GM-09f).
+
+    A missing key fails with a named ValueError (never a KeyError from a later
+    exact-key check), a non-exact-int (incl. bool) is rejected by `_int`, and a
+    forward version is rejected -- so the key set is only selected for a supported
+    version."""
+    if "schemaVersion" not in document:
+        _fail("schemaVersion", "is required")
     version = _int(document["schemaVersion"], "schemaVersion")
     if version not in SUPPORTED_SAVE_SCHEMA_VERSIONS:
         _fail("schemaVersion", "is unsupported (forward versions are rejected)")
+    return version
+
+
+def _validate_header(document: dict[str, Any]) -> None:
+    # schemaVersion is validated up front by _read_schema_version; the contract and
+    # rules version are STABLE across v1/v2 (only the additive map keys differ).
     if _string(document["stateContract"], "stateContract") != SAVE_STATE_CONTRACT:
         _fail("stateContract", f"must be {SAVE_STATE_CONTRACT!r}")
     if _string(document["rulesVersion"], "rulesVersion") != SAVE_RULES_VERSION:
         _fail("rulesVersion", f"must be {SAVE_RULES_VERSION!r}")


+def _validate_map_identity(document: dict[str, Any]) -> None:
+    """Validate the v2 map-identity scalars (GM-09f): a non-empty ASCII `mapId` with no
+    whitespace + a positive non-bool `mapDefinitionVersion`. Well-typed but UNKNOWN ids
+    are deferred to `resolve_map` at load (fail-closed there); this pins the SHAPE, a
+    true mirror of `rl.manifest_schema._validate_map_identity` (registry ids are ASCII
+    and whitespace-free, so this only rejects a hand-forged doc -- D-038)."""
+    map_id = _string(document["mapId"], "mapId")
+    if not map_id:
+        _fail("mapId", "must be a non-empty string")
+    if not map_id.isascii():
+        _fail("mapId", "must be ASCII")
+    if any(character.isspace() for character in map_id):
+        _fail("mapId", "must not contain whitespace")
+    _positive_int(document["mapDefinitionVersion"], "mapDefinitionVersion")
+
+
 def _validate_scalars(document: dict[str, Any]) -> None:
     _nonnegative_int(document["timeMs"], "timeMs")
     _nonnegative_int(document["steps"], "steps")
@@ -221,8 +271,13 @@ def validate_save(document: Any) -> None:
         coerced = safe_checkpoint_value(document)
     except TypeError as error:
         raise ValueError(f"save document holds unsupported values: {error}") from error
-    _exact_keys(coerced, _TOP_LEVEL_KEYS, "document")
+    # GM-09f two-phase: read + support-check the version, THEN choose the version-aware
+    # exact-key set, so a v1 doc carrying map keys and a v2 doc missing them both fail.
+    version = _read_schema_version(coerced)
+    _exact_keys(coerced, _top_level_keys_for(version), "document")
     _validate_header(coerced)
+    if version == SAVE_SCHEMA_VERSION_V2:
+        _validate_map_identity(coerced)
     _validate_scalars(coerced)
     _validate_progression(coerced)
     registry: set[str] = set()
diff --git a/test/test_gm07b_save_determinism.py b/test/test_gm07b_save_determinism.py
index 78a7f64..e50e5f0 100644
--- a/test/test_gm07b_save_determinism.py
+++ b/test/test_gm07b_save_determinism.py
@@ -24,6 +24,11 @@ from recursive_checkpoint import canonical_checkpoint
 REPO_ROOT = Path(__file__).resolve().parents[1]
 SRC_ROOT = REPO_ROOT / "src"
 FIXTURE_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v1.json"
+# GM-09f: the DETERMINISTIC v1->v2 upgrade of save-v1.json -- identical bytes except
+# schemaVersion 2 + the sorted-inserted map identity (classic@1). A v1 save now
+# re-saves as exactly these bytes (the upgrade is pinned), and this v2 fixture is
+# self-idempotent on re-save.
+FIXTURE_V2_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v2-classic.json"
 SAVE_GAME_MODULE = "save_game"
 SAVE_SCHEMA_MODULE = "save_schema"
 # Modules only `main` may import: the save/load stack plus the main-owned
@@ -49,6 +54,11 @@ EXPECTED_SAVE_V1_BYTE_LENGTH: int | None = 15442
 EXPECTED_SAVE_V1_SHA256: str | None = (
     "d34736a6dfe1023e3ce9a9c9a9d2f9428a1d6e2c696d83fb31838ae22deacd1e"
 )
+# GM-09f: the frozen v2-classic upgrade bytes (save-v1.json + header-only delta).
+EXPECTED_SAVE_V2_BYTE_LENGTH: int | None = 15485
+EXPECTED_SAVE_V2_SHA256: str | None = (
+    "60f2bc16c39610b8822288ebf08eea214cb2d0f54c9ac0208113a0892badbd84"
+)

 _WORKER = """\
 import hashlib
@@ -252,7 +262,6 @@ class TestGM07bFreshProcessIdentity(unittest.TestCase):
         load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
         environment_one = {**os.environ, "PYTHONHASHSEED": "1"}
         environment_two = {**os.environ, "PYTHONHASHSEED": "2"}
-        fixture_payload = FIXTURE_PATH.read_bytes()
         with tempfile.TemporaryDirectory() as directory:
             worker = Path(directory) / "gm07b_worker.py"
             worker.write_text(
@@ -269,7 +278,10 @@ class TestGM07bFreshProcessIdentity(unittest.TestCase):
             )
             self.assertEqual(first_save, second_save)
             self.assertEqual(save_a.read_bytes(), save_b.read_bytes())
-            self.assertEqual(save_a.read_bytes(), fixture_payload)
+            # GM-09f: re-saving the frozen v1 save UPGRADES it to v2 deterministically,
+            # so both hash-seed workers emit exactly the frozen save-v2-classic bytes
+            # (hash-seed independence proven against the pinned upgrade, not v1).
+            self.assertEqual(save_a.read_bytes(), FIXTURE_V2_PATH.read_bytes())

             first_replay = self._run_worker(worker, "replay", save_a, environment_one)
             second_replay = self._run_worker(worker, "replay", save_a, environment_two)
@@ -342,6 +354,17 @@ class TestGM07bFrozenFixture(unittest.TestCase):
         self.assertEqual(len(payload), EXPECTED_SAVE_V1_BYTE_LENGTH)
         self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V1_SHA256)

+    def test_frozen_save_v2_classic_fixture_bytes_are_pinned(self):
+        # GM-09f: the v2-classic upgrade fixture is byte-frozen (LF, no CR), so the
+        # v1->v2 upgrade the idempotence/cross-process tests pin can never silently
+        # drift.
+        self.assertTrue(FIXTURE_V2_PATH.exists(), "save-v2-classic.json is missing")
+        payload = FIXTURE_V2_PATH.read_bytes()
+        self.assertNotIn(b"\r", payload)
+        self.assertTrue(payload.endswith(b"\n"))
+        self.assertEqual(len(payload), EXPECTED_SAVE_V2_BYTE_LENGTH)
+        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V2_SHA256)
+
     def test_frozen_fixture_matches_the_freeze_recipe_and_loads(self):
         self.assertTrue(
             FIXTURE_PATH.exists(),
@@ -360,9 +383,15 @@ class TestGM07bFrozenFixture(unittest.TestCase):
         self.assertEqual(loaded.time_ms, 2_000)
         self.assertEqual(len(loaded.paths), 1)
         self.assertEqual(len(loaded.metros[0].carriages), 1)
-        # Load -> re-save byte idempotence pins the serializer against the
-        # frozen bytes without demanding deterministic shortuuid identities.
-        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), payload)
+        # GM-09f: loading the frozen v1 save and re-saving it now UPGRADES it to v2 --
+        # a deterministic header-only transform -- so the re-save equals the frozen
+        # save-v2-classic.json byte-for-byte (the upgrade is pinned), and that v2
+        # fixture is self-idempotent on re-save.
+        v2_payload = FIXTURE_V2_PATH.read_bytes()
+        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), v2_payload)
+        self.assertEqual(
+            canonical_save_bytes(serialize_game(load_game(FIXTURE_V2_PATH))), v2_payload
+        )
         # The freeze recipe regenerates the same STATE modulo entity IDs:
         # compare through the UUID-free checkpoint oracle instead of bytes.
         regenerated = deserialize_game(json.loads(_fixture_bytes(self)))
diff --git a/test/test_gm07b_save_schema.py b/test/test_gm07b_save_schema.py
index 1800b46..3d581b9 100644
--- a/test/test_gm07b_save_schema.py
+++ b/test/test_gm07b_save_schema.py
@@ -22,8 +22,10 @@ SAVE_GAME_MODULE = "save_game"
 UNKNOWN_STATION_ID = "Station-" + "2" * 22 + "-ShapeType.RECT"
 UNKNOWN_PASSENGER_ID = "Passenger-" + "2" * 22
 UNKNOWN_PATH_ID = "Path-" + "2" * 22
+# v2 (GM-09f): a freshly serialized document adds the additive map identity.
 TOP_LEVEL_KEYS = frozenset(
-    """schemaVersion stateContract rulesVersion timeMs steps gameSpeedMultiplier
+    """schemaVersion stateContract rulesVersion mapId mapDefinitionVersion timeMs
+    steps gameSpeedMultiplier
     isGameOver pauseReasons passengerSpawningStep passengerSpawningIntervalStep
     passengerMaxWaitTimeMs overduePassengerThreshold deliveries lineCredits
     purchasedNumPaths unlockedNumPaths unlockedNumStations numPaths numStations
@@ -153,17 +155,22 @@ class TestGM07bSaveSchemaVersioning(unittest.TestCase):
         schema = _module(self, SAVE_SCHEMA_MODULE)
         for name, expected in (
             ("SAVE_SCHEMA_VERSION_V1", 1),
-            ("SAVE_SCHEMA_VERSION", 1),
-            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1}),
+            ("SAVE_SCHEMA_VERSION_V2", 2),
+            ("SAVE_SCHEMA_VERSION", 2),
+            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1, 2}),
+            # stateContract + rulesVersion are STABLE across v1/v2 (GM-09f).
             ("SAVE_STATE_CONTRACT", "mini-metro-save-v1"),
             ("SAVE_RULES_VERSION", "rules-v1"),
         ):
             self.assertEqual(getattr(schema, name, None), expected, name)
         validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
         _, document = _document(self)
-        self.assertEqual(document["schemaVersion"], 1)
+        self.assertEqual(document["schemaVersion"], 2)
         self.assertEqual(document["stateContract"], "mini-metro-save-v1")
         self.assertEqual(document["rulesVersion"], "rules-v1")
+        # A freshly serialized game is v2 and carries the map identity (classic@1).
+        self.assertEqual(document["mapId"], "classic")
+        self.assertEqual(document["mapDefinitionVersion"], 1)
         self.assertIsNone(validate_save(document))

     def test_schema_version_and_pinned_literal_strictness(self):
@@ -172,11 +179,23 @@ class TestGM07bSaveSchemaVersioning(unittest.TestCase):
         mutations = {
             "bool-true schemaVersion": _setter((), "schemaVersion", True),
             "bool-false schemaVersion": _setter((), "schemaVersion", False),
-            "forward schemaVersion": _setter((), "schemaVersion", 2),
+            # 2 is now SUPPORTED (v2); 3 is the forward version that must be rejected.
+            "forward schemaVersion": _setter((), "schemaVersion", 3),
             "zero schemaVersion": _setter((), "schemaVersion", 0),
             "string schemaVersion": _setter((), "schemaVersion", "1"),
             "float schemaVersion": _setter((), "schemaVersion", 1.0),
             "null schemaVersion": _setter((), "schemaVersion", None),
+            "list schemaVersion": _setter((), "schemaVersion", [2]),
+            # GM-09f version-aware keys: a v2 doc (this one) DOWNGRADED to v1 still
+            # carries the map keys, which the v1 exact-key set forbids -> rejected.
+            "v1 header with v2 map keys": _setter((), "schemaVersion", 1),
+            # A well-typed but non-positive / non-string map identity is rejected.
+            "zero mapDefinitionVersion": _setter((), "mapDefinitionVersion", 0),
+            "empty mapId": _setter((), "mapId", ""),
+            "integer mapId": _setter((), "mapId", 1),
+            # GM-09f mirror of rl.manifest_schema: mapId is non-empty ASCII, no whitespace.
+            "non-ascii mapId": _setter((), "mapId", "rivér"),
+            "whitespace mapId": _setter((), "mapId", "river "),
             "wrong stateContract": _setter((), "stateContract", "mini-metro-save-v2"),
             "empty stateContract": _setter((), "stateContract", ""),
             "null stateContract": _setter((), "stateContract", None),
diff --git a/test/test_gm09a_maps.py b/test/test_gm09a_maps.py
index bcfb255..f59a62f 100644
--- a/test/test_gm09a_maps.py
+++ b/test/test_gm09a_maps.py
@@ -235,10 +235,13 @@ class TestGM09aImportSafety(unittest.TestCase):


 class TestGM09aSaveGuard(unittest.TestCase):
-    def test_serialize_rejects_a_non_classic_map(self):
-        # Fail-closed (review Codex-7): until the save schema carries map identity,
-        # a save-capable Mediator must be serializable ONLY as classic@1, so a
-        # future non-Classic map can never be silently written as Classic.
+    def test_serialize_rejects_a_forged_map_definition(self):
+        # Fail-closed STRUCTURAL guard (GM-09a; GM-09f generalized it past `== CLASSIC`
+        # to `== resolve_map(id, version)`): a save records only the map IDENTITY and
+        # reconstructs terrain from the registry on load, so a forged/drifted
+        # definition -- here `river@1` carrying CLASSIC's palette and NO river terrain
+        # -- must be rejected, or it would persist as `river@1` and silently reload as
+        # the real RIVER. (A REGISTERED river/delta/lake now serializes; see GM-09b/d/e.)
         from save_game import serialize_game

         map_def_cls = _sym(self, "MapDefinition")
@@ -246,7 +249,7 @@ class TestGM09aSaveGuard(unittest.TestCase):
         m = Mediator(seed=0)
         # Classic serializes fine.
         serialize_game(m)
-        # A non-Classic definition must be rejected with a clear, named error.
+        # A forged (registry-mismatched) definition must be rejected with a named error.
         m.map_definition = map_def_cls(
             map_id="river",
             map_definition_version=1,
diff --git a/test/test_gm09b_river.py b/test/test_gm09b_river.py
index aeea87b..8c34517 100644
--- a/test/test_gm09b_river.py
+++ b/test/test_gm09b_river.py
@@ -172,13 +172,21 @@ class TestGM09bSaveGuardStructural(unittest.TestCase):
         with self.assertRaises(Exception):
             serialize_game(m)

-    def test_river_map_is_not_serializable(self):
+    def test_river_map_round_trips_through_a_v2_save(self):
+        # GM-09f: a registered RIVER map now serializes (v2 records the map identity)
+        # and reloads with its map preserved -- the forged-classic guard above stays
+        # green because it checks STRUCTURAL equality to the registered definition.
         from mediator import Mediator
         from save_game import serialize_game
+        from save_load import deserialize_game
+        from save_schema import validate_save

-        m = Mediator(seed=0, map_definition=_sym(self, "RIVER"))
-        with self.assertRaises(Exception):
-            serialize_game(m)
+        river = _sym(self, "RIVER")
+        document = serialize_game(Mediator(seed=0, map_definition=river))
+        self.assertEqual(document["mapId"], "river")
+        self.assertEqual(document["mapDefinitionVersion"], 1)
+        validate_save(document)
+        self.assertEqual(deserialize_game(document).map_definition, river)


 class TestGM09bTerrainRenderer(unittest.TestCase):
diff --git a/test/test_gm09d_delta.py b/test/test_gm09d_delta.py
index ed7e086..d026e2b 100644
--- a/test/test_gm09d_delta.py
+++ b/test/test_gm09d_delta.py
@@ -214,14 +214,17 @@ class TestGM09dClassicRiverUnaffected(unittest.TestCase):


 class TestGM09dSaveGuardAndRender(unittest.TestCase):
-    def test_delta_map_is_not_serializable(self):
+    def test_delta_map_round_trips_through_a_v2_save(self):
+        # GM-09f: a registered DELTA map now serializes (v2 records the map identity)
+        # and reloads with its map preserved.
         from save_game import serialize_game
+        from save_load import deserialize_game
+        from save_schema import validate_save

-        # The fail-closed guard must raise a ValueError naming the exact rejected
-        # map identity (delta@1) -- not merely any Exception, which a stray
-        # RuntimeError would also satisfy (review Codex).
-        with self.assertRaisesRegex(ValueError, r"delta'@1"):
-            serialize_game(Mediator(seed=0, map_definition=DELTA))
+        document = serialize_game(Mediator(seed=0, map_definition=DELTA))
+        self.assertEqual(document["mapId"], "delta")
+        validate_save(document)
+        self.assertEqual(deserialize_game(document).map_definition, DELTA)

     def test_terrain_paints_both_channels_and_not_the_mid_bank(self):
         # Assert BOTH channels are water and the mid bank is not -- a regression that
diff --git a/test/test_gm09e_lake.py b/test/test_gm09e_lake.py
index eeb35b5..d596ada 100644
--- a/test/test_gm09e_lake.py
+++ b/test/test_gm09e_lake.py
@@ -235,11 +235,17 @@ class TestGM09eOtherMapsUnaffected(unittest.TestCase):


 class TestGM09eSaveGuardAndRender(unittest.TestCase):
-    def test_lake_map_is_not_serializable(self):
+    def test_lake_map_round_trips_through_a_v2_save(self):
+        # GM-09f: a registered LAKE map now serializes (v2 records the map identity)
+        # and reloads with its map preserved.
         from save_game import serialize_game
+        from save_load import deserialize_game
+        from save_schema import validate_save

-        with self.assertRaisesRegex(ValueError, r"lake'@1"):
-            serialize_game(Mediator(seed=0, map_definition=LAKE))
+        document = serialize_game(Mediator(seed=0, map_definition=LAKE))
+        self.assertEqual(document["mapId"], "lake")
+        validate_save(document)
+        self.assertEqual(deserialize_game(document).map_definition, LAKE)

     def test_terrain_paints_the_lake_interior_but_not_the_dry_corners(self):
         from rendering.terrain_renderer import RIVER_COLOR, draw_terrain
```

## New test file: test/test_gm09f_save_map.py
```python
"""GM-09f contract: the save-schema v2 map field (D-038).

A v2 save records the map IDENTITY (`mapId`/`mapDefinitionVersion`) and reconstructs
terrain from the registry on load, so a non-Classic game round-trips. A v1 document
(no map keys) still loads by synthesizing `classic@1`, keeping `save-v1.json` valid.
Serialization + load are fail-closed on TWO axes: the map_definition must EQUAL its
registered definition (a forged/drifted map is rejected), and the state must be LEGAL
under that map (stations on land, crossings within budget). Tunnel counts stay derived.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from maps import CLASSIC, DELTA, LAKE, RIVER, MapDefinition
from mediator import Mediator
from save_game import serialize_game
from save_load import deserialize_game
from save_schema import canonical_save_bytes, validate_save

pygame.init()


def _river_crossing_mediator():
    """A RIVER game with one committed river-crossing line (quiescent, canonical).

    Uses the default single unlocked path -- no override -- so the serialized
    progression invariants (unlockedNumPaths vs purchasedNumPaths) stay consistent.
    """
    m = Mediator(seed=0, map_definition=RIVER)
    # seed=0 RIVER: station 2 = left bank, 0 = right bank -> a crossing line.
    m.create_path_from_station_indices([2, 0])
    return m


def _as_v1(document):
    """A v1 document: drop the v2 map keys and set schemaVersion 1 (old save shape)."""
    v1 = copy.deepcopy(document)
    v1["schemaVersion"] = 1
    del v1["mapId"]
    del v1["mapDefinitionVersion"]
    return v1


class TestGM09fRoundTrip(unittest.TestCase):
    def test_v2_round_trip_preserves_each_map(self):
        for name, map_def in (
            ("classic", CLASSIC),
            ("river", RIVER),
            ("delta", DELTA),
            ("lake", LAKE),
        ):
            document = serialize_game(Mediator(seed=0, map_definition=map_def))
            self.assertEqual(document["schemaVersion"], 2)
            self.assertEqual(document["mapId"], name)
            self.assertEqual(document["mapDefinitionVersion"], 1)
            validate_save(document)
            self.assertEqual(deserialize_game(document).map_definition, map_def)

    def test_default_mediator_serializes_as_classic(self):
        document = serialize_game(Mediator(seed=0))  # no map_definition -> CLASSIC
        self.assertEqual(document["mapId"], "classic")
        self.assertEqual(deserialize_game(document).map_definition, CLASSIC)

    def test_v2_canonical_bytes_are_idempotent(self):
        first = canonical_save_bytes(
            serialize_game(Mediator(seed=0, map_definition=DELTA))
        )
        again = canonical_save_bytes(
            serialize_game(deserialize_game(json.loads(first)))
        )
        self.assertEqual(first, again)


class TestGM09fBackwardCompat(unittest.TestCase):
    def test_a_v1_document_loads_as_classic(self):
        # A v1 save (no map identity) synthesizes classic@1 -- the old load behavior.
        v1 = _as_v1(serialize_game(Mediator(seed=0)))
        validate_save(v1)
        self.assertEqual(deserialize_game(v1).map_definition, CLASSIC)

    def test_v1_document_with_map_keys_is_rejected(self):
        forged = serialize_game(Mediator(seed=0))
        forged["schemaVersion"] = 1  # v1 header, but keeps the v2 map keys
        with self.assertRaises(ValueError):
            validate_save(forged)

    def test_v2_document_without_map_keys_is_rejected(self):
        missing = serialize_game(Mediator(seed=0))
        del missing["mapId"]  # v2 header but missing a required map key
        with self.assertRaises(ValueError):
            validate_save(missing)


class TestGM09fFailClosedLoad(unittest.TestCase):
    def test_load_rejects_an_unknown_map_id(self):
        document = serialize_game(Mediator(seed=0))
        document["mapId"] = "atlantis"
        with self.assertRaisesRegex(ValueError, "atlantis"):
            deserialize_game(document)

    def test_load_rejects_an_unsupported_map_version(self):
        document = serialize_game(Mediator(seed=0))
        document["mapDefinitionVersion"] = 99
        with self.assertRaisesRegex(ValueError, "99"):
            deserialize_game(document)


class TestGM09fMapIdentityShape(unittest.TestCase):
    """`validate_save` pins the v2 `mapId` SHAPE -- a non-empty ASCII string with no
    whitespace, a true mirror of `rl.manifest_schema._validate_map_identity`. Registry
    ids already satisfy this, so these guard only hand-forged documents (review: harness
    + Codex both flagged the missing ASCII/whitespace check against D-038's contract)."""

    def _document_with_map_id(self, map_id):
        document = serialize_game(Mediator(seed=0))
        document["mapId"] = map_id
        return document

    def test_validate_rejects_a_non_ascii_map_id(self):
        with self.assertRaisesRegex(ValueError, "ASCII"):
            validate_save(self._document_with_map_id("rivér"))

    def test_validate_rejects_a_whitespace_bearing_map_id(self):
        with self.assertRaisesRegex(ValueError, "whitespace"):
            validate_save(self._document_with_map_id("river "))

    def test_validate_rejects_an_empty_map_id(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            validate_save(self._document_with_map_id(""))

    def test_validate_rejects_a_non_string_map_id(self):
        with self.assertRaisesRegex(ValueError, "must be a string"):
            validate_save(self._document_with_map_id(123))


class TestGM09fStructuralGuard(unittest.TestCase):
    def _forge(self, map_id, **overrides):
        base = dict(
            map_id=map_id,
            map_definition_version=1,
            shape_types=CLASSIC.shape_types,
            unique_shape_types=CLASSIC.unique_shape_types,
            unique_spawn_start_index=CLASSIC.unique_spawn_start_index,
            unique_spawn_chance=CLASSIC.unique_spawn_chance,
        )
        base.update(overrides)
        return MapDefinition(**base)

    def test_serialize_rejects_a_forged_classic_with_terrain(self):
        # A classic id carrying terrain would persist as classic@1 and reload as the
        # real terrain-free CLASSIC -- the structural guard rejects it.
        m = Mediator(seed=0)
        m.map_definition = self._forge("classic", rivers=((5.0, 0.0, 6.0, 10.0),))
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_forged_river_without_terrain(self):
        # A river id WITHOUT the real river terrain: rejected (would reload as real RIVER).
        m = Mediator(seed=0)
        m.map_definition = self._forge("river")  # no rivers/spawn_regions
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_forged_delta_without_terrain(self):
        # Same guard for the delta id (would reload as the real two-channel DELTA).
        m = Mediator(seed=0)
        m.map_definition = self._forge("delta")  # no channels/spawn_regions
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_forged_lake_without_terrain(self):
        # Same guard for the lake id (would reload as the real bounded-lake LAKE).
        m = Mediator(seed=0)
        m.map_definition = self._forge("lake")  # no lake rect/spawn_regions
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_falsey_map_definition(self):
        # A FALSEY MapDefinition (a subclass whose __bool__ is False) carrying classic@1
        # identity must NOT be silently coerced to CLASSIC by an `or CLASSIC` default:
        # it is not the registered CLASSIC object, so the structural guard rejects it.
        # Regression for the fail-open the `is None` default closes (review Codex).
        class _FalseyMap(MapDefinition):
            def __bool__(self) -> bool:
                return False

        falsey = _FalseyMap(
            **{f.name: getattr(CLASSIC, f.name) for f in dataclasses.fields(CLASSIC)}
        )
        self.assertFalse(bool(falsey))  # the trap: truthiness is False
        self.assertNotEqual(falsey, CLASSIC)  # but it is NOT the registered CLASSIC
        m = Mediator(seed=0)
        m.map_definition = falsey
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)


class TestGM09fStateLegality(unittest.TestCase):
    def test_serialize_rejects_a_state_illegal_under_its_map(self):
        # CLASSIC stations relabeled river@1 sit in the water -> rejected on serialize.
        m = Mediator(seed=0)
        m.map_definition = RIVER
        with self.assertRaisesRegex(ValueError, "not on the map's land"):
            serialize_game(m)

    def test_load_rejects_a_forged_off_land_document(self):
        # A hand-forged v2 doc: a CLASSIC game's state relabeled river@1. It validates
        # structurally but its stations are in the water -> rejected on LOAD.
        document = serialize_game(Mediator(seed=0))
        document["mapId"] = "river"
        validate_save(document)  # schema-valid (well-typed identity)
        with self.assertRaisesRegex(ValueError, "not on the map's land"):
            deserialize_game(document)

    def test_legality_gate_refuses_an_over_budget_reconstruction(self):
        # The creation gate (within_tunnel_budget) means normal play can never build an
        # over-budget state, so this drives the load-side defense-in-depth branch directly
        # (as the impl review verified): consumed crossings above the map budget are
        # refused after reconstruction, a corrupt-doc safety net. RIVER has spawn_regions
        # so the (empty) station pool is scanned first, then the budget check fires.
        from save_load import _require_legal_map_state

        over_budget = SimpleNamespace(
            all_stations=[], num_tunnels=RIVER.tunnel_budget, consumed_tunnels=99
        )
        with self.assertRaisesRegex(ValueError, "exceed the map's tunnel budget"):
            _require_legal_map_state(over_budget, RIVER)


class TestGM09fDerivedTunnelState(unittest.TestCase):
    def test_a_river_crossing_survives_the_round_trip(self):
        # Tunnel counts are DERIVED, not persisted: a saved river-crossing game reloads
        # with the same consumed/available, reconstructed from map_definition + paths.
        mediator = _river_crossing_mediator()
        self.assertEqual(mediator.consumed_tunnels, 1)
        document = serialize_game(mediator)
        loaded = deserialize_game(document)
        self.assertEqual(loaded.map_definition, RIVER)
        self.assertEqual(loaded.consumed_tunnels, 1)
        self.assertEqual(loaded.available_tunnels, 2)


if __name__ == "__main__":
    unittest.main()
```

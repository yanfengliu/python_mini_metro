# GM-09b PLAN — Adversarial Review (harness lane, verbatim), verdict NOT CLEAN

## Q1 SCOPE DEFERRAL (save-v2 to GM-09f): SOUND
No river-capable Mediator reaches serialize_game in GM-09b. Only save_game caller is main.py:146 (write_autosave); controller.mediator built only via build_game (Mediator()), build_from (loaded classic), build_tutorial (Mediator(seed=…)); app_controller has no map_definition/save_game ref; the only river-capable construction is player_env.py:142, under src/rl/ which the isolation scan forbids from importing save_game. Guard fail-closed for a canonical river; write_autosave swallows to None (keeps prior autosave). D-032/D-033-aligned.

## FINDING A — MAJOR: empty-tuple vs None sentinel
CLASSIC.spawn_regions == () not None. If the guard is `if spawn_regions is None:`, CLASSIC's () slips into the rejection branch (inside zero regions always False → infinite hang or extra draws moving _CONSTRUCT_FP + save-v1). Fix: falsy sentinel `if not spawn_regions:`. Test CLASSIC passes () with unmoved fingerprint.

## FINDING B — MINOR: get_random_position bounds param unnecessary + risky
The rejection design needs NO change to get_random_position (its 2 draws are pinned). Adding a bounds param risks float-order/rounding drift shifting a CLASSIC pixel. Fix: leave get_random_position byte-identical; rejection in the caller.

## FINDING C — MINOR: conflates two spawn mechanisms
Commit to one (full-screen rejection); write down the per-station RNG draw count.

## FINDING D — MINOR: get_random_station missing from the chain
get_random_stations → get_random_station → get_station_spawn_position. Thread spawn_regions through get_random_station too.

## FINDING E — MINOR (determinism-ranked): rejection loop unbounded
Cap attempts + named error on exhaustion + assert padded_rect ∩ (∪ spawn_regions) has positive area at construction.

## Q4 IMPORT-SAFETY: SOUND (tuples). NOTE: geometry.Polygon.contains is BROKEN — imports shapely at module top, references unset self.position (AttributeError), dead code, mints a uuid (trips headless-render guard). Use a plain point-in-rect predicate.

## FINDING F — MAJOR: hook location
The RL observation path calls GameRenderer.draw DIRECTLY (player_env.py:279-280), bypassing main.run_game. A main-only draw_terrain → agent training on --map river never sees the river. Fix: draw_terrain at the TOP of GameRenderer.draw (before network_renderer.draw:97), getattr(state,"map_definition",None) → None paints nothing. CLASSIC no-op (empty rivers) keeps byte-identity.

## Q6 GEOMETRY: SOUND — axis-aligned rect banks + rect river → point-in-rect trivial, deterministic, no shapely.

## FINDING G — MINOR: docs surfaces omitted — ARCHITECTURE (terrain_renderer, data-flow, new fields), GAME_RULES (river no-spawn/render rule), PROGRESS.
## FINDING H — NIT: MapDefinition new fields need =() defaults + __post_init__ tuple-coercion.

## Verdict: NOT CLEAN — fix A (falsy sentinel) + F (GameRenderer.draw hook); fold B/C/D/E/G/H + avoid broken Polygon.contains.

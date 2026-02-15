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

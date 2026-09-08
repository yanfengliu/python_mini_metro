# Smooth rendering design

## Decision

Keep Python 3.13 and pygame-ce. Separate logical route geometry from visual lane layout, make drawing observational, add a cached antialiased network renderer, and drive interactive simulation through a fixed 60 Hz accumulator with input handled before simulation. This renderer remains the canonical pixel source for the later Gymnasium environment.

## Boundaries

- `Path.segments` stays logical centerline simulation geometry and preserves the existing alternating path/padding sequence and metro indices. Topology mutation rebuilds it explicitly; future movable-station content must call the same geometry-revision API.
- `rendering.layout` derives immutable centered visual lanes and metro projections without allocating gameplay entities or UUIDs.
- `rendering.network_renderer.NetworkRenderer` caches static route pixels by a value signature, while `rendering.game_renderer.GameRenderer` draws dynamic temporary lines, entities, UI, and overlays above them.
- Entity drawing receives explicit visual positions and restores temporary rotation; it does not change passenger positions, shape hitboxes, route geometry, or snap-blip lists. Expired visual effects are pruned by the simulation update.
- `Mediator.prepare_layout()` owns station, path/speed button, and game-over hitboxes before first-frame input. `Mediator.render()` consumes prepared state.
- `FixedStepClock` converts wall time into a globally phased deterministic `17, 17, 16` millisecond sequence, clamps stalls, caps catch-up work, drops excess backlog to a sub-step remainder, and exposes interpolation alpha/dropped-time telemetry.
- `GameSession` is the shared raw-event/fixed-step driver used by the window and later by the pixel Gymnasium environment. The legacy high-level `MiniMetroEnv.step(action, dt_ms)` contract remains unchanged.
- `MetroInterpolator` keeps previous/current visual metro poses outside simulation and blends them without entering checkpoints. Zero-length logical padding preserves its existing transition tick; interpolation alone bridges visual lane changes.
- Fonts and other pygame resources are lazy and renderer-owned, use pygame's bundled default font, work on software surfaces without `display.set_mode`, and are never created by state-only sessions.

## Visual direction

Use a warm off-white background, antialiased line strokes with a subtle neutral halo and round caps/joins, symmetric lanes for every active-line count, and outlined line-colored metros. Preserve the existing minimal geometric station/passenger language.

## Invariants

- Rendering the same state repeatedly produces identical pixels and does not change either the recursive canonical checkpoint or an explicit render-relevant mutable-state snapshot.
- GUI and headless play share logical route geometry.
- Reversing a station pair preserves its lane side.
- New content invalidates render caches through value signatures containing ordered station IDs/positions, loop state, color, lane slot, surface size, and style revision.
- Fixed-step pacing makes integration consistent without changing logical segment timing, public environment actions, or balance constants.
- Each renderer owns one bounded network cache; resets/environments never share surfaces.
- Layering stays routes and temporary route, stations/passengers/effects, metros/onboard passengers, UI, then game-over overlay.

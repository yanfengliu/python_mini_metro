# GM-01b implementation scope

## Intent

Make the player-visible objective match the canonical delivery objective without changing the RL action/task protocol or the reconstructable terminal-metrics-v1 contract. Correct the stale passenger-spawn cadence documentation and pin the live behavior with focused tests.

## Runtime and tests

- `src/rendering/game_renderer.py` now renders ordered `Passengers Delivered` and `Line Credits` HUD rows, presents deliveries first on game over, retains canonical-first legacy fallbacks, and flows overlay text above the existing prepared buttons without moving hitboxes.
- `src/config.py` names HUD and overlay spacing explicitly while retaining the old score display constants as compatibility aliases; the private station-unlock accumulator now uses delivery terminology.
- `test/test_game_renderer.py` begins from divergent canonical and legacy sentinels, pins exact labels and order, checks canonical precedence and legacy fallback, proves each metric changes pixels, and verifies horizontal/vertical fit at 1920x1080 and 800x600.
- `test/test_spawn_cadence.py` pins the 900-step base, inclusive per-station 630-1,170 sampling, sample-once state, first-update attempts at 1x/2x/4x, full-station reset behavior, equal simulated-time cadence, and non-divisible 4x whole-tick quantization.

## Public documentation and visual evidence

- `README.md`, `GAME_RULES.md`, and `ARCHITECTURE.md` distinguish lifetime deliveries from line credits and describe the executable spawn behavior.
- `visual/before-*.png` and `visual/after-*.png` are matching deterministic 1920x1080 captures at seed 42 with 23 deliveries and 4 line credits. The old images label 4 credits as score; the new images show both canonical values and a non-overlapping game-over summary.

## Fingerprint boundary

- Protocol: `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f` before and after.
- Default task: `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d` before and after.
- Environment content: `390a9fbbd60b479b2957f89c99b5c01f699836a0bd2ecf8bc80de01591f50682` before; `feb81d5d64e8304318c54cffc44cc105d6c16e9ef06cbe24c45d9ba3f01958cf` after the final reviewed runtime edits.

Terminal-metrics v1 remains exactly `{deliveries, display_score, seed, simulation_time_ms}`, with legacy `display_score` continuing to serialize remaining line credits.

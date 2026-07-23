# GM-08c empirical seed/sim probe findings (pre-implementation)

Ran headless probes (`SDL_*=dummy`) against the live seeded game to de-risk the plan before coding. These findings REVISE the plan's overload gate and force a sim-freeze design.

## Findings

1. **No-input game-over at 40 s, every seed.** A seeded `Mediator(seed=N)` game with NO player input flips `is_game_over` at ~40.0 s across seeds {1,7,42,123,2024} — the passenger 40 s wait-limit (`passenger_max_wait_time_ms`), not crowd. Max station crowd only reaches **3-4** before that (never 5), so the plan's `max_crowd >= 5` overload gate is **UNREACHABLE**. Wait-time (the warning ring), not crowd count, is the real overload signal.

2. **Post-game-over the sim FREEZES.** After `is_game_over`, passengers stay pinned ([3,3,3] unchanged over +30 s), `is_paused` stays False, nothing spawns or moves. So any tutorial step that needs the sim (deliver, or watching trains) **soft-locks** the moment game-over hits — the player can only Escape.

3. **The renderer paints "Game Over" chrome on `is_game_over`** (`game_renderer.py:158-159` → `_draw_game_over`), which would render under the tutorial overlay.

4. **Seed 42 is uniquely delivery-friendly.** Initial 3 stations by seed: 1=[Cross,Circle,Cross], 7=[Rect,Circle,Rect], 42=[Triangle,Rect,Cross], 123=[Cross,Cross,Triangle], 2024=[Rect,Cross,Rect]. **Only seed 42 has 3 DISTINCT shapes**, so any 2-station line the player draws connects two different shapes and enables deliveries. Chosen `TUTORIAL_SEED = 42`.

## Design consequences (fold into plan v2)

- **Freeze the sim during untimed setup.** `main.run_game` advances 0 (frozen) for TUTORIAL steps that do not need time — draw / reroute / train — so the 40 s clock never runs while a first-timer learns the controls (input still applies; `advance(0)` is the proven TITLE/SETTINGS freeze). The pure tutorial module exposes `step_needs_time(progress)`.
- **Run the sim only for `deliver`**, from fresh (frozen) wait-times, completing on the first delivery well under 40 s, then re-freeze — so game-over is impossible by construction.
- **Overload becomes an ACKNOWLEDGE step** (advance on the next non-Escape input in `_handle_tutorial`), not gated on real overload — a good player never overloads, and forcing it would risk the fatal game-over. It teaches the concept safely while frozen.
- **The TUTORIAL render branch must NOT draw game-over chrome** — either it never occurs (the freeze guarantees it) or, as a belt-and-suspenders, the tutorial renders without the game-over path. Simplest: the freeze guarantees `is_game_over` stays False, so no special suppression is needed; add a test asserting a full tutorial run never flips `is_game_over`.
- `pause` / `speed` are taught while frozen (the control flip — `is_paused`, `game_speed_multiplier` — is still detected); safe and instant.

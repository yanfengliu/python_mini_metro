# GM-07a research — live runtime/screen/pause surface (verbatim synthesis)

Security note: this research subagent reported an injected "cross-repository research directive" in its task stream demanding external cloning and a `gh auth token`-embedded push; it refused, and the incident is recorded in session memory. Nothing external was read or pushed; every claim below is grounded in the local tree.

## Loop ownership (`src/main.py`, 130 lines)

`run_game(max_frames)` at main.py:26 owns: window/game/presentation surfaces, clock, viewport transform, the raw pygame event pump, `restart_requested` orchestration, and restart-by-full-reconstruction (`Mediator()`+`GameRenderer()`+`GameSession()`+`prepare_layout`+`advance(0)`, main.py:90-94, fresh random seed, no `Mediator.reset()`). It delegates simulation to `Mediator`, fixed-step cadence to `GameSession`, composition to `GameRenderer.draw`, and game-over hit-testing to `mediator.handle_game_over_click`. There is no title/menu/pause-menu/settings state; the loop assumes a live playing Mediator. `pygame.display.*`/`pygame.init` occur only in main.py:27,29,117.

## Pause ownership

`Mediator.is_paused` is a plain bool attribute (mediator.py:150); `set_paused` facade at 582-583 delegates to `_input.set_paused` (input_coordinator.py:398-399). Writers: Space KEY_UP toggle writes the raw bool directly (input_coordinator.py:366 — bypasses `set_paused`); `apply_speed_action("pause")` → set_paused(True) (406); any speed selection implicitly unpauses (414); structured `pause`/`resume` (491,494); direct test writes. Readers: `transition_active = not is_paused and not is_game_over` (mediator.py:625) with GM-06d reconcile unconditional (628) and drain+settle transition-gated (629-637); GameSession pause gate resets the wall clock so no catch-up backlog accrues (game_session.py:54,66,76,87); PassengerFlow early-return (passenger_flow.py:148); settle pause gate (fleet_management.py:405); speed-button active states (input_coordinator.py:416-427); observation `is_paused` (env.py:236); checkpoint twice (recursive_checkpoint.py:147,396); privileged oracle (rl/privileged_oracle.py:29,79); pause oracles (recursive_playtest.py:170-207).

## Game-over today

Flag flips inside `update_waiting_and_game_over` (mediator.py:715-719) with transient-input clear on the edge. Click routing via `handle_game_over_click` (mediator.py:424-425 → input_coordinator.py:159-172) against rects built in `prepare_layout` (input_coordinator.py:48-61). Loop branch main.py:49-69 (R/Esc/mouse). Overlay renders inside `GameRenderer._draw_game_over` (game_renderer.py:176-177, 429-494). Programmatic reset: `env.reset` builds `Mediator(seed)` (env.py:46-65); `env.step` short-circuits when over (81-84); PlayerPixelEnv mirrors (rl/player_env.py:126-128,174).

## Headless bypass table

`MiniMetroEnv` constructs `Mediator` only, no display; `PlayerPixelEnv` uses off-screen surfaces only (no `set_mode`); `recursive_playtest` and `agent_play` drive `MiniMetroEnv`. An AppController scoped to main.py's loop touches no headless path; the four programmatic entries must keep constructing `Mediator`/`GameSession` directly and never route through a menu gate (PLAN.md:33,182; D-004).

## Checkpoint/replay pause contract

Two bool projections per checkpoint must stay equal and derivable: `structured.is_paused` (recursive_checkpoint.py:147 ← env.py:236) and `progression.is_paused` (:396). `pause`/`resume` are persisted replayable actions at every version (`_LIVE_ONLY_ACTION_TYPES` holds only `cancel_unassignment`, recursive_contract.py:51). Recursive oracles: `paused-time-progression` (recursive_playtest.py:181-184) — paused clock frozen; `paused-state-mutation` (185-195) — a successful pause changes exactly the two bools and nothing else, and a paused noop changes nothing. Therefore pause REASONS must not enter checkpoints/observations in GM-07a (GM-07b owns persisting reasons per PLAN.md:184); `is_paused` must remain readable and writable as a bool.

## Line budgets and coverage

main.py 130, mediator.py 791 (<1000), input_coordinator.py 498, game_session.py 95, game_clock.py 103, env.py 353, recursive_checkpoint.py 497, game_renderer.py 494, passenger_flow.py 494, fleet_management.py 499 — five files sit 1-6 lines under the 500 target; pause-reason logic must not land there. `test_main.py` mocks the display and does NOT cover the game-over/restart branch. Signature pins: `set_paused "(self, paused: 'bool') -> 'None'"` and `apply_action "(self, action: 'object') -> 'bool'"` (test_mediator_input_contract.py:106,110).

## Risks R1-R10

R1 Space bypasses set_paused (raw bool flip — the exact D-010 modal hazard). R2 direct bool writes exist in tests and the toggle; a property must keep a working setter. R3 dual checkpoint projection must stay equal/bool with no new fields absent a schema bump. R4 persisted pause/resume actions and the flips-exactly-the-bool oracle must stay green. R5 signature pins constrain the facade. R6 transition_active must still resolve one effective bool; reconcile stays unconditional, drain+settle stay gated. R7 game-over is loop-inline with renderer-owned overlay; headless envs have no screen concept. R8 loop restart is full reconstruction with a fresh seed; env.reset seeds explicitly; no Mediator.reset(). R9 five files at 494-499 lines. R10 thin loop-state coverage in test_main.py.

## Fingerprint addendum (verified by the parent session directly)

`compute_content_fingerprint` (src/rl/training.py:282-309) hashes every non-`src/rl` file under `src/` (plus player_env/protocol), so new `src/` modules and main/mediator/input edits intentionally advance environment-content identity, exactly as GM-06c/GM-06d did; protocol and task fingerprints remain exact when the low-level protocol is untouched. `compute_training_fingerprint` (training.py:312+) hashes trainer/model code and dependency declarations — GM-07a does not touch those.

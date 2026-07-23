# GM-08c PLAN — Adversarial Review (harness lane, verbatim)

Read the plan and verified every signal against the live `src/`. The step-detection logic is mostly sound, but two independent MAJOR soft-locks make the overload step uncompletable in good play and freeze the time-dependent steps once the seeded game hits its own game-over.

## MAJOR-1 — `is_game_over` freezes the tutorial sim; deliver + overload become permanently uncompletable (soft-lock)
"The tutorial never promotes game over (TUTORIAL != PLAYING)" is true for the SCREEN (`reconcile_game_over` gated at `app_controller.py:148`) but a non-sequitur for the sim: the mediator's `is_game_over` flag still flips and once it does the sim is frozen for the rest of the run.
- `game_session.py:54` — `advance()` short-circuits and resets the clock when `is_game_over`. No ticks ever run again.
- `passenger_flow.py:148` — `increment_time` returns immediately on `is_game_over`; no spawns/movement/deliveries/crowd change.
- `passenger_flow.py:451-463` — game over set when `waiting_over_limit >= overdue_passenger_threshold`. Nothing in the TUTORIAL path resets `is_game_over` (only a fresh Mediator clears it).
Failing scenario: on deliver (4) or overload (5), a stranding/degenerate line strands two passengers; with `overdue_passenger_threshold=2` (`config.py:56`) and `passenger_max_wait_time_ms=40_000` (`config.py:53`), `is_game_over` flips at ~40-55 s, sim freezes, neither predicate can ever fire again. Only exit is Escape. Violates the acceptance and the plan's "no step soft-locks / a pause is always recoverable" (a game-over freeze is NOT recoverable). Also `can_assign` returns False on `is_game_over` (`fleet_management.py:188`).
Fix: keep the sim alive. Given "no Mediator class change," set a per-instance attribute at `build_tutorial` time — e.g. `mediator.overdue_passenger_threshold = 10**9` (per-instance write, not class/config). Own it explicitly as a deviation from "reads the mediator only."

## MAJOR-2 — The overload crowd threshold is not reliably reachable (soft-lock in good play, game-over race in bad play)
`max(len(st.passengers)) >= threshold` — game over is driven by WAIT TIME (`passenger_flow.py:451-463`), independent of crowd, so crowding and game-over are not ordered. Spawn interval 630-1170 steps ≈ 10.5-19.5 s (`config.py:51`, `passenger_flow.py:92-97`); a full station drops new spawns (cap 12, `config.py:27`); a stranded station only accumulates ~3-4 by the ~40-55 s game-over. Any threshold in (4,12] is unreachable before game-over; a low one (2-3) only races game-over in bad play. In GOOD play a single-line single-train (capacity 6, `config.py:69`) keeps `max(len)` at 1-2 → threshold never reached; the coaching ("keep your lines flowing") tells the player to PREVENT the outcome the step requires. Riskiest step; as specified (unspecified threshold, no forcing mechanism) it cannot satisfy "advances when and only when the player performs it."
Fix: (a) redesign as an observational step that auto-advances after the tip shows for N seconds of UNPAUSED play (honest — overload is a consequence to observe), optionally OR-ed with a low crowd threshold; or (b) keep a threshold only if empirically pinned to a small value the seed provably reaches AND combined with MAJOR-1 suppression. Define the numeric value; "an overload-teach threshold" is unspecified.

## MINOR-3 — Speed "changed from baseline" mis-detects when the player already sped up
Keys 1/2/3 → speed 1/2/4 (`input_coordinator.py:367-372`, `mediator.py:449-450`); attribute `game_speed_multiplier` (`mediator.py:153`). Detection correct, no engine-driven change. But deliver(4)/overload(5) make the player wait → they likely press 2/3 before step 7; baseline at step-7 activation is already 2/4, and pressing the same speed is a no-op → step doesn't advance (recoverable). Fix: complete on `game_speed_multiplier != 1`, or "a speed key was pressed since activation."

## MINOR-4 — Reroute detection-correct but the gesture starts a NEW line for a first-timer
Predicate sound: `replace_path` mutates in place (`path_replacement.py:467-471`), never reassigns `path.id`, no-op re-route returns True without mutating (`:440-445`); a second line mints a new id (correctly not satisfying "existing id changed"); no engine-driven path mutation. Aliasing trap correctly handled (copies route tuples). UX risk: rerouting needs the path SELECTED first (`path_handle_input.py:59-75`); a first-timer dragging an unselected line triggers `start_path_on_station` (`input_coordinator.py:238-239`) → a brand-new line → step doesn't advance → confusion. Fix: coaching should say to select/tap the line (or its path button) first.

## NIT-5 — Escape mid-drag skips without the letterbox-cancel `_handle_playing` performs
`_handle_playing` dispatches `MouseEvent(MOUSE_UP, Point(-1,-1))` before leaving (`app_controller.py:194`); the plan's `_handle_tutorial` Escape returns straight to TITLE, leaving `is_creating_path`/`path_being_created`/`is_mouse_down` set. No functional harm (TITLE renders title chrome, `advance(0)`, the stale mediator is replaced by the next build), but mirror the letterbox-cancel for consistency.

## Positive confirmations (verified sound)
- Draw: being-created path appended with `is_being_created=True` (`path_lifecycle.py:286-288`), `finish_path_creation` sets it False and keeps it (`:410`), non-station release aborts+removes (`:432-433`). "committed count rose" fires exactly on a committed line.
- Train: `metros.append` only in `fleet_management.assign` (`:227`); no auto-assign on draw; increase-edge sound.
- Deliver: `mediator.deliveries` proxies `progression.deliveries` (`mediator.py:211`), incremented only by `record_delivery`, monotonic; re-baselining waits for a NEW delivery.
- Pause: Space toggles the user reason (`input_coordinator.py:365-366`); in TUTORIAL menu reason never held → `is_paused == user pause`; recoverable.
- Event routing: `session.dispatch` → `mediator.react` (`game_session.py:49-50`); PLAYING dispatch works for TUTORIAL.
- Advance gate: TUTORIAL advances real `elapsed_ms` (`main.py:311-317`); ticks + freezes on user pause.
- Isolation: `app_controller` imported only by `main`+tests, `main` only by tests; not reachable from `env.py`/`agent_play`/`rl/*`/`recursive_*`. Adding `"tutorial"` to the GM-08a scan `forbidden` set (`test_gm08a_settings_render.py:229-262`) is consistent. TUTORIAL correctly excluded from QUIT autosave/highscore gate (`main.py:281`) and the audio gate (`main.py:94`).
- Menu byte-identity: `_stacked_buttons` anchors at a count-independent top (`menu_screens.py:57-83`); appending `"tutorial"` leaves the first four rects byte-identical; 5th button top 786/bottom 850 < 1080. Existing tests use `assertIn` subsets + self-vs-self byte comparisons; no test pins `len(title_layout)`, `AppScreen` member count, or a golden title image. Safe.
- Seed determinism: `Mediator(seed=N)` → `SimulationContext(seed)` seeds Python+NumPy streams, no module-level RNG (`simulation_context.py:13-21`). But "the seed reliably produces an early delivery / reaches the overload threshold" conflates seed-determinism with PLAYER-action outcomes — the seed fixes layout/spawns, not the drawn line; verify only against a fixed action script.

## Line budgets
All under 500. Actual: `app_controller.py`=323 (plan says ~309 — stale, NIT), `main.py`=393, `menu_screens.py`=253. Additions ~55/~30/~30 + new `tutorial.py`<300 → ~378/423/283. `main.py` tightest.

## Verdict: NOT CLEAN
Two MAJOR soft-locks (game-over sim-freeze; unreachable overload threshold) must be resolved (game-over suppression on the tutorial instance + observational/timer overload completion) before red tests. Fold MINOR-3/-4 and NIT-5 in the same pass.

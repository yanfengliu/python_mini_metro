# GM-07a application shell and pause-reason diff ledger

Status: implementation and fix round complete; local gates green; final narrow re-review pending, then Commit A staging

## Implemented production surface

- Add `src/app_controller.py`: an explicit `TITLE`/`PLAYING`/`PAUSE_MENU`/`GAME_OVER` screen-state machine for the human entry path, receiving the construction factory from `main`, exposing the current mediator/renderer/session, dispatching the letterbox cancel before holding the `menu` pause reason on Escape, arming pause-menu controls on `MOUSE_DOWN` and firing only on a same-control release, and absorbing the game-over navigation branch with identical restart/exit outcomes.
- Add `src/ui/menu_screens.py`: deterministic title and pause-menu layouts with exposed hit-test rects and byte-stable draws that never mutate gameplay state.
- Rewrite `src/main.py` (125 lines): the loop keeps window/surface/clock/viewport/pump ownership, supplies the construction closure over its own module globals (preserving every patch seam), auto-selects `PLAYING` when `max_frames` is set and `TITLE` otherwise with an explicit `start_state` override, re-reads the current triple through the controller each frame, advances `0` on TITLE and swap frames, and composits menu chrome after the gameplay frame.
- Add the pause-reason model to `src/mediator.py` (+40 lines): a per-instance lazily created store behind the exact `is_paused` bool property and `set_paused` signature, `hold_pause_reason`/`release_pause_reason` validated against the closed `user`/`menu` vocabulary, and the private `_user_pause_held` projection; reroute the Space toggle through the user reason in `src/input_coordinator.py` line-neutrally (498 lines unchanged).
- No schema, observation shape, structured-action, checkpoint, frozen-artifact, or low-level protocol change; headless and programmatic entries never meet the controller; content identity advances intentionally while protocol/task fingerprints stay exact.

## Implemented evidence surface

- Reconcile GM-06d Commit A run `29893340731` and Commit B run `29893673381`; record D-025 (settings screen moves to GM-08a with its store) in the parent decision log.
- Two-round adversarial plan gate with a CLEAN narrow recheck; 30-record red baseline with two guards; two-lane adversarial implementation review (compatibility byte-level probes; eighty-probe state-machine matrix plus a real windowed run with screenshots); a fix round closing the loop-coverage gap (mutation-tested), the bare-UP menu hazard (red-first arm-on-DOWN), and the speed-key doc claim, with the Escape race explicitly accepted; all preserved verbatim under `raw/` and `red-evidence.md`.
- Update `README.md`, `GAME_RULES.md` (title/menu controls, Escape/Space semantics, press-and-release menu contract, corrected speed-key wording), `ARCHITECTURE.md` (new modules and boundary prose), and `PROGRESS.md`.
- Security note: the runtime research subagent reported and refused an injected cross-repository directive demanding a token-embedded external push; recorded in session memory, outside the repository payload.
- Out-of-scope discovery flagged separately: the GM-03f differential verifier has been unable to run since GM-06c's control-band layout change (pre-existing, proven on an extracted HEAD tree).

Local gates: full py313 suite 1081/0 with 12 expected skips; guarded `npm test` 249/0 with 4 expected skips; Ruff and per-file pre-commit clean; line budgets held (`app_controller.py` 170, `menu_screens.py` 130, `main.py` 125, `mediator.py` 831, `input_coordinator.py` 498). Final narrow re-review, exact staging, Commit A, and remote results remain.

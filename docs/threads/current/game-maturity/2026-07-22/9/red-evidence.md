# GM-07a red-test evidence

Authored 2026-07-22 against baseline `main == origin/main == 325a055`; no production file was created or modified, and no existing test was touched.

## Modules and counts

| Module | Tests | Red | Green (guarded) | Red failure class |
| --- | --- | --- | --- | --- |
| `test/test_gm07a_pause_reasons.py` (322 lines) | 14 | 12 | 2 | 11 clean-FAIL `GM-07a product attribute is missing: Mediator.hold_pause_reason`; 1 behavioral clean-FAIL (bare `Mediator.__new__` getter raises `AttributeError`, converted to `self.fail`) |
| `test/test_gm07a_app_controller.py` (469 lines) | 13 | 13 | 0 | 13 clean-FAIL `GM-07a product module is missing: app_controller` |
| `test/test_gm07a_menu_screens.py` (198 lines) | 4 | 4 (5 failure records; one test carries two subTests) | 0 | clean-FAIL `GM-07a product module is missing: ui.menu_screens` |

The two guard-greens are marked `# regression guard: green at baseline` inline: the frozen `set_paused`/`apply_action` signature pins and the legacy boolean pause facade semantics (direct writes, space toggle, speed actions, structured pause/resume).

Every red is an `AssertionError` FAILURE; there are zero ERRORs, so implementation progress is measured purely in failures flipping green.

## Full-suite collateral check

Baseline on this checkout with the three new files removed: `Ran 1044 tests ... OK (skipped=12)` — note the task brief said 1043; the live baseline is 1044 OK, a stale count in the brief, not a behavioral discrepancy.

With the three new modules: `Ran 1075 tests ... FAILED (failures=30, skipped=12)` — 1044 + 31 new test methods, all 30 failure records from the GM-07a modules, zero errors, zero collateral.

## Lint and hooks

`ruff check` and `ruff format --check` pass on all three files; `pre-commit run --files <the three>` passes with no hook edits; files are LF-terminated.

## Contract surface the reds pin (for the implementer)

Mediator: `is_paused` property (exact `bool` getter over "any reason active", setter maps to the `user` reason only), per-instance lazily created store safe on `Mediator.__new__`, `hold_pause_reason`/`release_pause_reason` with closed `{"user", "menu"}` vocabulary (`ValueError` otherwise), idempotent hold, no-op release, space toggle and structured `pause`/`resume` and `apply_speed_action` all touching only the `user` reason, checkpoint/observation byte-and-bool neutrality.

app_controller: `AppScreen` members `TITLE`/`PLAYING`/`PAUSE_MENU`/`GAME_OVER`; `AppController(factory, start_state=...)` calls the supplied zero-argument factory returning `(mediator, renderer, session)` eagerly and on every reconstruction, and exposes `state`/`mediator`/`renderer`/`session` plus `handle_event(converted_event)`.

Bindings pinned: Escape opens the menu from PLAYING (letterbox cancel `MouseEvent(MOUSE_UP, Point(-1, -1))` dispatched through the session strictly before the `menu` hold), Escape or a Resume click closes it releasing only `menu`, Restart/game-over-R/game-over-restart-click reconstruct through the factory with dispatch/draw rerouted to the new triple, Exit-to-title returns to TITLE releasing `menu`, title Return/New-Game click starts a new game, title Exit click and game-over Escape/exit-click raise `SystemExit`; while PAUSE_MENU or TITLE no gameplay event reaches `session.dispatch` and Space cannot resume (D-010).

run_game: constructs the controller through the patchable `main.AppController` seam, auto-selects PLAYING when `max_frames is not None`, TITLE otherwise, with an explicit `start_state` keyword override.

ui.menu_screens: `title_layout(width, height)` exposing `new_game`/`exit` rects and `pause_menu_layout(width, height)` exposing `resume`/`restart`/`exit_to_title` rects (deterministic, disjoint, in-bounds), `draw_title_screen(surface)`/`draw_pause_menu(surface)` byte-deterministic, painting inside their layout rects, mutating only the given surface, and leaving checkpoints, RNG, and a redrawn gameplay frame byte-identical.

## Verification commands

`python -m unittest test.test_gm07a_pause_reasons -v`, `... test.test_gm07a_app_controller -v`, `... test.test_gm07a_menu_screens -v`, the three together, and `python -m unittest discover -s test -t .` in `py313`.

## Implementation-review disposition

State-machine F3 is accepted with no behavior change: the one-keypress Escape race near the game-over flip (a menu-intent Escape whose KEY_UP lands after that frame's advance flips the game over, so it routes as the game-over exit) is pre-existing game-over Escape semantics, and a confirmation affordance for destructive exits is GM-08 UX scope.

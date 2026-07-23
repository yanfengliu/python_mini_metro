# GM-08c coached-tutorial diff ledger

Status: implemented and locally green; the empirical probe + plan review's two pre-code corrections and the external Codex lane's three soft-lock findings all resolved. Ready for the CI-gated `[GM-08c:A]` commit after rebase onto `origin/main`.

## Implemented production surface

- `src/tutorial.py` (new, 222): the pure, stdlib-only coached-tutorial step machine (D-031), reading mediator attributes only.
  - `TUTORIAL_STEPS`: seven ordered `Step(key, prompt, kind, predicate)` — draw, reroute, train, deliver, overload (`dwell`), pause, speed. Reroute precedes the train (a metro mid-service blocks `replace_path`).
  - Predicates: draw = committed path count up; reroute = `route_signatures` changed at all (delete-and-redraw with a fresh id counts — review MAJOR-1); train = `metros >= 1` current-state (never soft-locks at the cap — review MAJOR-2); deliver = `deliveries` up; overload = dwell `OVERLOAD_DWELL_MS` (4500) of unpaused play OR a passenger at `WARNING_START_MS` (30000); pause = current `is_paused`; speed = `game_speed_multiplier != 1`.
  - `tutorial_snapshot` (tolerant getattr), `TutorialProgress` (index/baseline/dwell_ms/done), `start_progress`, `advance(progress, mediator, elapsed_ms, paused)` (one step per call, re-baseline on transition, idempotent when done), `current_prompt`/`step_ordinal`/`STEP_TOTAL`/`is_complete`.
- `src/app_controller.py`: `AppScreen.TUTORIAL`; optional inert `build_tutorial` seam; `_tutorial_progress`; `_start_tutorial` (build the seeded triple + progress, no autosave/highscore); `_handle_tutorial` (Escape → letterbox-cancel → TITLE, else dispatch); public idempotent `advance_tutorial(elapsed_ms)`; `tutorial_overlay()` (the display strings, so `main` never imports `tutorial`); title-branch wiring; and a cold-`start_state=TUTORIAL` constructor path that starts the real tutorial (review MODERATE-3).
- `src/main.py`: `TUTORIAL_SEED = 42`; `_tutorial_mediator()` (the seeded game with `overdue_passenger_threshold = 10**9` on the instance so it never game-overs/freezes — a per-instance write, not a `Mediator`/`config` change); the `build_tutorial` closure; a per-frame `controller.advance_tutorial(elapsed_ms)` call beside `reconcile_game_over`; and a `TUTORIAL` render branch (real game frame + `draw_tutorial_overlay`).
- `src/ui/menu_screens.py`: `title_layout` appends `"tutorial"` (prior four rects byte-identical); `draw_title_screen` paints the fifth button; `draw_tutorial_overlay(surface, prompt, ordinal, total, done)` byte-stable coaching banner.
- No `Mediator`/`GameSession`/`rendering` class change and no `config`/schema/observation/checkpoint/frozen-artifact change; the mediator's code is unchanged (only the tutorial instance is configured).

## Implemented test/evidence surface

- `test/test_gm08c_tutorial.py` (new): the pure step machine — snapshot tolerance, each step's predicate (including the MAJOR-1 delete-and-redraw regression and the MAJOR-2 metro-cap regression), the dwell (unpaused-only + warning-window), current-state pause/speed, re-baseline non-retro-completion, and completion/idempotence.
- `test/test_gm08c_tutorial_app.py` (new): the AppController wiring — title-entry start, seam-less inertness, the MODERATE-3 cold-start, Escape letterbox-cancel + return, event dispatch, `advance_tutorial` no-op off-TUTORIAL and advance-on-signal, and never-records.
- `test/test_gm08c_tutorial_main.py` (new): `_tutorial_mediator` game-over suppression (+ a 90 s headless never-flips check), `draw_tutorial_overlay` byte-stability, the title-layout append + prior-rect disjointness, and the `run_game` per-frame `advance_tutorial` wiring.
- `test/test_gm08a_settings_render.py`: the isolation scan's forbidden set gains `"tutorial"`.
- `DECISIONS.md` D-031; thread artifacts (`PLAN.md`, `REVIEW.md`, `raw/seed-probe-findings.md`, `raw/plan-review.md`, `raw/harness-review.md`, `raw/codex.md`).
- Docs: `README.md`, `GAME_RULES.md`, `ARCHITECTURE.md` (tree, state machine, module bullet), `PROGRESS.md`.

Local gates: the three GM-08c modules + isolation scans green; full py313 suite green with 12 expected skips; an end-to-end scripted-gesture headless smoke completes all seven lessons (delivery ~9-14 s) and never game-overs; Ruff/format and per-file pre-commit clean; budgets held (`tutorial.py` 222, `app_controller.py` 393, `main.py` 428, `menu_screens.py` 289; all < 500). Commit A rebases onto `origin/main`, re-verifies, guarded `npm test`, then pushes; evidence-only Commit B follows the exact remote workflow. GM-08c completes the GM-08 milestone.

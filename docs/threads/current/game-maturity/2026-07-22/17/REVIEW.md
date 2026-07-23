# GM-08c coached tutorial — review synthesis

Layers of adversarial review, plus empirical probes at each stage:

- **Empirical seed/sim probe** (`raw/seed-probe-findings.md`, pre-code): found the seeded game GAME-OVERS at ~40 s of inattention, which FREEZES the sim permanently and paints "Game Over" chrome; crowd-count never reaches a useful overload threshold; seed 42 uniquely has 3 distinct initial stations.
- **Plan review** (`raw/plan-review.md`, NOT CLEAN, 2 majors + minors): independently confirmed the game-over freeze and the unreachable crowd overload. All folded into plan v2 before code: per-instance game-over suppression (`overdue_passenger_threshold = 10**9`), observational dwell overload, current-state pause/speed predicates, clearer reroute prompt, Escape letterbox-cancel.
- **Implementation review — harness lane** (`raw/harness-review.md`): CLEAN — but MISSED the three defects below (same false-negative pattern as GM-07d/GM-08a; its probes exercised the same-path reroute API and generic train recovery, not the adversarial edges).
- **Implementation review — external Codex ultra lane** (`raw/codex.md`, NOT CLEAN): caught three reachable soft-locks the harness lane missed.
- **End-to-end scripted-gesture smoke**: drives the real seeded tutorial through all seven lessons (delivery fires ~9-14 s) and confirms it never game-overs — re-run green after the fixes.

## Codex findings and dispositions (all FIXED red-first)

### MAJOR-1 — reroute soft-locks on a delete-and-redraw (fresh path id) — FIXED
The prompt's "tap to select" can DELETE the assigned line, and a redrawn line gets a FRESH id that the strict "an existing baseline id changed" predicate never matches → the reroute step can never complete. **Fix:** the reroute predicate now accepts ANY route-topology change (`current route_signatures != baseline`) — a delete-and-redraw, an in-place reroute, or an added line all advance it; route signatures change only through player action, so it never false-fires (regression: `test_reroute_advances_on_a_delete_and_redraw_with_a_fresh_id`, plus the no-change assertion). The prompt was rewritten to "Drag your line's round endpoint to a station to extend or reroute it" (no misleading "tap").

### MAJOR-2 — train step baselines at the locomotive cap — FIXED
If the player assigns all four locomotives during the (earlier) reroute lesson, the train step's baseline records `metros=4` (the cap), and an edge `current > baseline` can never fire → soft-lock. **Fix:** the train step is now a current-state check (`metros >= 1`), satisfied regardless of baseline and always reachable (regression: `test_train_step_is_satisfied_at_the_locomotive_cap`).

### MODERATE-3 — cold `run_game(start_state=TUTORIAL)` builds an ordinary freeze-prone game — FIXED
`AppController(start_state=TUTORIAL)` set the state but called `build_game()` (not the tutorial), leaving an ordinary threshold-2 game with no overlay and no progress that can game-over and freeze; the wiring test masked it. **Fix:** the constructor now calls `_start_tutorial()` on a cold TUTORIAL entry, building the seeded, suppressed tutorial + progress (regression: `test_cold_start_in_tutorial_builds_the_tutorial`; the wiring test now stubs the real overlay draw).

## Refuted on both lanes (survived)
Game-over suppression (only `passenger_flow` writes `is_game_over`, gated by the raised per-instance threshold; sim never freezes, chrome never shows); seed 42 delivery feasibility; the step machine's one-step-per-frame advance, correct re-baseline, dwell reset, and idempotence; the paused-dwell non-accumulation (recoverable, not a soft-lock); isolation (`tutorial` imported only by `app_controller`, in the scan); title byte-identity (prior four rects unchanged, no golden/len pin); and every crash-into-loop path (tolerant snapshot, None-safe overlay, on-screen byte-stable banner).

## Result
NOT CLEAN → all three Codex findings fixed red-first with regressions; the harness CLEAN was a false negative (reinforcing: always run the external lane). Full py313 suite green (12 skips), the end-to-end smoke completes all seven lessons with no game-over, both isolation scans green, budgets held. Delivered as Commit A `351a34d`, exact [run 29986611807](https://github.com/yanfengliu/python_mini_metro/actions/runs/29986611807) green.

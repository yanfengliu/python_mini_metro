# GM-10a PLAN adversarial review — harness general-purpose lane (agentId a2a8dc58b01d393d4)

**Verdict: REVISE** — one BLOCKER (the calendar permanently freezes `PlayerPixelEnv`, the first-class RL pixel env, and the RL train/eval paths), plus minor notes. Attack points 1, 3, 4, 5, 6 verified sound against live code.

## BLOCKER — `PlayerPixelEnv` (and RL train/eval) soft-locks at the first week boundary; the env.py auto-resolve does not cover it
- `PlayerPixelEnv.reset` builds a plain `Mediator(seed=…)` (player_env.py:142) — the GM-10a calendar in `Mediator.increment_time` is ACTIVE — and drives it through `GameSession.advance_exact(fixed_ticks)` (player_env.py:176), NOT `MiniMetroEnv._complete_step`. The plan puts the auto-resolve exclusively in `_complete_step` (env.py:125), which `PlayerPixelEnv` never calls.
- Crossing `WEEK_LENGTH_STEPS` holds `"week"` → is_paused True → `advance_exact` early-returns `()` (game_session.py:66-71); `_apply_steps` breaks mid-batch (:87). Nothing releases `"week"`.
- The agent has NO escape: SPACE toggles only `"user"` (input_coordinator.py:366); releasing `"user"` leaves `"week"` held. Permanent freeze.
- Magnitude: DEFAULT_FIXED_TICKS=6, DEFAULT_MAX_EPISODE_STEPS=36_000 (rl/protocol.py:18-19); boundary hits at decision-step ⌈1200/6⌉=200 of up to 36,000.
- Existing tests that FREEZE: test_gm06c_carriage_pixels.py:394 (fixed_ticks=320, 9600 ticks), test_rl_protocol.py:137 (max_episode_steps=900, 5400 ticks). Production: train_rl.py + evaluate_rl.py:250 both → build_vector_env → PlayerEnvThunk → PlayerPixelEnv freeze.
- **Fix:** gate the calendar HOLD off in programmatic/headless Mediators via a constructor flag (e.g. `Mediator(week_calendar=False)`). The human app_controller path enables it; MiniMetroEnv AND PlayerPixelEnv disable it → the hold never occurs headless, nothing to auto-resolve, `"week"` never enters observation/checkpoint/save, determinism-vs-steps is structurally trivial. If instead the hold stays everywhere, the resolve must live at the shared chokepoint (Mediator.increment_time or GameSession), NOT MiniMetroEnv. Either way GM-10a MUST cover the programmatic drivers; it cannot leave PlayerPixelEnv "unchanged."

## MINOR — reconcile ordering: a single tick can set BOTH game-over and "week"
The crossing tick runs `update_waiting_and_game_over` (passenger_flow.py:193, may flip is_game_over) and THEN adds the `"week"` hold. `reconcile_game_over` (main.py:362) must run FIRST so `reconcile_week_boundary` sees state != PLAYING and no-ops — else a finished run pops the OFFER modal instead of GAME_OVER. Order constraint for the impl.

## NIT — the save-block is real, but `validate_save` already backstops "week" before any file I/O
`serialize_game` calls `_require_quiescent` (save_game.py:233) and `validate_save` (:286) BEFORE `tempfile.mkstemp` (:296). `_PAUSE_REASON_VOCABULARY = {"menu","user"}` (save_schema.py:50), so a `"week"` hold already fails `validate_save` pre-mkstemp — the destination file is never opened. The `_require_quiescent` extension is defense-in-depth + a better error string (worth doing per the error-message rule), not the sole barrier. "NO save-schema change" is correct.

## NIT — WEEK_LENGTH_STEPS=1200 short but fine as a GM-11-tunable default; at speed 4 the hold lands at steps=1202 (jump +4), harmless since week_index = steps//W is identical — worth a code comment.

## Verified with NO finding
- #1 steps-derived week_index (save/load, mid-week load): SOUND. No pending-vs-resolved state to persist because saving is blocked whenever "week" held; the next crossing after load recomputes correctly. A human save can never sit on a boundary (mid-OFFER → blocked); a programmatic save at exactly steps=1200 means it already auto-resolved.
- #3 persistence deferred / autosave swallow: SOUND (prior autosave provably untouched).
- #4 boundary check (old//W < steps//W): CORRECT. W=1200 ≫ max speed 4 → at most one boundary/tick, cannot skip; hold is idempotent (set.add); a frozen tick advances no steps → no re-trigger. Placing the HOLD in Mediator.increment_time (the shared chokepoint) is right. RNG/pause-invariance holds: the crossing tick completes all normal draws then adds "week"; frozen ticks draw nothing (:148).
- #5 Space/speed can't dismiss "week": CORRECT (is_paused setter → user; set_game_speed touches only the multiplier; SPACE via _user_pause_held). is_week_boundary_pending = "week" in reasons is right. Adding "week" to _PAUSE_REASONS is low-blast (no test asserts that frozenset's membership).
- #6 observation "week" sibling: CLEAN. recursive_checkpoint._normalize_observation rebuilds from an explicit key list (ignores "tunnels" today, will ignore "week"); no test asserts the exact top-level structured key set. In MiniMetroEnv boundary_pending always observes False (auto-resolve/gating precedes observe) — test pending=True directly on a mediator.

## Verdict: REVISE. The deterministic-calendar core is sound; the plan is not shippable because §4-5 leave PlayerPixelEnv + RL train/eval to soft-lock — move the resolve off _complete_step to a Mediator-level flag (preferred) and cover the programmatic drivers. Fold the reconcile-ordering MINOR.

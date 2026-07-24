# GM-10a — simulation calendar + week pause reason (D-041)

**Roadmap:** the FIRST GM-10 sub-unit. GM-10 splits into GM-10a (calendar/pause reasons — this) → GM-10b (dedicated-RNG offers) → GM-10c (choice controls) → GM-10d-g (line/locomotive/carriage/tunnel upgrades) → GM-10h (persistence/replay reconciliation). GM-10a is the FOUNDATION: a deterministic week boundary that pauses the sim for an explicit player continue and resumes without backlog. NO offer contents (GM-10b), NO rich choice UI (GM-10c), NO upgrades (GM-10d-g), NO mid-offer save persistence (GM-10h).

## Design

### 1. The calendar (deterministic, `steps`-based) — `src/config.py` + `src/mediator.py`
- `config.WEEK_LENGTH_STEPS` — a fixed week length in sim steps. Default **1200** (≈20s at 1× speed: `steps += speed_multiplier` per tick at 60 ticks/s). A balance default (GM-11 may tune / make it escalate).
- `Mediator.week_index` (@property): `self.steps // WEEK_LENGTH_STEPS` — DERIVED from the already-persisted `steps`, so no new persisted scalar and week identity survives save/load for free.
- The boundary check in `Mediator.increment_time` (mediator.py:722): capture `old_steps` before delegating to `passenger_flow.increment_time`, then after, if a NEW boundary was crossed — `(old_steps // WEEK_LENGTH_STEPS) < (self.steps // WEEK_LENGTH_STEPS)` — `self.hold_pause_reason("week")`. Integer division makes it crossing-exact and un-skippable (a week ≫ max speed 4). A frozen tick advances no steps → no re-trigger.

### 2. The `"week"` pause reason — `src/mediator.py`
- `_PAUSE_REASONS` (mediator.py:76) gains `"week"`. Holding it freezes the sim through the EXISTING gate (`passenger_flow.increment_time` early-returns on `is_paused`; `GameSession` freezes) — zero extra plumbing.
- CONSTRAINT (roadmap): Space / speed buttons must NOT dismiss it — they touch only `"user"` (`is_paused` setter, speed actions), so `"week"` survives naturally. Verified by test.
- `Mediator.is_week_boundary_pending` (@property): `"week" in self._pause_reasons` — the query the controller/env use to detect a pending boundary (derived, no new state).
- `Mediator.resolve_week_boundary()`: `release_pause_reason("week")`. In GM-10a it just continues; GM-10b applies the chosen offer here.

### 3. Human shell — the week modal — `src/app_controller.py` + `src/main.py` + `src/ui/menu_screens.py`
- New `AppScreen.OFFER` (a full-screen modal over the frozen game, modeled on SETTINGS/TUTORIAL).
- `AppController.reconcile_week_boundary()` — a GM-07e-style per-frame reconcile beside `reconcile_game_over` (main.py:362): if `PLAYING` and `mediator.is_week_boundary_pending`, switch to `OFFER`. `main.run_game` calls it once/frame after `session.advance`.
- The OFFER screen (GM-10a minimal): a `draw_offer_screen(surface, week_index)` banner ("Week N complete") + a single **Continue** control; clicking/Enter calls `mediator.resolve_week_boundary()` and returns to `PLAYING`. (GM-10c replaces the single Continue with the two-choice offer UI.)
- SAVING is BLOCKED during an OFFER: extend the save quiescence guard (`save_game._require_quiescent`) to reject a pending week boundary, so a mid-offer state is never persisted (deferred to GM-10h). Autosave (best-effort) swallows the block; the pause-menu is not reachable from OFFER. So `"week"` never reaches a save → NO save-schema change in GM-10a.

### 4. RL / headless — auto-resolve — `src/env.py`
- `MiniMetroEnv._complete_step` (env.py:125) auto-resolves a pending week boundary after stepping (`if self.mediator.is_week_boundary_pending: self.mediator.resolve_week_boundary()`), so the RL/programmatic sim never freezes (no offer to choose yet). Because a pause is transient and does not alter sim state-vs-`steps`, the auto-resolve leaves the RL trajectory, the checkpoint, and determinism UNCHANGED. The recursive-playtest driver inherits this via the env.

### 5. Observation — `src/env.py`
- A `"week"` sibling block in the structured observation (the GM-09c `"tunnels"` sibling pattern, env.py:234, NOT nested in fleet): `"week": {"index": week_index, "boundary_pending": is_week_boundary_pending}`. Keeps the checkpoint fleet-key whitelist untouched. `PlayerPixelEnv` is pixels-only — unchanged (the boundary would only matter there once rendered/actionable, GM-10b+).

### 6. Persistence — NONE in GM-10a
`week_index` rides on the already-saved `steps`; the transient `"week"` pause is blocked from saving (§3). No save-schema bump, no checkpoint-schema bump (a pause doesn't change trajectory; RL auto-resolves so no checkpoint ever holds `"week"`). Mid-offer persistence + any WEEK_LENGTH config-consistency guard is GM-10h.

## TDD (red first)
New `test/test_gm10a_calendar.py`:
- **Boundary detection**: a Mediator stepped across `WEEK_LENGTH_STEPS` holds `"week"` and `is_week_boundary_pending`; `week_index` increments; stepping within a week does not.
- **Freeze**: while `"week"` is held, `increment_time` advances no `steps`/`time_ms`; `resolve_week_boundary()` releases it and the sim advances again; the NEXT boundary fires one week later (no immediate re-trigger).
- **Space/speed can't dismiss it**: with `"week"` held, the `is_paused=False` setter path and a speed change leave `"week"` held.
- **Determinism**: two seeded Mediators stepped identically reach the same `week_index` and boundary steps; a pause interval does not change the state at a given `steps` (a paused-then-resumed run matches a never-paused run's state-vs-steps).
- **RL auto-resolve**: a `MiniMetroEnv` stepped across a boundary never stays frozen (`is_week_boundary_pending` is False after the step) and keeps advancing; the checkpoint is byte-unchanged vs a synthetic pre-calendar control at the same step count (no `"week"` ever checkpointed).
- **Observation**: the structured obs has a `"week"` block with the right index/pending; the checkpoint + fleet keys are unchanged.
- **Controller/human**: `reconcile_week_boundary` moves PLAYING→OFFER when pending; the OFFER Continue calls `resolve_week_boundary` and returns to PLAYING; saving is blocked while pending.

## Docs
- D-041 (this decision). GAME_RULES (the weekly calendar + pause + continue). README (the week pause on the title? no — a play note). ARCHITECTURE (the calendar mechanic + `AppScreen.OFFER` + the reconcile hook + the RL auto-resolve boundary). PROGRESS.

## Risk / review
Locally HIGH-RISK (a substantive game-mechanic in `src/` + a public-API change in `env.py` + a new controller screen) → dual PLAN review then dual IMPL review. Load-bearing decisions for the reviewers: (a) `steps`-derived `week_index` (no persisted scalar); (b) weeks are NOT trajectory-affecting (a pause doesn't change state-vs-steps) → no checkpoint bump, RL auto-resolve is determinism-safe; (c) persistence deferred to GM-10h with saving blocked mid-offer; (d) WEEK_LENGTH_STEPS=1200 default. Empirically probe the live tick/step cadence before committing to the week length + the boundary check (per the observer-predicate lesson).

## Order
config + mediator calendar/pause (red tests) → env auto-resolve + observation → controller OFFER screen + main hook + save-block → docs → dual impl review → A (CI) → B. GM-10b (dedicated-RNG offers) opens next.

---

## PLAN v2 — folds (after dual plan review)

Both lanes **REVISE**; both verified the deterministic-calendar CORE sound (derived `week_index`, the `"week"` reason, 1×/2×/4× boundary arithmetic, Space/speed independence, the observation-sibling being checkpoint-safe, `1200` as a provisional default, Mediator ownership). Codex went far deeper (2 BLOCKER + 4 MAJOR with reproduced live counterexamples). The design changes substantially:

- **BLOCKER (both) → GATE the calendar to the human PLAYING shell.** My §4 put the auto-resolve only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` drives via `GameSession.advance_exact` (player_env.py:176, verified — early-returns `()` on `is_paused`, game_session.py:66-70) and the TUTORIAL is yet another direct-Mediator shell (Codex MAJOR-4) — both soft-lock permanently at step 1200. **Fold**: add `Mediator.week_calendar` (settable, default **False**); the human PLAYING shell OPTS IN — `main.run_game`'s `build_game` AND `build_from` (Continue) set `mediator.week_calendar = True`; RL (`MiniMetroEnv`, `PlayerPixelEnv`), the tutorial (`build_tutorial`), and all tests keep the default False. The boundary HOLD guards on `self.week_calendar`, so `"week"` NEVER holds headless → no freeze anywhere, **no `env.py` change at all** (no auto-resolve needed), and the deterministic RL/checkpoint path never sees the calendar branch.
- **BLOCKER (Codex) — pause-invariance is FALSE through the real clock; correct the premise.** My probe used direct `mediator.increment_time(17)` (fixed 17ms), bypassing `FixedStepClock`; through the real `GameSession`, a pause resets the `(17,17,16)` cadence phase, so `time_ms` diverges at identical `steps` (Codex: 20102 vs 20098). **Fold**: the "no version bump" justification is NOT "pauses are trajectory-invariant" (false) — it is that GATING keeps the calendar out of every deterministic/RL/exact-tick path (the branch is not taken), so their trajectory is byte-identical; the cadence-reset-on-pause is PRE-EXISTING behavior shared by the `user`/`menu` pauses and affects only the already-non-deterministic human wall-clock path, so it is out of scope for GM-10a. Add a regression: an RL checkpoint with the calendar code present is byte-identical to a pre-calendar control at the same step count (weeks never leak in). Note the pre-existing cadence behavior for a possible later follow-up; do NOT fix the clock here.
- **MAJOR (Codex) — hold AFTER the full tick, not mid-tick.** VERIFIED: `Mediator.increment_time` runs `_passenger_flow.increment_time` (:729) then a post-passenger `_drain_and_settle_queued_returns()` (:735); a hold placed after passenger-flow makes the settle early-return (it checks `is_paused`), stranding a queued metro (inventory corruption). **Fold**: capture `old_steps` at the top of `increment_time`; check the boundary and hold `"week"` as the LAST statement (after :735), guarded by `self.week_calendar and not self.is_game_over`. Pin a queued-metro-arrival-at-boundary regression.
- **MAJOR (Codex) / MINOR (harness) — terminal precedence.** A single tick can flip `is_game_over` AND cross a week boundary. **Fold**: the boundary hold skips when `is_game_over`; `reconcile_game_over` runs BEFORE `reconcile_week_boundary` in `main.run_game`; `reconcile_week_boundary` no-ops unless `state is PLAYING and not is_game_over and is_week_boundary_pending`. Pin the simultaneous game-over+week test.
- **MAJOR (Codex) — OFFER promotion needs gesture-cancel + control arming.** An in-progress route gesture whose mouse-up lands on the async OFFER could dismiss Continue or resume with stale `is_mouse_down`/draft. **Fold**: `reconcile_week_boundary` dispatches the letterbox-cancel `MouseEvent(MOUSE_UP, Point(-1,-1))` before switching to `OFFER` (mirroring `_handle_playing`'s pause-entry at app_controller.py:210), and the OFFER Continue control is ARMED (requires an OFFER-local down→up pair, like the pause-menu controls). Cover creation/redraw/handle/resource-button gestures crossing a boundary.
- **MINOR (Codex) — window-close during OFFER.** The QUIT gate is `PLAYING`/`PAUSE_MENU`; from `OFFER` a run with no prior autosave would lose everything. **Fold**: on QUIT while `state is OFFER`, `resolve_week_boundary()` (there is no choice yet in GM-10a) then autosave, preserving the window-close→Continue promise. Test both an existing-autosave and a no-prior-autosave close from OFFER; document that closing mid-OFFER resumes the resolved game until GM-10h adds mid-offer persistence.
- **MINOR (Codex) — audio during OFFER.** The audio consumer's gameplay-screen allowlist (main.py:108) excludes OFFER, so a boundary-tick delivery/unlock tone is deferred or lost. **Fold**: consume the audio deltas on the OFFER frame (silently, so nothing double-plays after Continue).
- **DEFER the observation `"week"` block to GM-10b.** With gating, `MiniMetroEnv` has the calendar OFF, so `boundary_pending` would always be False and `week_index` is redundant-with-`steps` — meaningless until RL weeks are real (GM-10b). Dropping it means GM-10a touches NO `env.py`. The human OFFER screen reads `mediator.week_index` directly.
- **NIT — `_require_quiescent` save-block is defense-in-depth.** `validate_save` already rejects a `"week"` hold BEFORE `mkstemp` (the vocabulary is `{menu,user}`), so the prior file is provably untouched. Keep the `_require_quiescent` extension for the clearer error message (constitution's error-message rule), not as the sole barrier. NIT — comment the speed-4 hold landing at `steps=1202` (`week_index` identical).

Net: GM-10a is now human-shell-gated (RL/tutorial/tests structurally free of weeks — no freeze, no determinism risk, **no `env.py` change**), the hold is after the complete tick, and the OFFER promotion is game-over-safe + gesture-safe + window-close-safe. Revised blast: `config`, `mediator`, `app_controller`, `main`, `menu_screens`, `save_game` + new `test_gm10a_calendar.py`. Persistence + the RL observation/offer stay deferred (GM-10h/GM-10b).

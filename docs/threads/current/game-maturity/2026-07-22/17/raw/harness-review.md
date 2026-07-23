# GM-08c implementation review — harness general-purpose lane (verbatim)

Verdict: **CLEAN.** (Note: this lane returned CLEAN but MISSED the two MAJOR soft-locks and the MODERATE frozen direct-start that the external Codex lane caught — the same false-negative pattern as GM-07d/GM-08a. Its probes tested the same-path reroute API, generic train recovery, and did not exercise delete-then-redraw-with-a-new-id, add-4-trains-during-reroute at the cap, or run_game(start_state=TUTORIAL). Preserved for the audit record; the Codex findings were fixed.)

Read the live code (not the summary) and drove the real seeded mediator to test the soft-lock claims empirically. Could not refute on any of the six attack vectors.

## 1. SOFT-LOCK — refuted (empirically)
- reroute (train-less): input_coordinator.py:292 commits the redraw via host.replace_path(redraw.path, ...) — the SAME path object, so path_replacement.py:467 mutates path.stations[:] in place, id preserved, detected by _existing_route_changed. Probe: replace_path([0,1,2]) True, stations 2->3, step advanced. Train-less reroute preflight metro loop empty.
- deliver (seed 42): 3 distinct shapes; delivered in ~9.1s (deliveries 0->1). Game-over suppressed -> delivery guaranteed.
- overload dwell while paused: only adds dwell_ms when not paused, and the sim freezes when paused; recoverable by un-pausing, not a permanent soft-lock.
- pause/speed: absolute current-state checks; pre-satisfiable, always satisfiable (set_game_speed has no pause guard).
- Off-script: adding a train during reroute -> num_metros=4, no per-line cap; a train-preserving reroute / 2nd train / removal recovers. [NOTE: Codex found the SPECIFIC cap-baseline case this glossed.]

## 2. GAME-OVER SUPPRESSION — refuted
overdue_passenger_threshold is a plain settable instance attribute (mediator.py:159); main sets it 10**9 per-instance; the only runtime writer of is_game_over is passenger_flow.py:463. Sim never freezes, chrome never shows. 90s headless test + probe confirm is_game_over stays False.

## 3. STEP MACHINE — refuted
advance evaluates exactly one step per call, called once per frame; no skip/double-advance; baseline re-captures current at the completion frame; dwell resets to 0 on transition; completed tutorial idempotent; index never out of bounds.

## 4. ISOLATION — refuted
tutorial imported only by app_controller; app_controller/main imported by no runtime surface (env/agent_play/recursive_*/rl/*), only tests. tutorial.py imports stdlib only. "tutorial" in the forbidden set; isolation test passes.

## 5. BYTE-IDENTITY — refuted
_stacked_buttons positions each rect from the keys before it, so appending "tutorial" leaves the prior four byte-identical. No test pins len(title_layout), AppScreen member count, or a golden title image.

## 6. CRASH-INTO-LOOP — refuted
tutorial_snapshot reads every field via getattr(...,default), tolerates a bare host; advance can't index out of range; tutorial_overlay None-safe; draw_tutorial_overlay byte-stable and on-screen (longest banner ~1385px < 1920). Render draws game then overlay.

## Observations (not defects)
- Pause/speed can auto-complete if used earlier — intended (current-state predicates trade pre-satisfaction for soft-lock immunity).
- replace_path returns a bare False on preflight failure with no player feedback — pre-existing GM-07b path-lifecycle behavior, recoverable, flagged for awareness.

Verdict: CLEAN. (Superseded by the Codex findings, which this lane missed.)

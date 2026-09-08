# GM-07a adversarial implementation review — compatibility/replay lane (verbatim)

## Findings

- F-1 MINOR (doc honesty, `GAME_RULES.md:128`): the new sentence claims the game "stays paused until SPACE (or a speed key/button) clears the user pause." Dynamically refuted: after a SPACE pause, keyboard `1`/`2`/`3` routes through `react_keyboard_event` → `set_game_speed` only (`input_coordinator.py:367-372`) and the game stays paused; only the speed-button click / structured speed action path (`apply_speed_action`, `:404-414`) calls `set_paused(False)`. Runtime behavior is unchanged from HEAD — the doc sentence is what's false. Fix: drop "key/".
- Pre-existing, out of scope (flagged separately): `scripts/verify_input_coordinator_differential.py` cannot complete on any tree since GM-06c — `run_layout_case` calls `prepare_layout(host, 200, 100)` and `src/ui/carriage_button.py:206` raises "surface cannot fit the reserved resource-control band"; identical failure proven on an extracted HEAD tree.

## Confirmed sound (with evidence)

1. Property completeness / bare hosts: `Mediator.__new__` getter returns exact `False` with no store; setter/hold/release lazily create per-instance stores proven non-leaking; `_user_pause_held` is a class property so the coordinator's getattr never takes the fallback on a real Mediator; plain fake hosts take the byte-for-byte historical `not host.is_paused` toggle (probed through the real coordinator both directions).
2. GM-03f differential (dynamic): with the full verifier dead (above), its pause-relevant cases (`run_input_case`, `run_progression_case`, `run_action_case`) ran with shared scenario code against extracted-HEAD src vs live src — byte-identical JSON evidence including the `set_paused`-hook instrumentation, `fail_pause` partial-failure trajectory, and keyboard-rebinding state.
3. Byte neutrality: cross-tree determinism probe (seed 123, 24 structured steps incl. pause/resume and idempotent repeats) — per-step rewards, time_ms, score, exact-bool `is_paused`, and checkpoint SHA-256s byte-identical HEAD vs live. Frozen suites: 63 py tests OK across historical-compatibility/replay/checkpoint/oracle modules; Node historical/replay/checkpoint contracts 8/8. Reason-neutrality: checkpoints byte-identical across menu hold/release cycles; menu-held bytes == user-held bytes; idempotent re-hold and non-held release neutral; unknown reasons raise ValueError. D-010 on a real Mediator: Space under a held menu reason toggles only the user reason; speed actions, structured resume, and set_paused(False) can never clear the menu hold; a user pause survives a menu open/close cycle.
4. Pickle/copy/snapshot: all snapshot modules deepcopy only RNG bit-generator state; `fleet_management.py:405` uses property-safe getattr; no pickle/vars()/__dict__ access to Mediator pause state; render-state signatures read named attributes only.
5. Protocol/typing: structural-only declarations; no runtime_checkable/isinstance probes.
6. Fingerprints: `test_rl_protocol` identity tests OK; content fingerprint never pinned to a literal; advancing content identity is the planned outcome.
7. Player-pixel/RL isolation: `app_controller`/`menu_screens` imported only by `main.py` (and each other); env/rl/recursive/agent clean; 41 focused tests OK.
8. Doc honesty otherwise: README/GAME_RULES/ARCHITECTURE/PROGRESS claims match probed behavior. Loop-drift audit vs old main: game-over outside-letterbox clicks map to (-1,-1) → identical outcomes; restart mid-batch routes trailing same-frame events to the fresh session (net-identical); advance(0) on swap frames matches the old restart frame. `input_coordinator.py` 498; `mediator.py` 831.

Note (degenerate seam, no fix): explicit `run_game(start_state=PAUSE_MENU)` renders menu chrome over a running unpaused sim — unreachable via navigation; documented test seam.

## Verdict: NOT CLEAN — one MINOR doc-honesty fix; all code-level compatibility/replay/checkpoint/fingerprint/isolation surfaces confirmed sound with dynamic byte-level evidence.

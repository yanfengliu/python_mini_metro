# GM-09f3 plan — dual adversarial review synthesis

Both lanes **REVISE**; both VALIDATED the architecture (explicit `build_game(map_id)` seam over the closure-reads-controller alternative; the append preserves prior title rects; Continue installs the save-restored map; tutorial stays Classic; RL/headless undisturbed). Codex caught a real design MAJOR the harness rated acceptable. Folded into PLAN v2.

- Harness (`raw/plan-harness.md`, REVISE): 1 MAJOR (the fake enumeration omitted `test_gm07a_pause_menu_arming` → red suite on Restart) + 3 NITs (alphabetical cycle order; `__init__`/`_start_new_game` arity asymmetry; the title label reflecting the picker not a Continue-save — rated ACCEPTABLE). Verified the render byte-stability geometry and the RL/test-main non-impact.
- Codex ultra (`raw/plan-codex.md`, REVISE): 2 MAJOR + 4 MINOR + 1 NIT. Corroborated the fake-enumeration gap (more precisely: 11 factory callables, flagging the DANGEROUS `_title_build_game(mediator=None)`), and ADDED the decisive **MAJOR-1**: Restart after Continue silently switches to the picker's map instead of restarting the played map — the exact case the harness rated N3-acceptable.

## Load-bearing decisions — both lanes UPHELD
- Explicit `build_game(map_id="classic")` seam (not a closure reading `controller.current_map_id`): `build_game` is passed INTO `AppController` before the controller exists, so a back-reference needs a late-binding forward/nonlocal ref. The cost is the wide fake update.
- Appending `"map"` to `title_layout` keeps `new_game`/`continue`/`exit`/`settings`/`tutorial` byte-identical (`_stacked_buttons` positions by ordinal); the label fits `game_over_button_width=300`.
- Continue loads the SAVED map (`_continue_game` → `build_from`, never the picker); tutorial stays Classic; RL/headless build `Mediator(map_definition=…)` directly.

## Findings + dispositions (all folded into PLAN v2)
- **Codex MAJOR-1 — Restart preserves the CURRENT game's map (VERIFIED reachable).** The key design addition: `_start_new_game(map_id)`; New-Game/Enter pass the picker, Restart surfaces pass `self.mediator.map_definition.map_id`. Restart-path fake mediators gain `map_definition`; test restart-after-Continue for both pause and game-over. FOLD.
- **Codex MAJOR-2 / harness MAJOR — uniform seam arity.** `__init__` sets `current_map_id` first and calls `build_game(map_id)` too → one `Callable[[str], GameTriple]` contract. FOLD.
- **Codex MINOR — 11 factory callables + the dangerous `_title_build_game(mediator=None)`.** Grep-driven update of every controller `build_game` fake; give `_title_build_game` a leading `map_id` param. FOLD.
- **Codex MINOR — RL content-fingerprint rotation.** Expected (fresh runs unaffected); no fixture repin (`EXPECTED_LF_TRAINING` pins only training sources, untouched here); record the boundary. FOLD.
- **Codex MINOR — gate composition.** Add a selected-river crossing/tunnel-gate end-to-end test. FOLD.
- **Codex MINOR — docs.** D-040; correct STATE.md's `build_tutorial` over-reach at Commit B. FOLD.
- **Codex NIT / N1 / N2 / N3.** Stale wording folded; alphabetical cycle order KEPT (both accept it, avoids a second constant); the arity + Restart NITs are subsumed by the two MAJOR folds.

## Result
Both REVISE → all folded into PLAN v2; Codex MAJOR-1 (Restart-preserves-map) is the substantive design addition; the architecture is dual-confirmed. Ready for red tests.

---

# GM-09f3 implementation — dual adversarial review synthesis

Both lanes independently confirmed the PRODUCTION code is correct on every vector (restart-preserves-map across all three surfaces, uniform seam arity, the `_title_build_game` collision fix, cycle/wrap, byte-identical rects, Continue/tutorial isolation, gate composition, RL/headless containment). The split verdict was again purely TEST STRENGTH.

- Harness (`raw/impl-harness.md`, **SHIP**): no BLOCKER/MAJOR; 1 MINOR — mutation-testing showed `main.run_game`'s `build_game` `map_by_id` resolution had no end-to-end coverage (a regression to "always Classic" stayed green). Probed all three restart paths + Continue + tutorial + gate live.
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST**): 1 MAJOR + 2 MINOR, all mutation-resistance — production verified correct (its probes built `["classic","river"]` and a river crossing moved tunnels 0/3→1/2). All folded (test-only, no production change):
  - **MAJOR (Codex) = harness MINOR** — the gate test built River directly, bypassing selection + `main`; a `map_by_id`→Classic regression kept all tests green. **FOLD**: `test_run_game_selection_builds_a_real_river_mediator_end_to_end` drives the REAL `main.run_game` through Map×3 → New Game with a real `Mediator`, asserts the selection-built mediator's `map_definition == RIVER`, AND runs the crossing gate on THAT mediator (tunnels 0→1).
  - **MINOR (Codex) — game-over MOUSE Restart (:331) not distinctly covered** (only K_r). A regression to that one branch using the picker stayed green. **FOLD**: `test_game_over_mouse_restart_after_continue_keeps_the_loaded_map` (Continue river, picker=lake, game-over click→Restart → river).
  - **MINOR (Codex) — render test checked relative ordering, not exact rects** (a 1px whole-stack shift passed). **FOLD**: pin the five exact pre-map `pygame.Rect` values + the appended map rect.
- BOTH lanes noted a subagent's `git checkout -- src/main.py` transiently reverted the uncommitted work; both restored + re-gated. Independently re-verified here: full suite green (1474), `src/main.py:221` has `Mediator(map_definition=map_by_id(map_id))`, diff intact.

## Result
Harness SHIP + Codex FIX-FIRST → production correct by BOTH; the MAJOR (end-to-end mutation gap) + 2 MINOR mutation-resistance gaps folded (test-only), so a `map_by_id`-drop, a game-over-click-restart-uses-picker, and a title-rect-drift regression now each fail the suite. Post-fold: focused 14/14, full suite **1474/0** (12 skips), ruff + format + pre-commit clean. Ready to deliver [GM-09f3:A] — COMPLETING GM-09f.

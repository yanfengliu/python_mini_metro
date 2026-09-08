# GM-09f3 PLAN review — in-game map menu (D-040) — harness general-purpose lane (agentId a9b998786bbbc1a9d)

Verified against live code at `src/app_controller.py`, `src/main.py`, `src/ui/menu_screens.py`, `src/maps.py`, `src/mediator.py`, `src/rl/player_env.py`, and the full test suite. The core design is sound; one concrete gap will turn the suite RED if the plan is followed literally.

## BLOCKER — None.

## MAJOR

**M1 — the "8 build_game fakes" enumeration is incomplete: it omits `test/test_gm07a_pause_menu_arming.py`, whose zero-arg fake is reached by Restart.**
- `test_gm07a_pause_menu_arming.py:61` defines `def build():` (zero params) via `_factory`, passed to `AppController` at :79.
- `test_mid_drag_release_over_restart_is_a_no_op_until_armed` (:110-120) fires Restart (`self._up(restart)` → asserts `len(self.build.triples) == 2`). Restart routes through `_start_new_game`, which the plan changes to `self._build_game(self.current_map_id)` — a one-positional-arg call.
- Concrete break: `TypeError: build() takes 0 positional arguments but 1 was given`, the moment Restart reconstructs. RED.
- Fix: add `test/test_gm07a_pause_menu_arming.py` (`_factory.build`) to the fakes list; reword the plan to "EVERY controller `build_game` fake gains `map_id="classic"`" rather than an enumerated count of 8, so the diff/commit is scoped completely.

## MINOR — None.

## NIT
- **N1 — cycle order alphabetical surfaces DELTA before RIVER.** `KNOWN_MAP_IDS = ('classic','delta','lake','river')`; from classic the first click lands on delta (budget 4) rather than river (the intro single-river, budget 3). Functionally fine, wraps correctly; a difficulty-curated order (classic→river→delta→lake) reads better. Not a bug.
- **N2 — `__init__` zero-arg vs `_start_new_game` one-arg asymmetry is harmless but inconsistent.** Both agree (current_map_id is "classic" at construction, initial triple is a placeholder). Passing `self.current_map_id` from `__init__` too gives one call convention. Optional.
- **N3 — title label reflects the next-new-game map, not a Continue-save's map.** Acceptable — the picker seeds NEW games only; Continue is independent.

## Disposition of the attack questions
1. SEAM — no finding; explicit `build_game(map_id="classic")` is right over the closure alternative (build_game is passed INTO AppController before the controller exists → a back-reference needs a forward/nonlocal ref, a late-binding wart). Restart, game-over restart, and K_RETURN (app_controller.py:267) all funnel through `_start_new_game`, so all honor the picker. `map_by_id` resolution safe (only writer of current_map_id is `_cycle_map` over KNOWN_MAP_IDS). The cost is the wide fake update (M1).
2. CYCLE — no functional finding (N1 UX). Default classic correct; wrap correct.
3. RENDER — no finding; byte-stability holds. The 6th button ("map") top=868 bottom=932 ≤ 1080, on-screen; earlier rects byte-identical (`_stacked_buttons` positions by ordinal; heading anchors to new_game.top). No full-surface title golden or exact key-set/count test exists; per-region byte tests for new_game/continue/exit are untouched by the appended map rect. Trailing `current_map_id="classic"` default keeps every `draw_title_screen(...)` call site valid (incl. test_gm07a_menu_screens.py:175's one-arg compose). `_assert_probe_clear` iterates the map rect but probe x=12 is outside the button x-band [810,1110]. Labels fit `game_over_button_width=300` ("Exit to Title" already fits). The GM-07a run-loop `lambda surface:` stub (test_gm07a_run_game_loop.py:170) needs the kwarg (plan covers it); gm07e uses MagicMock; gm07c/gm07d exit via QUIT before any draw.
4. CONTINUE — no finding. `_continue_game` uses `self._build_from(loaded)`, never reads current_map_id; the loaded mediator carries its own deserialized map_definition. `test_gm07c_continue_roundtrip.py` has no build_game fake and no restart, unaffected.
5. TUTORIAL — no finding. `_start_tutorial` uses `build_tutorial()` (unchanged seeded Classic); current_map_id never reaches it. gm08c's fakes are never hit by `_start_new_game`.
6. BLAST — RL/headless undisturbed (`rl/player_env.py:142` and `env.MiniMetroEnv` construct `Mediator(map_definition=…)` directly; no script calls run_game/AppController). The ~4 run-loop tests needing `build_mediator(map_definition=None)` are gm07a/c/d run_game_loop + gm07e. `test_main.py` correctly needs NO change (its main.Mediator patches use return_value/bare MagicMock, and the new map_by_id call is unpatched/pure — all five sites traced). No frozen title artifact or determinism fingerprint to disturb.
7. MISSING — otherwise complete. Initial __init__ map = classic; game-over New-Game, pause Restart, and K_RETURN all honor the picker via `_start_new_game`; label fits. `main` must `from maps import map_by_id` and thread `current_map_id=controller.current_map_id` into the title-draw call (both stated).

## Verdict: REVISE
Design and architecture correct; fix the one load-bearing gap (M1): add `test_gm07a_pause_menu_arming.py` to the fake-update set and restate the blast radius as "all controller `build_game` fakes". N1-N3 optional.

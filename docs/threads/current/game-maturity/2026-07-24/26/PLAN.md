# GM-09f3 — in-game map menu (D-040)

**Roadmap:** the FINAL GM-09f sub-unit and the payoff — a title-screen map picker so a human can actually choose `river`/`delta`/`lake`. The save (GM-09f) and high-score (GM-09f2) recorders are already map-aware, so this unit adds ONLY selection. `Mediator.__init__` already accepts `map_definition` (mediator.py:91, default CLASSIC); the whole terrain/crossing/save/RL stack is already map-aware (GM-09a–f2).

## Design

### 1. Controller owns the selection (`src/app_controller.py`)
- `self.current_map_id: str = "classic"` set in `__init__` BEFORE the initial `build_game()` (mirrors `self.current_settings` — the controller owns editable title UI state).
- `_cycle_map()`: advance `current_map_id` to the next of `KNOWN_MAP_IDS` (wrap around). Import `KNOWN_MAP_IDS` from `maps` (a data tuple; `maps` is import-safe — no cycle).
- `_handle_title`: add a `_clicked(layout, "map", position)` → `_cycle_map()` branch (the existing hit-test-rect pattern, app_controller.py:273-283).
- `_start_new_game`: pass the choice — `self._build_game(self.current_map_id)`. `__init__`'s initial build stays `self._build_game()` (zero-arg → classic default; the pre-title placeholder is irrelevant — New Game rebuilds).

### 2. The `build_game` seam gains an optional map id
- Seam: `build_game(map_id: str = "classic")` (chosen: EXPLICIT param over the closure-reads-controller alternative — the factory receives its input honestly, no factory→controller back-reference/late-binding wart). `run_game`'s `build_game` (main.py:216) resolves `map_by_id(map_id)` and builds `Mediator(map_definition=...)`.
- Blast: 8 tier-A controller-test `build_game` fakes gain `map_id="classic"` (ignored) — mechanical; the ~4 run-loop tests patching `main.Mediator` with a zero-arg side-effect gain a `map_definition=None` kwarg (needed either way, since `run_game`'s factory now calls `Mediator(map_definition=...)`).
- The tutorial stays CLASSIC (`build_tutorial` unchanged — a fixed coached lesson whose steps assume the classic layout).

### 3. Rendering the picker (`src/ui/menu_screens.py` + `src/main.py`)
- `title_layout`'s key tuple APPENDS `"map"` (last, after `"tutorial"`) so `new_game`/`continue`/`exit`/`settings`/`tutorial` rects stay byte-identical (the established append rule, menu_screens.py:80-84; `_stacked_buttons` positions by ordinal).
- `draw_title_screen(surface, continue_available=False, current_map_id="classic")` draws the map button labeled with the map name (`map_id.title()` → "Classic"/"River"/"Delta"/"Lake"). The label is UNCONDITIONAL (there is always a current map), so it belongs in `draw_title_screen` (unlike Continue, which is gated on `peek_autosave` and drawn by a main helper). Fits the shared `game_over_button_width` (the four names are short); if "Map: X" overflows, use the bare name.
- `main.run_game`'s TITLE branch (main.py:373) calls `draw_title_screen(game_surface, current_map_id=controller.current_map_id)`. The GM-07a run-loop stub (`lambda surface:`, test_gm07a_run_game_loop.py:169) gains `current_map_id="classic"` (keyword-with-default, stub-compatible).

### 4. Continue is unaffected
`_continue_game` loads the saved map (GM-09f `deserialize_game` already restores `map_definition`); the picker only seeds NEW games. A test pins that Continue ignores the current picker value and loads the saved map.

## TDD (red first)

New `test/test_gm09f3_map_menu.py`:
- **Picker cycles**: clicking the title `"map"` rect advances `current_map_id` through `KNOWN_MAP_IDS` and wraps; default is `"classic"`.
- **New Game builds the chosen map**: with `current_map_id="river"`, `_start_new_game` → the built mediator has `map_definition == RIVER` (drive a real `AppController` with a spy `build_game(map_id)` capturing the id; and an integration via `main.run_game` asserting `Mediator(map_definition=...)` gets the resolved map).
- **Continue loads the SAVED map, not the picker**: a controller with `current_map_id="lake"` that Continues a river save → mediator is RIVER.
- **Tutorial stays classic**: `_start_tutorial` builds classic regardless of `current_map_id`.
- **Render**: `draw_title_screen(surface, current_map_id="river")` is deterministic and paints the map button into `title_layout["map"]`; the label reflects the id; earlier title rects are byte-identical to the pre-map layout.
- **End-to-end**: select a non-classic map → New Game → the frame shows that map's terrain (surface probe: the terrain renderer painted for the chosen map).

Touched (mechanical): the 8 tier-A `build_game` fakes (+`map_id="classic"`); the run-loop `main.Mediator` side-effects (+`map_definition=None`); `test_gm07a/gm07c_menu_screens.py` (add `"map"` to the title key sets — earlier rects unchanged); the GM-07a run-loop `draw_title_screen` stub (+`current_map_id`).

## Docs
- D-040 (this decision). README (title map picker; how to select). GAME_RULES (map selection on New Game; each map's character already documented). ARCHITECTURE (the `build_game(map_id)` seam + the title `"map"` control; GM-09f COMPLETE). PROGRESS.

## Risk / review
HIGH-RISK (public entry-point `run_game` + a new UI boundary + the seam change) → dual PLAN review then dual IMPL review. Verify: terrain renders for the chosen map end-to-end; Continue still loads the saved map; the append keeps earlier title rects byte-identical; the tutorial stays classic; no RL/headless path is disturbed (they never build via the title picker — `env`/`player_env` construct `Mediator(map_definition=...)` directly).

## Order
seam + controller selection + cycle (red tests) → menu layout/render → main wiring → docs → dual impl review → A (CI) → B. This COMPLETES GM-09f; GM-10 (weekly progression) opens next.

---

## PLAN v2 — folds (after dual plan review)

Both lanes **REVISE**, both VALIDATED the architecture (explicit-param seam is right; append preserves prior rects — the new "map" rect is `(810,868,300,64)`, bottom 932 ≤ 1080, and "Map: Classic" is 174px in the 300px button; Continue installs the save-restored map via `build_from`; tutorial stays Classic; RL/headless construct `Mediator(map_definition=…)` directly and are undisturbed). Codex caught a real design MAJOR the harness rated N3-acceptable. All folded:

- **MAJOR (Codex M1) — RESTART must preserve the CURRENT game's map, not the picker.** VERIFIED: picker=`lake`, Continue a River save (`_continue_game` swaps in the river mediator), then Restart → naive `_build_game(current_map_id)` builds LAKE. **Fold**: `_start_new_game(map_id)` takes an explicit id; the NEW-GAME surfaces (`_handle_title` new_game + K_RETURN, app_controller.py:268/275) pass `self.current_map_id` (the picker); the RESTART surfaces (pause restart :254, game-over R :290, game-over restart :300) pass `self.mediator.map_definition.map_id` (the live game's map — authoritative, no extra tracking field). Restart-path fake mediators (`test_gm07a_pause_menu_arming`, `test_gm07a_app_controller` game-over restart, `test_gm07e`) gain a `map_definition`. Test BOTH pause-Restart and game-over-Restart after Continue.
- **MAJOR (Codex M2 / harness M1) — uniform seam arity.** **Fold**: set `self.current_map_id = "classic"` in `__init__` BEFORE the initial build, and call `self._build_game(self.current_map_id)` there too, so the seam is uniformly `Callable[[str], GameTriple]` — every call passes one id, no arity split.
- **MINOR (Codex) — the fake update is 11 factory callables, not "8 files".** **Fold**: update EVERY controller `build_game` factory (grep-driven, not enumerated) to `def build_game(map_id="classic")` — the 7 files the harness/Codex list, incl. `test_gm07a_app_controller` (2 fakes), `test_gm07c_continue_roundtrip` (2), `test_gm08c_tutorial_app` (2). **`_title_build_game(mediator=None)` (test_gm07c_continue_roundtrip:164) is DANGEROUS** — a positional `"classic"` becomes its `mediator`; give it a leading `map_id="classic"` param (ignored) so `build_game(map_id)` binds correctly.
- **MINOR (Codex) — RL content-fingerprint rotates.** Editing `app_controller`/`main`/`menu_screens` (all in `compute_content_fingerprint`'s `src/**`) rotates the environment-content fingerprint, so a pre-GM-09f3 manifest fails resume/eval with `content fingerprint mismatch` by default. **Fold**: this is EXPECTED and correct (no `--allow-content-drift` needed for fresh runs); VERIFY no test pins the full-src fingerprint (`EXPECTED_LF_TRAINING` pins only `TRAINING_SOURCE_PATHS`, which this unit does NOT touch — no rl/ edits), so no fixture is repinned; RECORD the boundary in EVIDENCE.
- **MINOR (Codex) — prove the crossing/tunnel GATE composes with selection, not just terrain.** **Fold**: add a test that selecting `river` → New Game → a committed crossing line consumes a tunnel and the budget gate applies (the gate is already per-map-tested in GM-09c/d/e; this pins that SELECTION reaches it end-to-end).
- **MINOR (Codex) — docs.** **Fold**: add D-040 to DECISIONS; STATE.md's GM-09f3 resume note (:25) currently over-reaches ("thread into `build_game`/`build_tutorial`") — correct it to `build_game` only (the tutorial stays Classic) at Commit B when STATE is rewritten.
- **NIT (Codex) — stale wording** (the title stub is no longer single-arg; `env.py` uses bare Classic mediators while `rl/player_env.py` passes `map_definition`). **Fold** into the docs wording.
- **N1 (harness) — cycle order.** NOT folded: both lanes accept alphabetical (`classic→delta→lake→river`); Codex confirmed it "violates no curated-order contract" and is deterministic. Keeping `KNOWN_MAP_IDS` order avoids a second ordering constant (and a needless `maps.py` fingerprint touch). Accepted as-is; default `classic` correct.
- **N2/N3 (harness) — superseded**: N2 (arity asymmetry) is fixed by the uniform-arity fold; N3 (Restart uses picker) is fixed by the Restart-preserves-map fold.

Label: "Map: {Name}" (`map_id.title()`), fits the 300px button. Revised touched set: `app_controller.py`, `main.py`, `menu_screens.py`; the 7 controller-fake files + the ~4 run-loop `main.Mediator` side-effects + the GM-07a `draw_title_screen` stub; new `test_gm09f3_map_menu.py`.

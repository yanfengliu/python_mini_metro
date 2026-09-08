BLOCKER — no findings.

## Findings

- **MAJOR** — [app_controller.py:189](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:189), [app_controller.py:252](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:252), [app_controller.py:285](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:285) — Restart can silently switch maps after Continue. Concrete state: picker=`lake`; Continue loads a River save; Pause→Restart, game-over `R`, or game-over Restart all call the planned `_build_game(self.current_map_id)`, starting Lake instead of restarting River. Fix: make `_start_new_game(map_id)` explicit—title click/Enter pass the picker, while restart surfaces pass the live mediator’s map—or separately track the active map. Test both pause and game-over restart after Continue.

- **MAJOR** — [app_controller.py:79](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:79), [app_controller.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:115), [PLAN.md:11](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-24/26/PLAN.md:11) — the proposed factory contract has two arities. The plan’s `def build_game(map_id)` spy fails during construction because `__init__` calls it with zero arguments; a legacy zero-argument factory constructs successfully and then fails on New Game/Restart. Fix: initialize `current_map_id` first, uniformly call `build_game(map_id)`, and type the seam `Callable[[str], GameTriple]`. The explicit-parameter seam is preferable to the controller-reading closure.

- **MINOR** — [PLAN.md:15](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-24/26/PLAN.md:15) — “8 fakes” is eight test modules, but the uniform seam reaches **11 factory callables**:

  - [test_gm07a_app_controller.py:170](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07a_app_controller.py:170) and line 431
  - [test_gm07a_pause_menu_arming.py:61](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07a_pause_menu_arming.py:61)
  - [test_gm07c_autosave_controller.py:155](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07c_autosave_controller.py:155)
  - [test_gm07c_continue_roundtrip.py:164](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07c_continue_roundtrip.py:164) and line 178
  - [test_gm07d_recorder_controller.py:119](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07d_recorder_controller.py:119)
  - [test_gm07e_game_over_reconcile.py:135](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07e_game_over_reconcile.py:135)
  - [test_gm08a_settings_controller.py:52](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings_controller.py:52)
  - [test_gm08c_tutorial_app.py:60](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08c_tutorial_app.py:60) and line 98

  `_title_build_game(mediator=None)` is especially dangerous: passing `"classic"` positionally makes the string the fake mediator.

- **MINOR** — [PLAN.md:42](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-24/26/PLAN.md:42), [training.py:296](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/training.py:296), [manifest.py:231](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest.py:231) — runtime RL/headless construction is isolated, but its provenance is not unchanged: all three edited `src` files rotate the environment-content fingerprint. A pre-GM-09f3 manifest then fails resume/evaluation by default with `content fingerprint mismatch` unless content drift is explicitly allowed. Record this expected boundary; no frozen fixture should be repinned.

- **MINOR** — [STATE.md:25](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:25), [PLAN.md:34](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-24/26/PLAN.md:34) — the accepted roadmap requires both selected terrain and the crossing/tunnel gate end-to-end; the plan tests only terrain. Add a selected-River flow that reaches the real tunnel-budget rejection, or explicitly prove composition with the existing gate contract.

- **MINOR** — [STATE.md:25](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:25), [PLAN.md:16](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-24/26/PLAN.md:16) — the canon currently says the chosen map threads into `build_tutorial`, contradicting the plan’s correct fixed-Classic tutorial. Add `STATE.md` and `DECISIONS.md` D-040 explicitly to the docs edits.

- **NIT** — [main.py:172](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:172), [PLAN.md:42](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-24/26/PLAN.md:42) — update stale wording: the title stub will no longer be single-argument, and only `rl/player_env.py` directly passes `map_definition`; `env.py` uses bare Classic mediators while recursive/agent paths construct `MiniMetroEnv`.

## Verified clean

- Alphabetical cycling `classic → delta → lake → river` is deterministic and violates no existing curated-order contract; Classic is the correct default.
- Appending `"map"` preserves every prior rect. The new rect is `(810, 868, 300, 64)`, bottom `932`; `Map: Classic` is only 174 px wide in the 300 px button.
- Existing menu tests pin repeatability, not a historical screen hash.
- Immediate Continue correctly installs the save-restored map through `build_from`; the picker does not override it.
- Tutorial remains Classic and cannot read picker state.
- Enter shares the New Game helper, so it is not a bypass once map sourcing is corrected.
- Exactly four strict `main.Mediator` side effects need the new keyword; the other patches are permissive mocks. Only one strict title-draw stub needs updating.
- Save/checkpoint/legacy-manifest and gameplay determinism fixtures remain unchanged.

Severity totals: **BLOCKER 0, MAJOR 2, MINOR 4, NIT 1**.

REVISE

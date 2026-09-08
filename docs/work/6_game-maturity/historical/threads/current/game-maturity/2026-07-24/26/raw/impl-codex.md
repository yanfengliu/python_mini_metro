FIX-FIRST. Live production behavior is correct, but the required mutation resistance has one MAJOR and two MINOR gaps.

### Findings

- MAJOR — [test_gm09f3_map_menu.py:246](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09f3_map_menu.py:246), seam [main.py:217](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:217) — select River, then regress `main.map_by_id` to return Classic → the human game runs Classic without River terrain/tunnels, while all 12 GM-09f3 tests still pass → drive real `main.run_game` through Map → New Game, assert `Mediator(map_definition=RIVER)`, and use that mediator for the crossing assertion. The current “gate composition” test constructs River directly, bypassing selection and `main`.

- MINOR — [test_gm09f3_map_menu.py:137](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09f3_map_menu.py:137), branch [app_controller.py:326](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:326) — picker=Lake, Continue River, then regress only game-over mouse Restart to use the picker → click Restart rebuilds Lake, while 37 relevant tests remain green → add a distinct-map Continue → game-over-click → Restart assertion expecting River.

- MINOR — [test_gm09f3_map_menu.py:237](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09f3_map_menu.py:237) — shift every title rect by one pixel → the five established hitboxes are no longer byte-identical, but 21 GM-09f3/GM-07a/GM-07c menu tests pass because the assertion checks only relative ordering → pin the five exact pre-map `pygame.Rect` values.

BLOCKER — no findings.
NIT — no findings.

### Verified

- All five live call sites are correct: New Game and Enter use the picker; pause Restart, game-over `R`, and game-over click use the live mediator’s map.
- Picker Lake + Continued River probes produced River for all three restart paths; later New Game produced Lake; Tutorial produced Classic.
- Uniform one-argument seam, `_title_build_game` collision fix, all controller factories/run-loop fakes, and production `map_definition` availability are correct.
- Cycle: `classic → delta → lake → river → classic`.
- Prior rects exactly match baseline; Map rect is `(810, 868, 300, 64)` and on-screen. Maximum label width is 174px inside the 300px button. Rendering is deterministic.
- Real headless `main.run_game` selection built `["classic", "river"]`; a River crossing changed tunnels from consumed/available `0/3` to `1/2`.
- Structured and pixel/RL entry points remain independent of the picker.

Validation:

- Focused suite: 50/50 passed.
- Full suite: 1,472 run; 1,460 passed, 12 expected skips, 0 failures/errors.
- A transient concurrent revert of `main.py` was restored; both gates were rerun afterward against the current live tree.
- The external multi-CLI lane was denied because transmitting the live repository lacked explicit authorization; three independent in-platform reviewers and mutation probes were used instead.
- No repository files were edited.

Verdict: **FIX-FIRST**

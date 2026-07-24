FIX-FIRST. I reproduced no production-code defect, but six MAJOR regression-test gaps allow load-bearing plan-review folds to be removed while the suite remains green.

## Findings

BLOCKER — none.

- MAJOR — [test/test_gm10a_calendar.py:254](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:254) — mutate Main’s builders to always enable `week_calendar`; `run_game(max_frames=1201)` and a long tutorial freeze at step 1200 with no resolving driver, while 25 relevant tests still pass → the critical interactive-only gate, `build_from`, PlayerPixelEnv, and pre-calendar byte-equivalence are unpinned → test bounded/unbounded `build_game` and `build_from`, tutorial and PlayerPixelEnv beyond 1200, plus a frozen pre-calendar checkpoint/observation fixture.

- MAJOR — [test/test_gm10a_calendar.py:109](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:109) — place an empty queued-return Metro at `segment_end` for the `1199 → 1200` tick, then move the hold before final settlement; all 14 GM-10a tests pass, but the Metro remains assigned and available locomotives stay 3 instead of the correct detached/4 → the hold-placement fold is not tested → construct that exact queued-arrival state and compare the complete normalized state against calendar-off after resolving. More random seeds alone do not fix this.

- MAJOR — [test/test_gm10a_calendar.py:99](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:99) — steps 1199, threshold 1, one rider at wait 983/limit 1000, then `dt_ms=17`; deleting the game-over guard leaves both game-over and week pending, yet all 14 tests pass because the current test pre-sets game-over and therefore never advances or crosses a boundary → terminal precedence is vacuously tested → create the simultaneous transition and assert GAME_OVER promotion plus record/delete-on-QUIT.

- MAJOR — [test/test_gm10a_calendar.py:53](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:53) — speed 4 from steps 1199 jumps to 1203; an exact-landing-only boundary mutant skips the offer while all 14 tests pass → the speed-jump contract is unpinned → cover residues 1196–1199, frozen ticks, resume, and the second boundary.

- MAJOR — [test/test_gm10a_calendar.py:175](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:175) — promote while a path-creation/redraw/handle/resource gesture is active; replacing the off-viewport `MOUSE_UP(-1,-1)` with `None` still satisfies the length-only assertion, leaving stale gesture state that can mutate gameplay after Continue → cancellation semantics are not tested → assert the exact event and exercise all four real gesture states with zero route/fleet/resource mutation.

- MAJOR — [test/test_gm10a_calendar.py:174](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:174) — no GM-10a test drives OFFER through `main.run_game`; deleting the OFFER QUIT branch exits without resolving/autosaving, deleting the audio snapshot causes a post-Continue burst, and deleting the render branch makes the modal invisible → three prior-review shell folds are unpinned → add run-loop promotion/render, silent-audio/no-burst, and OFFER-QUIT tests with both absent and existing autosaves.

MINOR — none.

NIT — none.

## Live behavior verified

- Only [src/main.py:233](C:/Users/38909/Documents/github/python_mini_metro/src/main.py:233) and [src/main.py:243](C:/Users/38909/Documents/github/python_mini_metro/src/main.py:243) enable the calendar. MiniMetroEnv, PlayerPixelEnv, tutorial, agent-play, recursive-playtest, saves loaded outside Main, and frame-limited Main remained calendar-off past step 1200.
- Final settlement precedes the hold. Seeds 0, 1, 2, 42, and 6309 matched calendar-off controls; the constructed queued-return seam also settled correctly.
- Speed-4 crossing held once; frozen ticks did not retrigger.
- The simultaneous terminal transition promoted GAME_OVER, not OFFER. QUIT recorded once and deleted the autosave.
- MagicMock truthy attributes stayed out of OFFER; real gesture probes cancelled cleanly; Continue required an OFFER-local down/up.
- Pending-week saving failed before touching the destination; `"week"` remained invalid save vocabulary; mid-week load derived the correct `week_index`; OFFER QUIT resolved then autosaved past the boundary.
- OFFER audio consumed deltas silently without a later burst. Headless runs retained NullAudio.
- A canonical checkpoint at step 1260 exactly matched a dynamically loaded pre-change `HEAD` control; no week state entered observations, saves, or checkpoints.

Mutation results: (a) settlement move survived; (b) game-over guard removal survived; (c) default-True was caught; (d) truthy weakening survived the GM-10a file but was caught by the broader MagicMock suite; (e) the `<` comparator mutation was caught. The separate speed exact-landing mutant survived.

Validation completed:

- GM-10a: 14/14 passed.
- Full suite: 1491 passed.
- RL contracts: 139 passed.
- Fresh/resumed recurrent, named-history, and legacy-PPO train/evaluate smoke: all 12 commands passed.
- Ruff check and format check: 7/7 files clean.
- Installed missing hash-pinned `sb3-contrib==2.9.0`; all task-owned smoke outputs were removed.
- No repository files were changed.

The configured external multi-CLI lane could not run because repository transmission was not authorized; three independent local adversarial lanes, mutation probes, and live-code verification were used.

**FIX-FIRST**

## CONFIRMED

- **MAJOR — instructed reroute can permanently soft-lock.** The prompt says to select a line “by tapping it” ([tutorial.py:89](/C:/Users/38909/Documents/github/python_mini_metro/src/tutorial.py:89)), but drawn routes are not hit-tested; tapping the assigned line button deletes it ([input_coordinator.py:240](/C:/Users/38909/Documents/github/python_mini_metro/src/input_coordinator.py:240), [input_coordinator.py:341](/C:/Users/38909/Documents/github/python_mini_metro/src/input_coordinator.py:341)). Reroute only recognizes changes to the baseline path ID ([tutorial.py:52](/C:/Users/38909/Documents/github/python_mini_metro/src/tutorial.py:52)); replacement lines receive fresh IDs. Real mouse-event reproduction remained on step 2 after deletion, drawing a replacement, and successfully rerouting that replacement.

- **MAJOR — train step can permanently baseline at the locomotive cap.** While reroute is active, the player can assign all four locomotives because controls are ungated. A continuity-preserving A-B→A-B-C redraw still succeeds with four trains, after which progress records `metros=4` as the train baseline ([tutorial.py:199](/C:/Users/38909/Documents/github/python_mini_metro/src/tutorial.py:199)). Train requires `current > baseline` ([tutorial.py:44](/C:/Users/38909/Documents/github/python_mini_metro/src/tutorial.py:44)), but inventory is capped at four ([config.py:61](/C:/Users/38909/Documents/github/python_mini_metro/src/config.py:61), [fleet_management.py:194](/C:/Users/38909/Documents/github/python_mini_metro/src/fleet_management.py:194)). Returning and reassigning cannot ever exceed the stored baseline.

- **MODERATE — explicit tutorial startup constructs an ordinary, frozen-prone game.** `AppController(start_state=TUTORIAL)` records that state but unconditionally calls `build_game()` and leaves tutorial progress unset ([app_controller.py:102](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:102), [app_controller.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:115)). Thus documented `run_game(start_state=AppScreen.TUTORIAL)` has threshold 2 and no overlay. A live 90-second probe reached game over; reconciliation ignored it because only `PLAYING` promotes, leaving a frozen `TUTORIAL` loop showing game-over chrome. The new test at `test_gm08c_tutorial_main.py:131-136` masks this by checking only that `advance_tutorial` was called.

## REFUTED

- Normal menu launch correctly installs the seeded threshold-`10**9` mediator. The threshold is writable, and `passenger_flow.py:451-463` is the only live game-over transition.
- Seed 42 produces Triangle/Rect/Cross. Every two-station pairing delivered within 6.234–13.550 simulated seconds; invalid one-station gestures cannot commit.
- Paused overload dwell does not accumulate and remains recoverable with Space. One post-tick call advances at most one step; no stale snapshot, double advance, or real-state snapshot crash was found.
- Isolation holds: only `app_controller` imports `tutorial`, only `main` imports `app_controller`, and the forbidden scan includes `tutorial`.
- Prior title rectangles are unchanged. The overlay is byte-stable, on-screen, and rendered after gameplay. Tutorial Escape/QUIT does not autosave or record.
- Focused GM-08c/isolation/legacy-menu suite: **43/43 passed**, but it does not cover the counterexamples above.

**NOT CLEAN — two reachable MAJOR permanent soft-locks and one MODERATE frozen direct-start path.**

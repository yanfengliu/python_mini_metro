# GM-06a red-first implementation evidence

## Combined product red

Command: `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest test.test_gm06a_locomotive_inventory test.test_gm06a_inventory_state test.test_gm06a_inventory_rendering`

Result before production implementation: `Ran 34 tests in 0.425s`, `FAILED (failures=20, errors=13)`. All 13 errors were missing `Mediator.available_locomotives`. The 20 failures were the missing read-only enforcement and structured fleet surface, missing third HUD line/count glyph in fast and fidelity observations, and the still-old `(0, 0, 700, 140)` exclusion. The two baseline-only geometry/purity methods passed.

The runtime lane separately applied only an in-memory `max(0, num_metros - len(metros))` property shim and passed all 13 methods. The state lane separately simulated only the planned read-only property plus structured fleet object and passed all 16 methods. These checks proved the tests did not require lifecycle, entity, checkpoint, replay, action, or protocol changes.

## Focused product green

Command: `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v test.test_gm06a_locomotive_inventory test.test_gm06a_inventory_state test.test_gm06a_inventory_rendering`

Result after the four planned production surfaces: `Ran 34 tests in 0.359s`, `OK`.

## Adjacent compatibility green

Command: `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest test.test_game_renderer test.test_path_handles test.test_player_env test.test_env test.test_recursive_checkpoint test.test_gm05c_pixel_equivalence test.test_gm05c_state_equivalence test.test_gm06a_locomotive_inventory test.test_gm06a_inventory_state test.test_gm06a_inventory_rendering`

The first directly affected run found only two stale two-line `test_game_renderer` expectations. After those existing tests were updated to the accepted three-line behavior and locomotive pixel sensitivity, the definitive adjacent run passed `119` tests in `1.343s` with no failures.

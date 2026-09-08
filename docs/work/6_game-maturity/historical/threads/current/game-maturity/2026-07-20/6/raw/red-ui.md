# GM-06b controls and PlayerPixel red

Command: `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v test.test_gm06b_fleet_controls test.test_gm06b_fleet_rendering test.test_gm06b_fleet_player_pixels test.test_rl_demonstrator`

Result: 24 tests ran in 1.680 seconds; expected product red with 19 failures and one error. The gaps were absent FleetButtons/input adapter, release/action dispatch, privileged control coordinates, queue marker/styles/profile pixels, public assignment, and demonstrator assignment clicks. Six unchanged protocol/determinism/helper checks stayed green. A first harness-only invalid station index was corrected before this recorded run; all remaining failures were product gaps.

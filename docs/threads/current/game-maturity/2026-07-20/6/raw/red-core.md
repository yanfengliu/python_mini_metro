# GM-06b core fleet red

Command: `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v test.test_gm06b_fleet_assignment test.test_gm06b_fleet_queue`

Result: 29 test methods ran; expected product red with 5 failures and 30 subtest/errors. The gaps were missing public assignment/queued-unassignment methods, missing default queue state, transitional automatic allocation, and unblocked boarding permission/candidate/dwell paths. Both test files passed exact Ruff check/format and scoped whitespace checks.

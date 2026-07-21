# GM-06b focused green

Command: `$env:PYTHONHASHSEED='0'; C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest discover -s test -p "test_gm06b_*.py" -v`

Result: 72 test methods ran in 1.307 seconds; all passed. The three methods added from implementation review close synthetic-padding stopping, locked-purchase text overlap, and malformed geometry reaching Metro construction.

Command: `node --test test/gm06b-replay-contract.test.mjs`

Result: four tests passed in 115.8305 milliseconds. Exact checkpoint/fixture bytes, default v4 index assignment, literal v1/v2/v3 Node projection, and complete v4 projection all passed.

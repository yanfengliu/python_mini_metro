# GM-06c combined RED baseline

Status: recorded; production implementation gate open

Environment: `C:\Users\38909\miniconda3\envs\py313\python.exe`, pygame-ce 2.5.7, Python 3.13.10, Node test runner from the repository environment.

Python command:

`python -m unittest discover -s test -p "test_gm06c_*.py" -v`

Result:

`Ran 150 tests in 2.780s`

`FAILED (failures=132, errors=107)`

The counts include passing frozen historical controls. Failures/errors are the independently reviewed intended product RED: absent Carriage/CarriageManagement/Mediator composition surfaces, fixed-capacity/aggregate-dwell behavior, absent consist/control/pixel/checkpoint-v4/recursive-v5/agent-v5 behavior, and exact negative assertions against the pre-GM-06c implementation. There was no collection or syntax harness failure.

Node command:

`node --test test/gm06c-historical-compatibility.test.mjs test/gm06c-checkpoint-replay.test.mjs`

Result:

`tests 4; pass 2; fail 2`

The two historical v1-v4 controls pass. The two intended product-red failures show that Node currently drops the v5 reward/threshold/fleet/carriage contracts and still redrives the default as schema 4 instead of schema 5.

The three final independent RED gates are `CLEAN`; production files remained unchanged through this baseline.

# GM-06b checkpoint and replay red

Python command: `$env:PYTHONHASHSEED='0'; C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v test.test_gm06b_checkpoint_contract test.test_gm06b_replay_contract`

Python result: 22 test methods ran in 0.090 seconds; expected product red with 22 failures and 3 subtest/errors. Frozen checkpoint-v1/v2 bytes and the six-lane nonzero-dt legacy oracle remained green. Missing behavior was checkpoint v3 queue/fleet/prefix validation, old-encoder queue refusal, recursive/agent v4, index-only persisted fleet actions, preflight rejection, and the shared pre-tick compatibility adapter.

Node command: `node --test test/gm06b-replay-contract.test.mjs`

Node result: four tests ran in 119.4307 milliseconds; three frozen-byte/default-v4/literal-v1-v3 tests passed and the one intended v4 verifier-projection test failed because all three v4 fields were dropped.

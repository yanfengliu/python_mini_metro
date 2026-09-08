# GM-06b corrective A2 local green

- Targeted checkout-identity command: `$env:PYTHONHASHSEED='0'; C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v test.test_gm06b_fleet_player_pixels.TestGM06bFleetPlayerPixels.test_player_protocol_info_actions_and_task_identities_remain_exact test.test_gm06b_fleet_player_pixels.TestGM06bFleetPlayerPixels.test_canonical_lf_training_sources_retain_exact_fingerprint`.
- Targeted result: two tests passed in 0.353 seconds. The portable projection requires exact canonical-LF fingerprint `f6fa3ad50bb992152ea0f24dff35603e8e906714cf58c5fcc359ede4af54f65c`; changing only the copied `src/rl/training.py` line endings from LF to CRLF changes the production fingerprint, so production raw-byte sensitivity remains covered without pinning the live checkout.
- Focused command: `$env:PYTHONHASHSEED='0'; C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest discover -s test -p "test_gm06b_*.py" -v`.
- Focused result: 73 tests passed in 1.397 seconds.
- Definitive command: `$env:PYTHONHASHSEED='0'; C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
- Definitive result: 826 tests passed in 9.509 seconds with 12 expected optional-stack skips.
- Node replay command: `node --test test/gm06b-replay-contract.test.mjs`.
- Node replay result: four tests passed in 123.366 milliseconds.
- Static commands: `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff check test/test_gm06b_fleet_player_pixels.py` and `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff format --check test/test_gm06b_fleet_player_pixels.py`.
- Static result: Ruff check passed and the file was already formatted.
- Exact-file hook command: `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files` followed by the exact nine corrective paths, with a task-owned `PRE_COMMIT_HOME` and command-local Git safe-directory configuration.
- Exact-file hook result: EOF, trailing whitespace, Ruff, and Ruff format passed without edits; YAML correctly skipped because the corrective payload has no YAML file.
- Independent review result: both focused live-code/evidence reviewers returned final `CLEAN`; one additionally mutated every one of the 18 declared training inputs and confirmed the canonical projection rejected each mutation.

The pre-Commit-A `raw/green-combined.md` and `raw/green-full.md` records remain unchanged historical evidence. Corrective A2 changes only this test and transaction evidence; no production file changed. The successful `C:\tmp` hook cache was removed. The interrupted sandbox bootstrap's unreadable two-repository cache resisted both deletion and ownership repair, so its exact root was moved out of the repository to `C:\tmp\python-mini-metro-precommit-gm06b-a2-acl-blocked`; it is absent from Git status/staging and retained only for later ACL-capable cleanup.

# RL framework acceptance evidence

## Environment and dependency integrity

- The managed shared `py313` environment is read-only in this sandbox, so `requirements-rl-locked.txt` was installed into the ignored `output/venv-rl` environment built from that interpreter; `pip check` reported no broken requirements. The mandated direct `C:\Users\38909\miniconda3\envs\py313\python.exe` then ran the full suite with `PYTHONPATH` pointed at those exact locked workspace site-packages, proving Python 3.13.10 with Gymnasium 1.3.0, Stable-Baselines3 2.9.0, and Torch 2.13.0+cpu: 305/305 tests passed.
- Runtime versions were Gymnasium 1.3.0, Stable-Baselines3 2.9.0, TensorBoard 2.21.0, Torch 2.13.0+cpu, NumPy 2.5.1, pygame-ce 2.5.7, Shapely 2.1.2, and shortuuid 1.0.13.
- `uvx --from pip-audit pip-audit -r requirements-locked.txt --disable-pip` reported `No known vulnerabilities found`.
- `uvx --from pip-audit pip-audit -r requirements-rl-locked.txt --disable-pip` reported `No known vulnerabilities found`.
- `npm audit` in this repository reported zero vulnerabilities. The separately pinned civ-engine dependency installed with nine moderate advisories in its own dependency tree; python_mini_metro does not own or alter that external lock in this change.

## Automated validation

- With `PYTHONPATH` set to `output\venv-rl\Lib\site-packages` plus the repository root, `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: 305/305 passed with no skips, including the fresh-process pixel determinism check across different `PYTHONHASHSEED` values.
- `output\venv-rl\Scripts\python.exe -m unittest -v test.test_player_env test.test_rl_demonstrator test.test_rl_artifacts test.test_rl_cli test.test_rl_evaluation test.test_rl_manifest test.test_rl_protocol test.test_rl_training`: 62/62 passed, including direct Gymnasium contracts, real SB3 callback reseeding, exact-byte manifest/index/model loading, protected output paths, and final provenance recapture.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff check .`: passed for all 94 Python files.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff format --check .`: passed for all 94 Python files.
- `git diff --check`: passed.
- In-session direct invocations of the checked-out pre-commit hook implementations passed at the pre-review checkpoint across 209 text files. The final mechanical recheck passed Ruff lint/format, three YAML files, and trailing-whitespace/end-of-file validation across all 96 changed non-raw text files. During the actual commit hook, `end-of-file-fixer` appended terminators to the two UTF-16 Claude limit messages without changing their textual payload; the hook then passed. The earlier isolated `pre-commit run --files ...` wrapper attempts could not finish creating their private hook environments in the sandbox and were terminated after two approximately ten-minute stalls; no project hook failed.

## Real RL lifecycle

- A fresh two-worker spawned PPO run completed 256 requested timesteps with evaluations at 128 and 256 steps, then authenticated and evaluated its final model. The recorded standalone evaluation seed and terminal seed were both 10042.
- A resume run loaded the exact authenticated parent bytes, used requested seed 77, carried parent manifest SHA-256 `75a4f15af8315cc91548cd8e41ac62a114f01b54b50ef3613cafd156a524e9d2` and parent model SHA-256 `1038c99043da5d26ac6ac1831f42351bf4bdac646bcadeee365e20f9a99d9e54`, emitted the `resumed-training` tag, and completed at 512 cumulative PPO timesteps. Its recorded evaluation seed and terminal seed were both 10077.
- The fresh evaluation bound manifest SHA-256 `75a4f15af8315cc91548cd8e41ac62a114f01b54b50ef3613cafd156a524e9d2`, artifact-index SHA-256 `0371390c13244b21a951397892f1d18263da36097fd314bf2bcab928a2482606`, and final-model SHA-256 `1038c99043da5d26ac6ac1831f42351bf4bdac646bcadeee365e20f9a99d9e54` from one captured byte snapshot apiece.
- The resumed evaluation bound manifest SHA-256 `53e98a9c8e8e5b42e3029cbb49f9635af9ebd295acfed62bb8893f6e2ddb91a1`, artifact-index SHA-256 `92a44624c34e67de70e774d423b7d0e5be5b0e12e469abbdf0bc8d24be31d4ff`, and final-model SHA-256 `9ec200c6faa1f8d19cedb93a8879475c8f360f802667aafa0088da8fb2101540`.
- Selecting the authenticated model as the evaluation output exited 2 without changing model SHA-256 `1038c99043da5d26ac6ac1831f42351bf4bdac646bcadeee365e20f9a99d9e54`. A copied then tampered model exited 2 before load with `artifact size does not match index` and wrote no result. Independent in-process verifier injections after evaluation proved content, trainer-source, and runtime recapture each fails closed and writes no result.
- A session-observed 200-decision diagnostic completed in 0.8620 seconds (232.01 decisions/second); working set moved from 54.95 MiB to 55.18 MiB, process peak was 56.02 MiB, and tracemalloc peak was 0.24 MiB. This probe is diagnostic evidence, not a release gate.

## Node and recursive compatibility

- A temporary sibling layout checked out the repository-pinned civ-engine revision `e0cb614a516c449159a4562c2ac45bd40bffd3df` (version 2.2.0), installed and built it, then ran 41/41 Node tests successfully under local Node 24.12. The workflow's Node 22 execution is a pushed-CI gate rather than part of this local evidence.
- Local recursive run `recursive-2026-07-11T05-56-12-589Z-e61b4012` produced `no-fix-candidate`, replayed 8/8 cases exactly, reported zero findings, and passed its declared gates. Its provenance correctly records `worktreeDirty: true`; the required clean default pass occurs only after the prospective commit. This proves the bounded recorded scenarios stayed deterministic; it does not claim broader gameplay completion.

Ignored acceptance artifacts remain under `output/rl/final-fresh`, `output/rl/final-resumed`, and `output/node-pinned-acceptance-20260710-225410`; they are evidence inputs, not committed deliverables.

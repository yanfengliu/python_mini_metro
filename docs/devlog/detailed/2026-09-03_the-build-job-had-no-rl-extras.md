# Devlog — 2026-09-03

One session. `main`'s remote gate had been red for 112 consecutive runs; it is green locally now under a command that reproduces the CI environment. The shape of the day: every defect in the fix was found by running something, and none by reading it.

## The local gate and the remote gate were measuring different dependency sets

**Timestamp:** 2026-09-03 09:30–10:10

**Action:** Reproduced CI's `build` environment locally, then guarded the eleven tests that reached for absent packages.

**Result:** `build` installs `requirements-locked.txt` and runs the whole suite. That lockfile pins **8** distributions; `requirements-rl-locked.txt` pins **39** more. Eleven tests imported torch, stable_baselines3, sb3_contrib or PIL without a skip guard, so they errored. On a development machine all of those are installed, so `python -m unittest` was green here and red in CI on every push since `d6b5e39` (2026-08-14) — **112 consecutive failed runs**, counted from the runs API rather than estimated.

The first local run of the plain suite passes. That is the whole difficulty: there was no way to see this class of defect locally, so the local gate was not weak, it was blind.

**Reasoning:** The reproduction is a meta-path wrapper that makes the RL roots answer "not found". Answering rather than raising is the point: a genuinely absent package makes `import torch` raise ModuleNotFoundError from the import machinery AND `importlib.util.find_spec("torch")` return None, and the guards in this tree check both. A finder that raised would have broken every `find_spec` guard.

**Validation:** Same command, same machine, before and after. Before: `Ran 1721, FAILED (errors=11, skipped=28)`, exit 1, and the 11 test ids match CI run 33777420299 one for one. After: `Ran 1723, OK (skipped=38)`, exit 0. Deps-present control: `Ran 1740, OK`. `npm test` 253 tests / 249 pass / 0 fail.

What the proof would still miss: the harness hides packages in one interpreter. Fourteen test modules spawn `sys.executable`, and a child sees the real environment. No current child payload imports a blocked root, so it is latent — and it is named in the harness's own header rather than fixed, because with the blocklist now covering 24 roots a child shim would hide setuptools and packaging from every spawned interpreter, trading a latent false green for a live false red.

**Code reviewer comments:** Everything below came from review. Two lanes, both `claude-opus-5[1m]`, because both pinned reviewers were down (Codex `gpt-5.6-sol` out of quota until 2026-09-06 19:25; `claude-fable-5[1m]` rate-limited). Note for whoever reads a lane's silence later: both failures return **exit 0** with the limit message in the review body, so a lane that ran out of quota looks exactly like a completed review to anything checking the exit code. An abstention is not an approval.

## The number that did not move, and why that was the dangerous one

**Timestamp:** 2026-09-03 10:15

**Result:** The post-fix suite ran 1721 tests, exactly as many as the pre-fix suite. A reviewer caught that the derivation offered for it — five modules now skipping at load, replacing 7 counted entries with 5 — accounts for −2 and stops there, while the new contract module contributed +2. The two cancelled.

**Reasoning:** A count that lands back on its old value is a worse claim than one that moves, because nothing distinguishes it from "the run did not happen". The honest statement is `1721 → 1721 (−2 from the guards, +2 from the new module)`, and after the review's own additions it is 1723. The pre-fix skip count differed from CI's too — 28 locally against 37 on ubuntu — because the platform guards in this tree are `skipUnless(sys.platform == "win32")` and invert across the two machines. That difference is not a defect and was checked rather than assumed.

## Guarding a module and leaving it out of rl-smoke tests it nowhere

**Timestamp:** 2026-09-03 10:20–10:45

**Action:** Added `test/test_rl_coverage_contract.py`, and added seven modules to the `rl-smoke` list (18 → 25).

**Result:** Skipping alone would have moved eleven tests from "erroring in CI" to "running in neither job". The 2026-09-02 entry framed the decision as guard-versus-install-torch and deferred it; the third option is to guard AND name every guarded module in the job that has the extras. The contract found that the previous session's own guard had already created this hole: `test_training_readout_contract` skipped 12 tests in `build` and was absent from `rl-smoke`.

**Reasoning:** The obvious cheap gate — grep the test tree for RL package names and check those modules are listed — is unsound, and was rejected after measuring it: it misses `test_train_semantic_eval_trigger`, which reaches stable_baselines3 only through `train_semantic.KeepBest` and never names it. That is three of the eleven real errors invisible to the gate meant to catch them. Detection is now "the file skips AND names an RL package", which is still textual and still bounded, and the bound is written in the file.

**Validation:** Four mutations, each red, then green on revert: the job given `if: false`; the job switched to the base lockfile (the nastiest — the module list stays intact and all 25 modules would silently skip); a guarded module removed from the list; and a guard package renamed so it can never resolve. That last one is the case neither other instrument can see, since a permanently-false guard skips in both jobs and reports OK twice.

## Three defects in the instruments, all found by executing them

**Timestamp:** 2026-09-03 10:50–11:30

**Result:**

1. `importlib.metadata` reported **0 of 149** distributions under the harness. `_discover_resolvers()` drops any `sys.meta_path` entry lacking `find_distributions`, and the wrapper defined none — so numpy, pygame-ce and gymnasium all read as uninstalled, and `src/rl/provenance.py`, which catches `PackageNotFoundError` and degrades, would have recorded every version as null while looking like a pass. Now delegated, filtered to the blocked distributions: 144 of 149 visible.
2. The script branch left `sys.path[0]` pointing at the working directory, so `scripts/search_dataset.py --help` failed with `No module named 'search_policy'`. A harness whose purpose is to make `ModuleNotFoundError` mean "a missing RL package" was manufacturing one that named a local sibling.
3. The blocklist was five hand-written roots. The lockfile delta is 39 distributions, and `setuptools`, `packaging`, `networkx` and `sympy` were provably importable under the harness and provably absent in `build`. `BLOCKED` is now derived from the two lockfiles on every run and mapped to import roots through `importlib.metadata`, because a distribution name is not an import root — pillow ships `PIL`, protobuf ships `google`, setuptools ships `pkg_resources`. It refuses to start if the derivation fails to produce the five roots that matter, because a derivation that silently yields nothing is worse than the stale list it replaced.

**Reasoning:** A reviewer built a real venv from `requirements-locked.txt` instead of taking the harness's word, and got `1721, OK (skipped=37)` — matching the harness exactly. That independent calibration is what makes the harness usable as a gate; without it the harness is only a claim about itself.

## Two traps worth inheriting

**Timestamp:** 2026-09-03 11:35

- **`git checkout -- <path>` on a file added with `git add -N` truncates it to zero bytes.** The intent-to-add entry stages an empty blob, and checkout restores the index version. It destroyed `test_rl_coverage_contract.py` mid-session while "restoring" it after a mutation test; it was rewritten from scratch. Back mutation tests up with `cp` to a scratch path, never with git.
- **A module-level `raise unittest.SkipTest` behaves oppositely on the two invocation paths.** Under discovery it is reported as a skip and exits 0, which is what `build` does. With modules named explicitly on the command line — which is what `rl-smoke` does — it propagates out of the loader and aborts the whole step at zero tests, exit 1. Red is the right verdict for a job whose purpose is the RL stack, but it means one guarded module can take down all 25, and it reports nothing about the other 24.

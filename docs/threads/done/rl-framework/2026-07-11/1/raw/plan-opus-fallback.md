I've now verified the plan's key claims against the live code and the installed libraries. Two library facts I confirmed by reading the installed `stable_baselines3` 2.9.0 source (the Bash tool is down with a harness `session-env` permission error, so I used Read/Grep on site-packages instead):

- `RolloutBuffer.reset()` (buffers.py:392, class at :343) allocates observations with `dtype=observation_space.dtype` → uint8, so the plan's **486 MiB** rollout-buffer figure is right (8·128·24·108·192 B = 486.0 MiB), not a 4× float32 underestimate.
- `evaluate_policy` (evaluation.py:89–107) threads `states`/`episode_starts` and resets `episode_starts[i]=done`, so the training-time `EvalCallback` best-model selection is **recurrent-aware** — the memoryless-eval risk is confined to the repo's custom `evaluate_vector_policy`.

Here is my review.

---

## Verdict: Not yet — a few real, targeted findings. The plan's core is sound; these are fail-closed/provenance/test-coverage gaps worth fixing before implementation.

### What I verified as correct (so the driver doesn't re-litigate these)
- **Memory sizing** (item 3): 486 MiB train rollout / 972 MiB for 16-frame is arithmetically correct and uint8, confirmed against installed SB3. LSTM state buffers add ~4 MiB (negligible).
- **`gamma=1.0` / `gae_lambda=0.99` semantics** (item 5): defensible and well-motivated. Episode-sum reward = total deliveries, so undiscounted return *is* the true objective; SB3 bootstraps truncated episodes (`rewards[idx] += gamma*terminal_value`), so `gamma=1.0` is consistent with the `truncated_when=configured_horizon_reached` semantics in `protocol.py:221-230`. The plan appropriately frames it as a validate-and-can-be-overturned default with a retained PPO ablation.
- **Frame-stack channel math** (item 1): `VecFrameStack(..., channels_order="first")` yields `3*frame_stack` channels; `MiniMetroCNN` reads `shape[0]` dynamically (`model.py:20-25`), so 24 channels is fine.
- **Artifact/provenance byte-hashing is format-agnostic** (`artifacts.py:185-189`), so RecurrentPPO `.zip` artifacts authenticate identically — the "preserve authenticated artifact behavior" claim holds.
- **Windows spawn** is unaffected: workers only build `PlayerPixelEnv` via `PlayerEnvThunk` (`training.py:84-105`); the LSTM lives in the main process.
- **Model-selection note** (item 7) is correctly hedged ("pragmatic baseline," not "best") and won't make an unsupported claim.

### Findings

**1 — MEDIUM. Resume-inherit for `frame_stack`/`algorithm` is not achievable with the current CLI, and the one untested path is exactly the legacy cross-default case; CI structurally cannot catch it.**
- Evidence: `scripts/train_rl.py:96` sets `--frame-stack ... default=DEFAULT_FRAME_STACK`. Once `DEFAULT_FRAME_STACK` flips 4→8 (item 3), resuming a saved **4-frame `ppo`** run without passing `--frame-stack` gives `args.frame_stack=8 != saved 4` → the hard `raise` at `train_rl.py:198-202`. The plan's stated "resume inherits the saved algorithm and frame stack unless the user explicitly requests a conflicting value" (item 2) is impossible to implement with an argparse concrete default — it needs a `None` sentinel to distinguish "explicit override" from "defaulted."
- Why CI won't catch it: the rl-smoke resume step (`.github/workflows/test.yml:93`) resumes `ci-smoke`, which is created with the *same new defaults* (recurrent, 8-frame), so `saved==default==8` and the mismatch branch is never exercised. Item 1's red-test list covers legacy *evaluation* but not legacy *resume-inherit*.
- Ask: add the sentinel for `--frame-stack` (and `--algorithm`) resolution on resume, and add a red test that resumes a saved 4-frame `ppo` manifest and asserts it inherits `frame_stack=4` / `algorithm=ppo` without an explicit flag.

**2 — LOW/MEDIUM. `sb3-contrib` must be added to the provenance package tuples, or runtime-drift detection silently misses it.** The plan says "include it in runtime compatibility/provenance" (item 6), but the precise sites are easy to miss: `src/rl/provenance.py:15-24` (`DEFAULT_PACKAGE_NAMES`) and `:25-33` (`COMPATIBILITY_PACKAGE_NAMES`). If only `requirements-rl*.txt` and the lock are touched, a mismatched `sb3-contrib` version at resume/eval would **not** register as runtime drift (`runtime_compatibility_differences` only iterates `COMPATIBILITY_PACKAGE_NAMES`, `provenance.py:213-219`). Add `"sb3-contrib"` to both tuples and a test asserting it is present in `COMPATIBILITY_PACKAGE_NAMES`.

**3 — LOW. Old-PPO evaluation requires generalizing an unconditional `raise`, and the "preserve old PPO evaluation" claim should be documented as requiring `--allow-training-drift`.**
- The hard gates are `scripts/evaluate_rl.py:163` and `scripts/train_rl.py:196` (`if ...algorithm != "ppo": raise`). These must become algorithm dispatch, or *all* recurrent artifacts fail. Covered by the plan but flagging the exact edit sites.
- Separately: adding `sb3-contrib` to `requirements-rl.txt` changes `compute_training_fingerprint` (`training.py:26-40` lists both RL requirements files), so **pre-change PPO artifacts will need `--allow-training-drift` to evaluate**. That is correct fail-closed behavior and not a regression (any trainer edit already does this), but the docs/plan should state it so "preserve old PPO evaluation" isn't read as "seamless."

**4 — LOW. Clarify the LSTM topology and record it in the manifest.** "one 256-unit, one-layer LSTM for actor and critic" (item 4) is ambiguous: sb3-contrib's default is a **separate critic LSTM** (`enable_critic_lstm=True`, i.e. two LSTMs), while "one … for actor and critic" reads as a shared LSTM (`shared_lstm=True, enable_critic_lstm=False`). Pick one, and record `lstm_hidden_size`, `n_lstm_layers`, and `enable_critic_lstm`/`shared_lstm` in the algorithm-aware hyperparameter manifest so the choice is reproducible and fingerprinted.

**5 — LOW (test fidelity). The custom-evaluator red test must refute memorylessness at boundaries, not just state threading.** `src/rl/evaluation.py:50` currently does `action, _ = model.predict(observation, deterministic=...)`, discarding state. The fix must thread **both** `state` and `episode_start=dones` (reset per episode), and the test's `FakeModel.predict` signature (`test_rl_evaluation.py:16`, currently `predict(self, observation, *, deterministic)`) must be updated to assert non-`None` state is carried *and* zeroed on `done`. A test that only checks state is passed will not catch a missing `episode_start` reset — the subtle bug that leaks memory across episodes within an evaluation.

### Note
- Version pairing `sb3-contrib==2.9.0` with the existing `stable-baselines3==2.9.0` (`requirements-rl.txt:3`) is internally consistent; the plan's `pip check` step (item 6) is the right guard. I could not run `pip`/`pip check` or import `sb3_contrib` (not installed in `py313`; Bash tool unavailable this session), so the real RecurrentPPO learn/save/load/predict tests (item 1) can only be exercised where the regenerated lock is installed — ensure the new recurrent tests are added to the CI rl-smoke module list (`.github/workflows/test.yml:87`) so that path actually runs.

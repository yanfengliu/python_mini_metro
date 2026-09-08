# Initial review

Plan-breaking issue first: do not benchmark with `model.learn(total_timesteps=2048)`. SB3 2.9 updates the linear schedule against that horizon, so the measured second update runs at zero learning rate. Instead, pin the production horizon (currently 1,000,000), call `_setup_learn()`, then drive exactly two verified `collect_rollouts(..., n_rollout_steps=128)` / `_update_current_progress_remaining()` / `train()` iterations. Treat iteration 1 as warm-up and iteration 2 as measured.

Recommended minimal architecture:

- `scripts/profile_rl_history.py`
  - Supervisor/orchestrator only.
  - `counterbalanced_schedule()` produces cyclic Latin-square orders across at least three repeats.
  - `snapshot_process_tree()` uses Toolhelp32 parent-PID discovery.
  - `working_set_bytes()` uses `GetProcessMemoryInfo`.
  - `supervise_worker()` samples root plus live descendants every 50 ms, writing raw JSONL samples and lifecycle peak.
  - `evaluate_promotion()` computes medians and applies the preregistered gates.
  - Candidate presets: primary `(8-contiguous, 8-multiscale, 12-multiscale)` and fallback `(8-contiguous, 8-multiscale, 10-multiscale)`.
  - Launch the same interpreter via `sys.executable`; every run is a fresh worker process.

- `scripts/profile_rl_history_worker.py`
  - `resolve_candidate()` maps directly to live `contiguous_history(8)` / `history_for_layout(...)`.
  - `run_profile()` builds the real `TaskSpec`, eight spawned environments, `VecTemporalHistory`, and real RecurrentPPO through existing factories.
  - `drive_two_updates()` performs one 1,024-transition warm-up and one measured update using the SB3 loop above.
  - Assert after warm-up that all wrapper maximum-valid ages reached 128; otherwise mark the run invalid.
  - Record setup, collection, and training separately; rates are exactly `1024 / collection`, `4096 / training`, and `1024 / (collection + training)`.
  - Instrument the actual measured `rollout_buffer.get(64)` batches and CNN preprocessed inputs to record padded `uint8` and `float32` shapes/dtypes/bytes. Record `rollout_buffer.observations.nbytes`, `history_buffer_nbytes`, actual output bytes, and trainable parameters.
  - Provide a documented conv/linear/LSTM MAC estimator for one full rollout-policy forward across eight slots.
  - Pin both Torch thread counts explicitly; this machine’s current production defaults are 24 intra-op and 24 inter-op threads.
  - Record descriptor/fingerprint, source/runtime snapshots, CPU/RAM, versions, seed, task, workload, and QPC measurement-window timestamps.

- `test/test_rl_resource_profile.py`
  - Candidate mappings/fingerprints and cyclic schedule.
  - Exact analytical byte math and MAC formulas.
  - Promotion-gate boundary cases, controls never eligible, failures/batch mismatch/sample gaps fail closed.
  - Raw schema and source/runtime metadata.

- `test/test_rl_resource_profile_integration.py`
  - Real tiny RecurrentPPO two-iteration driver proving exact collect/train counts and nonzero measured learning rate.
  - Actual padded-minibatch capture.
  - Live Windows child/grandchild process-tree sampling, positive aggregate working set, and cleanup.
  - Production contract assertion: 8×128, batch 64, four epochs.

Verified live contracts:

- SB3/SB3-Contrib are 2.9.0; Torch is 2.13.0 CPU.
- `collect_rollouts(env, callback, rollout_buffer, n_rollout_steps)`, `train()`, and `_setup_learn(...)` match the proposed driver.
- Rollout observations are actually `uint8`.
- Current exact parameters are 1,478,933 for either eight-frame layout and 1,503,509 for twelve frames.
- Current public ring metric is `VecTemporalHistory.history_buffer_nbytes`.
- The stated storage math is consistent with the live `(3,108,192)` task.

Risks to address:

- Report both full-lifecycle and measured-window working-set peaks; use the conservative lifecycle peak for promotion, since buffer allocation occurs during setup.
- Preserve raw samples under ignored `output/`; commit only compact summaries and hashes to avoid oversized repository files.
- Record requested interval and maximum observed sample gap. A heavily saturated 24-thread training process can delay the supervisor despite a 50 ms target.
- Minibatch instrumentation adds slight timing overhead; keep it shape/byte-only and identical across candidates.
- Do not interpret working set or page faults as proof that paging did not occur.

# First re-review

Two substantive defects remain:

1. The MAC scope omits the live policy’s actor/critic MLP extractor. RecurrentPPO has separate post-LSTM `256→64→64` actor and critic linear stacks before `action_net` and `value_net` (the heads receive 64 features, not 256). GM-02d1 step 4 should explicitly include these four linear layers.

2. Full dirty-tree rejection currently makes the campaign impossible because live `git status` contains persistent untracked `.agents/`, which must not be staged. Define cleanliness as tracked/relevant runtime and benchmark paths, or explicitly ignore `.agents/` before the clean harness commit; do not silently claim a clean full tree while excluding it ad hoc.

Everything else is aligned with the live SB3 2.9 APIs and repository contracts.

# Final re-review

APPROVED. No remaining substantive defects found against the live repository and SB3 2.9 contracts.

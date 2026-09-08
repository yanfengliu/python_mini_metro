# Initial review

GM-02 temporal preflight is complete. The draft needs several corrections before approval.

1. High — GM-02a can create a dishonest manifest/runtime pairing. GM-02a must explicitly record the actual contiguous `VecFrameStack` layout `[N-1..0]`; it must not record `decision-history-v1` until that transform is active.

2. High — the pre-profile fresh default is ambiguous. Fresh runtime must remain 8-contiguous through GM-02c. `decision-history-v1` is opt-in until GM-02d measures it. Only GM-02d may change the default.

3. Medium — descriptor and wrapper should be separate modules for dependency safety, not merely file size. Put the descriptor in `src/rl/history.py`, the wrapper in `src/rl/temporal_history.py`, and import the wrapper locally inside `build_vector_env()` after `require_rl_dependencies()`. Add both files to `TRAINING_SOURCE_PATHS`.

4. Medium — the ring algorithm needs stronger lifecycle requirements. Require a circular write cursor and per-slot maximum-valid-age counter. Do not use `np.roll`. On done, validate and append the single-frame terminal observation, assemble and copy the ending history, then overwrite the slot with the auto-reset observation and reset valid age. Missing, wrong-shape, or wrong-dtype terminal observations should fail closed. Preserve `TimeLimit.truncated`, rewards, and dones unchanged.

5. Medium — aliasing needs an explicit regression. Retain returned and terminal arrays across later steps/reset and prove their bytes remain correct.

6. Medium — resource reporting must separate ring cost from rollout cost. For eight 108x192 RGB environments, the 129-frame parent ring is 61.224609375 MiB, the twelve-frame step output is 5.6953125 MiB, and the twelve-frame 128-step rollout observations are 729 MiB. Eight-multiscale also needs the 61.225 MiB ring despite its smaller 486 MiB rollout payload.

Live SB3 2.9.0 confirms `DummyVecEnv` and `SubprocVecEnv` save the ending frame in `info["terminal_observation"]`, set `TimeLimit.truncated`, auto-reset, and return the replacement episode's initial frame. `VecMonitor` preserves those values. RecurrentPPO uses the transformed terminal observation for timeout bootstrapping and derives the next recurrent reset mask from `dones`. Required order: `Dummy/SubprocVecEnv -> VecMonitor -> VecTemporalHistory`.

Required red tests cover t0 through t129, wraparound, repeated reset, true termination and truncation, terminal versus reset frames, staggered slots, malformed terminal observations, N=1/4/8/other contiguous equivalence, truncation pass-through, recurrent bootstrap/masks, Dummy and spawned Subproc smoke, and construction-failure cleanup. Current exact-RL baseline terminal/recurrent/roundtrip checks pass 3/3. No files were edited.

# Re-review

APPROVED. Runtime honesty and default gating are explicit; optional-dependency separation is fixed; circular-ring, terminal-copy, malformed-terminal, pass-through, and aliasing contracts are fixed; exact wraparound, staggered reset, legacy-equivalence, and retained-array tests are required; and resource accounting separately measures rollout, ring, output, and actual padded recurrent minibatches. These contracts match live SB3 2.9.0 auto-reset and RecurrentPPO timeout-bootstrap behavior. No substantive findings remain.

# Implementation finder and refuter

CLEAN. Focused exact-RL passed 42/42; fresh v2 smoke records the actual contiguous eight-frame runtime; a genuine on-disk v1 recurrent artifact evaluated and resumed into a v2 child with authenticated parent hashes; mismatch guards run before artifacts/environments; and optional imports remain dependency-light. The CLI mocks are corroborated by direct guards, parser tests, literal v1 bytes, a legacy model, and real smokes.

VERIFIED RESOLVED after the resource lane's findings. Both `history.py` and `manifest_schema.py` are independently mutated and change the training fingerprint while trainer-only mutations leave the content fingerprint unchanged. Missing `history` and unknown `future` top-level v2 keys fail exact-key parsing. Focused tests passed 3/3 and an independent parser probe produced explicit missing/unknown errors. No edits.

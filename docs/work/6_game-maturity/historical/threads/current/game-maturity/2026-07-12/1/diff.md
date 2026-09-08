# Plan-review delta

- Added a fail-closed GM-02a/02b boundary so v2 cannot describe multiscale history while runtime still uses `VecFrameStack`.
- Made the descriptor the single source for `frameStack` and `historyFingerprint`, fixed semantic literals, and required exact canonical v1 bytes plus arbitrary-N normalization cases.
- Split dependency-light history identity from the optional-dependency vector wrapper and specified bounded circular-ring, terminal-copy, aliasing, wraparound, and staggered-reset contracts.
- Kept fresh runtime at eight contiguous frames until GM-02d and preregistered repeated, counterbalanced resource measurements, numeric promotion gates, actual-allocation checks, and a greater-than-eight fallback.

## GM-02a implementation

- Added dependency-light immutable history descriptors for contiguous and reviewed 8/10/12 multiscale layouts, with closed semantics, canonical JSON, and SHA-256 identity.
- Split the near-ceiling manifest module into strict immutable v1/v2 schema parsing and atomic I/O/compatibility validation; fresh factories take one descriptor and derive the redundant frame count and digest.
- Preserved exact canonical manifest-v1 bytes and arbitrary positive contiguous stacks while making v2 descriptor/digest/frame-count/key disagreement fail closed.
- Kept runtime truthful with contiguous-only train/evaluate guards before artifact opening, emitted actual contiguous v2 history, and added both new identity modules to the trainer-only fingerprint allowlist.
- Added focused descriptor, manifest, CLI-ordering, legacy-model, and fingerprint regressions plus fresh-v2 and v1-to-v2 end-to-end artifact smokes.

## GM-02b implementation

- Added an optional-dependency `VecTemporalHistory` wrapper with one bounded `uint8` circular ring, cursor, and maximum-valid-age counter per vector slot; direct sampling produces owned oldest-to-newest channel-first stacks without rolling or copying the parent ring.
- Preserved reset and auto-reset semantics by zero-filling unavailable history, constructing owned terminal stacks before clearing done slots, retaining rewards/dones/infos, and poisoning all history after any failed reset or consumed step until a clean reset succeeds.
- Added exact chronology through offset-128 wraparound, staggered terminal/truncation and retained-array isolation, malformed lifecycle recovery, candidate allocation accounting, constructor/close cleanup, and byte equivalence with SB3 `VecFrameStack` for N=1/4/8/13.
- Added the wrapper to the trainer-only fingerprint boundary and documented that train/resume/evaluate deliberately remain on contiguous `VecFrameStack` until GM-02c integrates every runtime path together.

## GM-02c implementation

- Replaced count-only runtime stacking with one exact `HistoryDescriptor` shared by train, evaluation callbacks, resume, evaluation, and manifest persistence; all vector paths now construct `base -> VecMonitor -> VecTemporalHistory` while preserving a legacy Python `frame_stack` alias.
- Added mutually exclusive `--frame-stack N` contiguous controls and reviewed `--history-layout` names. Fresh omission remains contiguous eight; resume omission inherits the authenticated v1/v2 descriptor; equal-channel semantic mismatch fails before validation/artifact access.
- Added history identity to evaluation JSON, exact CLI/artifact-order tests, real named-history Subproc/terminal/timeout/mask/save-load coverage, model-space mismatch coverage, and explicit old-`VecFrameStack` v1 mechanism compatibility.
- Expanded Windows RL CI with the missing history modules plus named twelve-frame fresh/evaluate/resume/evaluate, exact default/named/legacy layout and fingerprint assertions, parent hashes, tags, and seeds. The fresh default remains eight contiguous frames pending GM-02d profiling.

## GM-02d1 benchmark harness

- Added dependency-light candidate, cyclic-order, analytical storage/MAC, and preregistered promotion contracts plus strict independent worker-result validation.
- Added a stdlib-first RecurrentPPO worker that blocks before heavy imports, then performs one warm-up and one measured production-horizon rollout/update while recording actual recurrent padding, tensor storage, rates, history ages, parameter counts, and one-row inference MACs.
- Added a Windows supervisor that retains PID/creation-time identities, follows the full descendant tree across root exit, samples aggregate working set at an absolute cadence, drains worker pipes concurrently, records bounded diagnostics and artifact hashes, and cleans up its owned process tree on every exit path.
- Added clean-source campaign orchestration, durable invalid-run summaries, post-worker drift detection, primary/fallback schedules, exact CLI exit semantics, focused core/exact-RL tests, CI coverage, public profiling guidance, and three-lane plan/implementation review evidence. No candidate measurement was observed before this harness transaction.

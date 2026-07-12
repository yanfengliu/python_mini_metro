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

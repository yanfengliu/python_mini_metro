# GM-02b correctness finder and refuter

## Finder

Two substantive lifecycle findings:

- Medium: `step_async()` delegates before reset validation. With `SubprocVecEnv`, work can be sent and never collected when `step_wait()` then raises. The focused test currently fails on this.
- Medium: after consuming a malformed transition, the wrapper remains initialized with stale ring state. Continuing can skip a transition or mix history across an underlying auto-reset. It should require explicit reset after validation failure.

Exact-RL focused result: 4 passed, 1 failed. No files edited.

## Reset-assembly refutation

MEDIUM — reset assembly failure does not poison/zero state. In `VecTemporalHistory.reset`, `_poison()` runs first, but the code writes the reset frame and sets `_initialized = True` before calling `_assemble_batch()`, with no try/except. A minimal exact-RL probe patched `_assemble_batch` to raise and observed `initialized True`, `ring_sum 84`, then `step_async_dispatched [0]`. This violates the intended “any reset validation or assembly failure requires successful reset” contract and can expose a wrapper whose reset call never returned successfully as usable. Wrap the complete reset reconstruction/assembly in try/except BaseException, poison on failure, and set initialized only after successful assembly (or poison in except); add a reset assembly-failure test asserting ring/cursors zero and pre-reset step_async rejection.

All six current focused exact-RL temporal-history tests pass, so this path is presently uncovered. The pre-reset step_async guard, consumed-step poisoning, malformed reset validation, constructor failure close, and stale/cross-episode prevention otherwise held under inspection. No edits.

## Final refutation

CLEAN on lifecycle and correctness.

Verified:

- Reset-assembly failure leaves initialized false with zeroed ring/cursors.
- Pre-reset stepping does not dispatch.
- Constructor failures close the base environment.
- Step/reset failures require successful reset.
- No stale or cross-episode continuation remains.
- Exact-RL temporal suite: 6/6 passed.
- Ruff check passed.

No files edited.

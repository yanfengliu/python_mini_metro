# GM-02b SB3 and recurrent compatibility finder and refuter

## Finder

MEDIUM — validation failures can leave the wrapper usable with stale cross-episode history.

`step_wait()` consumes the underlying auto-reset before validation, but errors leave `_initialized=True` and preserve the old ring. The current malformed-terminal test explicitly continues and expects prior-episode frames. `reset()` has the same issue if new reset observations are malformed.

After any failed post-transition validation, poison the wrapper until a successful explicit reset. Set `_initialized=False` before reset validation and after any `step_wait()` validation failure.

Other checks were clean:

- Synthetic suite passed 7/7.
- Real `DummyVecEnv -> VecMonitor` terminal/reset semantics passed.
- Real RecurrentPPO timeout bootstrap received the correct 36-channel terminal stack.
- Spawned `SubprocVecEnv -> VecMonitor` passed with two slots.

No files edited.

## Final refutation

CLEAN.

Verified after fixes:

- Focused wrapper/fingerprint tests passed 8/8.
- Poisoning now blocks stepping after malformed step/reset data until a successful reset.
- Real `DummyVecEnv -> VecMonitor` preserved reset and terminal stacks.
- RecurrentPPO timeout bootstrap consumed the correct 36-channel ending-episode history.
- Spawned two-slot `SubprocVecEnv -> VecMonitor` passed terminal auto-reset lifecycle checks.
- Constructor cleanup and candidate ring/output byte counts are directly covered.

No files edited.

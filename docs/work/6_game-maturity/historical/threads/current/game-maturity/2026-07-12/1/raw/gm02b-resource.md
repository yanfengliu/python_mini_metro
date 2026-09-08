# GM-02b resource and documentation finder and refuter

## Finder

1. MEDIUM — Lifecycle failures can leave the vector environment advanced while the wrapper remains initialized with stale history, enabling cross-episode/time-step leakage if a caller catches the advertised fail-closed error. On any post-advance/reset validation error, clear/poison history and require a fresh successful reset.
2. MEDIUM — The reset-before-step guard is too late for `SubprocVecEnv`. Override `step_async()` to reject before delegating when uninitialized, and test the base saw no action/worker command.
3. LOW/MEDIUM — The promised resource/cleanup acceptance is only partially pinned. Add bounded real-shape allocation/byte coverage and clarify/verify constructor ownership cleanup.
4. LOW — Architecture/status docs are stale for a completed GM-02b transaction. Update architecture to say the wrapper and synthetic lifecycle tests now exist but runtime remains on `VecFrameStack` until GM-02c; add the substantive PROGRESS entry when closing the unit.

Clean areas: ring is bounded `(n_envs,max_offset+1,3,H,W)` uint8; no `np.roll`; one owned batch allocation per step and only an additional owned terminal stack for done slots; no full-ring copy/float conversion; training fingerprint includes temporal_history and tests mutate it individually, while content fingerprint excludes it; source184 LOC/test341 and all files remain <500.

## Final refutation

Resource and cleanup behavior is approved; all 8 focused tests pass. The only remaining issue is stale architecture/status documentation that still describes the implemented wrapper as not landed.

Verified live:

- Exact candidate ring allocation is `(8,129,3,108,192)` uint8 = 64,198,656 bytes; test asserts that exact value, output space `(36,108,192)`, and returned vector batch 5,971,968 bytes.
- Allocation is bounded: one fixed uint8 ring, intp cursors/valid-age arrays, one owned stacked output per step, and one additional owned per-done terminal stack; no `np.roll`, full-ring step copy, or float conversion.
- Pre-reset `step_async` fails before dispatch; malformed step/reset poisons/zeros history until a successful reset. Constructor closes its base on any failure; normal close delegates and the test proves the base closes.
- `src/rl/temporal_history.py` and its test remain below 500 lines; `test_rl_training.py` remains at 495.
- Trainer fingerprint includes and individually mutation-tests temporal_history; content fingerprint explicitly mutates it with no digest change.

The remaining documentation finding was fixed before final validation. No files edited by the reviewer.

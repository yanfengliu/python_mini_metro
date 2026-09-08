Three MAJOR findings remain.

1. MAJOR — [src/path_lifecycle.py:313](C:/Users/38909/Documents/github/python_mini_metro/src/path_lifecycle.py:313) — with two `[2,0]` crossing lines already consuming 2 tunnels, `create_path_from_station_indices([2,0,2], loop=True)` is rejected. The raw list counts two crossings, but construction produces a two-station loop `[2,0]`, whose retraced closure correctly counts only once. A valid total of 3 is therefore rejected. Fix: derive one canonical, side-effect-free route plan before gating, then use it for both validation and construction.

2. MAJOR — [src/path_lifecycle.py:313](C:/Users/38909/Documents/github/python_mini_metro/src/path_lifecycle.py:313) — in the same consumed-2 state, `[0,1,0,2], loop=False` passes the upfront check as one crossing. Actual creation semantics produce loop `[0,1,2]`, which has two crossings; the end gate then rejects it, but stations 0 and 1 retain new snap blips and the canonical checkpoint changes. Fix: use the same canonical route plan at every gate and add checkpoint-inertness coverage.

3. MAJOR — [src/path_lifecycle.py:407](C:/Users/38909/Documents/github/python_mini_metro/src/path_lifecycle.py:407) — fill the budget with loop `[2,0,1]`, open `[2,0]`, and same-bank `[0,1]`; start an additional `[2,0]` draft, remove the same-bank line, then call `finish_path_creation()`. Removal’s button reassignment binds the draft; rejection removes it from `paths` but leaves it in `path_to_button` and `PathButton.path`. The UI retains a colored ghost-line button. Fix: reconcile button ownership during abort, or prevent draft paths from being assigned.

Verified clean:

- Derived `num_tunnels`: no writers; save/load/checkpoint/RL do not set it; CLASSIC→RIVER swap reports `3`.
- Normal finish/extend/loop end and commit gates agree.
- No over-budget commit found.
- Removal and reroute refund correctly.
- CLASSIC RNG, canonical checkpoint, frame, station construction, and frozen save bytes matched the committed baseline.
- Focused suite: 29/29 passed. Full suite: 1,401 passed, 12 skipped. These counterexamples are currently untested.

No BLOCKER/CRITICAL, MINOR, or NIT findings. The external CLI lane was blocked by egress policy and is not counted as approval.

FIX-FIRST

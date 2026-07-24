BLOCKER / CRITICAL — No findings.

MAJOR — `src/path_lifecycle.py:421-425` — RIVER seed 0, create same-bank `[0,1]`, fill the budget with three `[2,0]` lines, remove `[0,1]`, then attempt `[1,2]` → the rejected draft reuses the removed line’s color and deletes its still-active station-1 blip. Checkpoint and frame change despite unchanged RNG, paths, and tunnels → track exact blip instances created by each draft; color is not ownership.

MAJOR — `src/path_lifecycle.py:414-425` — CLASSIC seed 0, `start(0) → add(1) → abort` → live code removes the snap-blip while committed `HEAD` preserves it. RNG matches, but checkpoint and rendered frame bytes differ → keep ordinary CLASSIC abort byte-compatible and invoke owned-blip rollback only for tunnel-budget rejection.

MAJOR — `src/path_lifecycle.py:155-158` — CLASSIC seed 0, commit `[0,1]`, start draft `[1,2]`, then remove the committed line → live code leaves the draft’s button mapping as `[None]`; committed `HEAD` maps it to button 0. Checkpoint and frame differ → scope draft skipping to finite-budget behavior, preserving legacy CLASSIC assignment.

MINOR — `src/path_lifecycle.py:408-425` — a supported `release_color_for_path` override releases the original draft and rebinds `path_being_created` to a replacement → removal correctly follows the replacement, but cleanup also scans only the replacement, leaving the original draft’s blip behind → preserve the post-hook re-read for removal while separately retaining the pre-hook draft’s exact effect ownership for cleanup.

NIT — No findings.

Verified clean:

- Focused suite: 41/41 passed.
- Supplementary path/rebinding/render contracts: 20/20 passed.
- Explicit closure `[2,0,2]` correctly commits as a one-crossing loop.
- Mid-repeat `[0,1,0,2]` correctly resolves to a two-crossing loop and rejects inertly in the ordinary no-color-collision case.
- Exhaustive short-route checks found no over-budget commit.
- Committed-path button alignment and commit-time draft assignment work normally.
- Derived tunnel properties and live map-budget lookup remain correct.

FIX-FIRST.

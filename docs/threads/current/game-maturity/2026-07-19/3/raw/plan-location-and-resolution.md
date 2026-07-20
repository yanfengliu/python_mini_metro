# GM-04a location and resolution audit

GM-04a should establish an enforced package-resolution contract, not just record pin metadata.

Strong recommendation: use the repo-owned, ignored `/.civ-engine-pin/` directory and canonical package spec `file:.civ-engine-pin`. This avoids touching `../civ-engine`, works with Windows junctions and POSIX symlinks, and gives provenance one exact realpath to enforce.

A checked-in JSON manifest plus loader is suitable only with enforcement in the same transaction. JSON plus loader alone is insufficient because package and lock metadata still resolve `../civ-engine`, CI checks out and builds that sibling, provenance records the resolved root but does not require a specific location, and `--allow-dirty` currently bypasses all modeled mismatches.

Put the manifest under `scripts/` so the current source inventory hashes it. Rewire package and lock metadata, move CI checkout/build to the isolated path, make resolved-root mismatch non-overridable, consume the descriptor version from recursive manifests, and add static parity plus wrong-location provenance tests. GM-04b can own the safe clone/build/verify command and pre-hooks; GM-04c can own final suite and mismatch evidence.

The live suite is 44 tests rather than the parent plan's stale 41. The audit reproduced 25/44 with 19 pin-related failures and left the worktree unchanged.

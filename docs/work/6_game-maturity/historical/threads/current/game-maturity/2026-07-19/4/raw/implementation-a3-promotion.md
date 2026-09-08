# GM-04b A3 promotion-mode review

## Root cause

`assertEquivalentTree` read source and destination directory metadata concurrently with `Promise.all`. The POSIX test awaited the source `lstat` before changing the destination mode, allowing the destination `lstat` to capture the old mode first. Both snapshots could therefore compare equal and publication could incorrectly succeed. This was a real directory-mode integrity window, not merely an assertion mistake. Windows did not expose it because the POSIX-mode test was skipped.

## Files changed

- `scripts/civ-engine-setup-promotion.mjs`
- `test/civ-engine-setup-promotion.test.mjs`

The production correction serializes the source directory snapshot before the destination snapshot. A host-independent regression injects synthetic destination-mode drift only when the destination stat is invoked after the source snapshot completes.

## TDD evidence

RED against the previous concurrent implementation:

- Targeted test: 1 registered, 0 passed, 1 failed
- Failure: `AssertionError [ERR_ASSERTION]: Missing expected rejection.`

GREEN after restoring serialized source-before-destination reads:

- Targeted test: 1 registered, 1 passed, 0 failed
- Focused promotion and cleanup suites: 14 registered, 11 passed, 3 expected Windows POSIX skips, 0 failed

## Static evidence

- `node --check scripts/civ-engine-setup-promotion.mjs`: passed
- `node --check test/civ-engine-setup-promotion.test.mjs`: passed
- `git diff --check`: passed
- Production file: 288 lines
- Test file: 489 lines

## Findings disposition

- CI-blocking directory-mode snapshot race: fixed and regression-covered across hosts.
- No further findings in the reviewed directory-publication path.
- Scope caveat: per-entry file metadata and byte comparisons retain their existing concurrent behavior; they were outside this exact directory-mode CI failure and were not changed.
- No documentation, staging, commits, or pushes were performed.

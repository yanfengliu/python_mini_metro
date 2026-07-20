# GM-04b A3 child-observation finding resolution

Implemented the A3 P1 correction without touching documentation, staging, commits, or unrelated work.

- Added `test/civ-engine-setup-promotion-verification.test.mjs` with portable deterministic regressions for child metadata, file bytes, and link targets.
- RED: all 3 tests failed with `Missing expected rejection` under concurrent observations.
- GREEN: serialized source-before-destination `lstat`, `readFile`, and `realpath`; all 3 pass.
- Repeated the new suite 10 times successfully.
- Promotion suites: 17 registered, 14 passed, 3 expected Windows/POSIX skips.
- Full setup suites: 102 registered, 98 passed, 4 expected skips.
- Syntax, whitespace, and line-count checks passed; files remain below 500 lines.

This establishes ordered pairwise observations only. It does not make verification an atomic filesystem snapshot or prevent out-of-band mutation after a destination observation.

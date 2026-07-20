CLEAN.

The final A2 correction now:

- Revalidates the complete root package/lock/`.npmrc` contract after link creation and exact-root audit.
- Rejects concurrent contract drift while retaining the created exact link and drifted files for inspection.
- Rejects and preserves exact-fast-path foreign entries.
- Uses exact bigint device/inode identity for the root container.
- Preserves EEXIST winners and detects container swaps without unsafe cleanup.
- Performs no root npm invocation.
- Uses truthful atomic-link landing language and correct 466/456/111 line counts.

Validation:

- Correction slice: 21/21 passed.
- Full setup-focused glob: 96 registered, 92 passed, 4 expected platform skips, 0 failed.
- Syntax checks passed.
- `git diff --check` passed.
- Production and split test files remain below 500 lines: 466, 456, and 111.

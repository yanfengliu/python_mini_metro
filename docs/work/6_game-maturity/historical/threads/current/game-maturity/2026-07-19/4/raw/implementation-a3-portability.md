# GM-04b A3 portability correction — implementation self-review

## Root cause

`buildSetupEnvironment({ platform })` accepted an explicit target platform but constructed its default Git/npm paths with the host-bound `path.join`. On Ubuntu, simulated Windows input therefore produced `C:\controlled\home/gitconfig`; on Windows, simulated POSIX input produced `\controlled\home\gitconfig`. The CI expectation was correct.

## Files changed

- `scripts/civ-engine-setup-process.mjs`
- `test/civ-engine-setup-process.test.mjs`

Production now selects `path.win32` for `win32` and `path.posix` otherwise when deriving:

- `GIT_CONFIG_GLOBAL`
- `npm_config_userconfig`
- `npm_config_globalconfig`
- `npm_config_cache`

The test adds a host-independent contract covering both Windows and POSIX target paths.

## RED proof

Before the production correction:

- 6 registered
- 4 passed
- 1 failed
- 1 expected platform skip

Local failing assertion:

- Actual: `\controlled\home\gitconfig`
- Expected: `/controlled/home/gitconfig`

This reproduced the inverse of the Ubuntu CI failure and proved the implementation depended on the host path module.

## GREEN proof

Focused `test/civ-engine-setup-process.test.mjs`:

- 6 registered
- 5 passed
- 0 failed
- 1 expected platform skip

Full `test/civ-engine-setup*.test.mjs` slice:

- 97 registered
- 93 passed
- 0 failed
- 4 expected platform skips
- Duration: 7.374 seconds

Additional checks:

- `node --check scripts/civ-engine-setup-process.mjs`: clean
- `node --check test/civ-engine-setup-process.test.mjs`: clean
- `git diff --check`: clean
- Production file: 352 lines
- Test file: 271 lines

## Scope and disposition

No remaining finding was identified in the changed implementation or focused setup-contract scope. Actual same-host behavior is preserved; the correction removes host dependence from the explicitly platform-selectable environment builder.

I did not run the full canonical `npm test`, Python suite, pre-commit hooks, or remote CI. I did not edit documentation, stage, commit, or push. The unrelated untracked `.agents/` directory was preserved.

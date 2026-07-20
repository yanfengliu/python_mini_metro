FINDINGS

[P1] Child-entry equivalence checks retain the same concurrent snapshot race — `scripts/civ-engine-setup-promotion.mjs:158-161,188-191`

A3 serializes only each directory’s root `lstat`. Child metadata and file bytes are still read with `Promise.all`, so destination observation begins before the source observation completes. I reproduced a deterministic race where the destination read captured the original bytes, the destination was then changed after the source read completed, and both cached buffers compared equal. `promotePin` resolved successfully while the published file contained `"tampered destination\n"`.

The new regression at `test/civ-engine-setup-promotion.test.mjs:313-359` proves root-directory mode ordering but can pass while file mode/byte verification retains the identical defect. The later orchestration audit is useful defense in depth, but `assertEquivalentTree` itself can falsely certify equivalence and does not produce the intended ownership error/preservation path.

Serialize source-before-destination observations for child metadata, file bytes, and any analogous link-target comparison, then add a portable file-level regression that would fail under the concurrent implementation.

[P2] `planGitInvocation` bypasses the corrected target-platform defaults — `scripts/civ-engine-setup-process.mjs:59-64`

`planGitInvocation` derives `gitGlobalConfigPath` and `hooksPath` with host `path.join`, then explicitly passes `gitGlobalConfigPath` into `buildSetupEnvironment`, shadowing A3’s corrected default. On Windows with `platform: "linux"` and `homeDir: "/controlled/home"`, I observed:

```json
{"global":"\\controlled\\home\\gitconfig","hooks":"core.hooksPath=/controlled/home/hooks-disabled"}
```

The expected target value is `/controlled/home/gitconfig`; Linux simulating Windows produces the converse mixed-separator class. No current production caller appears to inject a non-host platform, but the exported planner’s platform contract remains internally inconsistent, and the new test exercises only `buildSetupEnvironment`. Derive all home-relative planner paths with the selected platform path implementation and cover the planner in both target-platform directions.

Verification performed:

- Syntax checks passed for all four changed files.
- Focused suites: 18 registered, 14 passed, 4 expected platform skips, 0 failed.
- `git diff --check` passed.
- Review made no workspace changes.

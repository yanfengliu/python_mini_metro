Review result: BLOCKED on two substantive findings.

1. [MEDIUM] Exact installations bypass the root `node_modules` audit.

   - `auditRootNodeModules()` is called only from `installRootDependency()` at `scripts/civ-engine-setup-operations.mjs:211-215`.
   - Setup skips that operation when resolution is already exact at `scripts/civ-engine-setup.mjs:148-164`.
   - `verifyDefaultPin()` and `verifyOnly()` check resolution/provenance without auditing sibling entries at `scripts/civ-engine-setup-operations.mjs:218-274`.
   - Therefore an exact `node_modules/civ-engine` link plus a foreign root entry passes no-op setup and strict verification, contradicting `README.md:34` and `PLAN.md:40`.
   - Fix: require the exact root-container audit in both final/default and verify-only paths, with a regression proving a foreign sentinel is rejected but preserved.

2. [MEDIUM] Root-container identity uses lossy numeric inode values.

   - `assertPhysicalDirectory()` uses default numeric `lstat` at `scripts/civ-engine-setup-operations.mjs:429-434`; `assertSameDirectoryIdentity()` compares those values at `:419-425`.
   - Windows NTFS file IDs can exceed `Number.MAX_SAFE_INTEGER`. On this host, an actual bigint inode `92042317384571062` is exposed numerically as `92042317384571060`.
   - Distinct IDs can therefore compare equal, weakening the claimed identity-stable container defense.
   - Fix: use `lstat(..., { bigint: true })` and exact bigint/string comparison, consistent with the setup ownership code.

Additional corrections:

- [LOW] `docs/threads/current/game-maturity/2026-07-19/4/PLAN.md:26` still says a stale root slot may be reinstalled, contradicting the missing-only/refuse-stale policy at line 40 and `README.md:34`.
- [LOW] The new tests cover normal creation, stale link, physical slot, and foreign entries, but do not deterministically exercise the EEXIST winner-preservation branch or container-identity-change branch.

Validation run: 49/49 focused setup, safety, contract, and provenance tests passed. The exercised stale/physical/foreign states were preserved, root npm was not invoked, and the Windows junction success path passed.

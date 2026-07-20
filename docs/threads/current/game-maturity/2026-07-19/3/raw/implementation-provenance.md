# Provenance implementation review

## Initial review

- **High — expected-root junctions defeat isolation.** `captureCivEngineState` realpaths the configured `.civ-engine-pin` before comparing it with the resolved package. Therefore `.civ-engine-pin -> ../civ-engine` produces `locationMatches=true`. An exact-pin sibling passes normally; a mismatched sibling passes with `--allow-dirty`. Reject a symlink/junction at the configured pin path and prove its physical location remains inside the repository.
- **High — summary stripping bypasses location/runtime policy.** `assertCivEngineStateAllowed(state.summary)` omits `locationMatches` and `runtimeEntryMatches`, allowing exact-content wrong-root state that the full state rejects. Keep historical summaries readable through summary/manifest validation, but require fresh identity fields for execution policy.
- **Medium — advertised Node support is too broad.** Unflagged `import.meta.resolve` requires Node 20.6+, while package/docs promise all Node >=20.
- **Medium — descriptor accepts dangerous install roots.** `scripts`, `.git`, `node_modules`, and `output` all pass validation. Freeze `installPath` to `.civ-engine-pin` or reject reserved/tracked roots before GM-04b consumes it.
- **Low — semver validation is incomplete.** Invalid prereleases such as `1.0.0-01` and `1.0.0-alpha.01` are accepted.

Validation run: focused pin, provenance, recursive-pass, and recursive-CLI suites passed **38/38**. No files were edited by this reviewer.

## Full-state re-review

- **High / Commit-A blocker — full-state identity booleans remain forgeable.** `assertFreshCivEngineIdentity` checks `expectedPackageRootPhysical`, `locationMatches`, and `runtimeEntryMatches` only for boolean type. Reproduction: capture with physical expected root `C:/tmp` yields `locationMatches=false` and is correctly rejected; `{ ...state, locationMatches: true }` is accepted even though `localResolvedPackageRoot` and `localResolvedExpectedPackageRoot` differ. The same technique can bypass a runtime-entry mismatch under `allowDirty`. Validate booleans against their path evidence, and add tampered-full-state regressions.

Focused pin/provenance suite: **22/22 passed** after the workflow parity fix. Configured-root junction rejection, summary stripping, top-level `dist` junction rejection, runtime-resolution mismatch, nested shadowing, and historical-summary tests all passed.

## Final re-review

- **Low — architecture inventory drift after the test split.** `ARCHITECTURE.md` omits `test/civ-engine-provenance.test.mjs` and `test/source-provenance-fixtures.mjs`, and its recursive-loop test paragraph still attributes physical-identity coverage only to the older test files.

The WeakMap fresh-capture fix and provenance/runtime containment are otherwise **clean**. Focused split suites passed **22/22**.

After the architecture update: code re-review is clean; the module-private WeakMap snapshot is registered on both available and unavailable captures, exact deep comparison rejects spread, serialized, and in-place mutation, and normal `captureSourceProvenance` preserves the branded engine reference.

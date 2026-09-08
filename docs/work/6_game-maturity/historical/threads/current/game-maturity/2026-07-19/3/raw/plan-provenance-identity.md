# GM-04a provenance identity audit

Use `scripts/civ-engine-pin.json` as the checked-in single source of truth with a dependency-light strict loader. Reject missing/extra fields, wrong package/schema, unsafe paths, malformed commit/digest/version, and non-canonical repository identity; freeze the parsed descriptor and resolve paths from explicit `repoRoot` rather than ambient cwd.

The critical invariant is that the captured checkout and executed ESM package are one physical identity. Current provenance assumes root `node_modules/civ-engine`, while production uses bare imports and a nested `scripts/node_modules/civ-engine` can win. Resolve `civ-engine/package.json` and `civ-engine` without execution, realpath both, require the runtime URL to equal the declared runtime entry, hash and Git-attest that root, and require setup's configured root to be the same root.

Do not import engine APIs before provenance: `playtest-recursive.mjs` deliberately captures first and dynamically imports engine-dependent modules afterward. Preserve explicit fixture overrides, make relative overrides repo-root-relative, keep the persisted summary schema compatible, and add wrong-version, combined-diagnostic, truthful-match-boolean, location, and runtime-identity tests.

The live sibling is version 2.4.1, commit `2632daca2ea1d1330cf1270962941005354f775b`, and digest `8da72fd76e9f513773bb5f63c899321ffd7a9ef6dbb0cf82d2aec3dbba481971`; the existing gate attributes all three mismatches. The live suite contains 44 tests across five test files.

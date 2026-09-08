# GM-04a reviewed diff

## Dependency and execution boundary

- Add one strict checked-in civ-engine descriptor and dependency-light loader, retain the physical checkout only at ignored `/.civ-engine-pin/`, change package/lock resolution from `../civ-engine` to `file:.civ-engine-pin`, fix npm link behavior, and install only the root runtime graph after building the pin's own development graph.
- Make CI checkout the exact descriptor repository and commit at the same nested path with read-only contents permission and no persisted credentials, then enforce build, root install, provenance, Node test, clean recursive-pass, and Python-test order.
- Raise this repository's Node floor to 20.6 because unflagged synchronous `import.meta.resolve` is part of the enforced pre-execution identity boundary.

## Provenance boundary

- Resolve package metadata and runtime through ESM without execution; require a physical contained configured root, physical package metadata and `dist/`, a contained physical declared runtime, and exact actual/expected package and runtime identity before recursive execution.
- Keep historical summary validation stable while requiring a module-private exact fresh-capture snapshot for execution policy, so stripped, serialized, spread, or in-place forged full states cannot bypass non-overridable location/runtime checks.
- Preserve attributable `--allow-dirty` behavior only for content, commit, digest, or worktree canaries inside the correct physical identity.

## Tests, review, and documentation

- Preserve all 44 pre-GM04 Node names and add 12 descriptor/provenance tests for schema/path/cwd/workflow parity, configured-root and `dist` junctions, nested shadows, conditional runtime mismatch, truthful summaries, and fresh-state tampering. Split hermetic repository helpers and engine-specific tests so every affected production and test file remains focused.
- Update README, architecture, AGENTS, progress, parent cursor/evidence/decision, plan, review, and raw reviewer artifacts. Preserve the unrelated clean sibling, pre-existing `.agents/`, ignored evidence, and public recursive schemas.
- Final local evidence is 56/56 Node, 582 core with 12 expected optional-RL skips, 585/585 exact RL, a clean root npm tree, zero root and pin-runtime vulnerabilities, one moderate pin build advisory with zero high/critical, and three clean independent final re-reviews.

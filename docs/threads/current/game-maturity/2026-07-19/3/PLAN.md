# GM-04 isolated civ-engine plan

Status: GM-03f is remotely finalized at Commit B `be0b1e1812c126e7472a3ed56fe4a66f62d17122`; GM-04a implementation and adversarial review are locally green, and scoped Commit A staging is active

Transaction marker: `[GM-04a:A]`

## Baseline and intent

GM-03f Commit B passed exact workflow run `29725101133`: `build` ran from 07:35:38Z through 07:36:11Z (33 seconds) and `rl-smoke` from 07:35:40Z through 07:39:20Z (3 minutes 40 seconds). `main == origin/main == be0b1e1`, with only the pre-existing untracked `.agents/` tree.

The live `node_modules/civ-engine` junction resolves to the unrelated sibling `../civ-engine` at version 2.4.1, commit `2632daca2ea1d1330cf1270962941005354f775b`, and runtime digest `8da72fd76e9f513773bb5f63c899321ffd7a9ef6dbb0cf82d2aec3dbba481971`. The repository pin remains version 2.2.0, commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, and runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`. The unisolated baseline registers 44 tests and reports 25 pass plus 19 attributable pin failures; the parent plan's 41-test count is stale.

GM-04 establishes a repo-owned ignored engine checkout that never reads, writes, checks out, resets, builds, or otherwise mutates `../civ-engine`. Local and CI package resolution, provenance, and recursive execution must converge on the same physical checkout before the complete Node suite or public recursive commands run.

## Frozen work-unit boundary

GM-04a defines and enforces the pin contract. Add a checked-in `scripts/civ-engine-pin.json`, a dependency-light strict loader, exact `file:.civ-engine-pin` package and lock resolution, `/.civ-engine-pin/` ignore coverage, `install-links=false`, nested CI checkout/build, resolution-without-execution provenance identity, and contract tests. Update manual setup documentation so Commit A never documents the obsolete sibling. Do not add the public setup/verifier command or pre-hooks in this work unit.

GM-04b adds one idempotent cross-platform Node setup/verification command that consumes the descriptor, obtains the fixed public repository without accepting caller credentials or a caller-selected origin, checks out the exact commit detached, installs and builds the engine before root `npm ci --omit=dev`, verifies the exact physical root/version/commit/clean status/runtime digest, and installs fail-fast hooks before every public Node test/playtest entry point. It must use argv arrays, `shell: false`, and `npm.cmd` on Windows; it must never broadly clean `output/`, `node_modules/`, the sibling, or another checkout.

GM-04c freezes the 44 pre-GM04 test names, proves every retained and newly added Node test passes against the pin, runs a clean default recursive pass, proves a link to the live sibling fails before engine-dependent code with actual and expected path/version/commit/digest, proves repeated setup is stable, scans tracked/staged dependency material for credentials, and records exact local and remote results. Post-change acceptance is the exact final `N/N` total, not the stale 41 count and not an assumed 44/44 after new tests are registered.

## Canonical descriptor

`scripts/civ-engine-pin.json` has exactly these fields: `schemaVersion`, `packageName`, `repositoryUrl`, `installPath`, `version`, `commit`, and `runtimeTreeSha256`. The checked-in values are schema 1, package `civ-engine`, fixed credential-free public HTTPS origin `https://github.com/yanfengliu/civ-engine.git`, install path `.civ-engine-pin`, version 2.2.0, the full pinned commit, and the full pinned runtime digest.

The loader reads JSON synchronously from its module URL without importing `civ-engine`; rejects missing/extra keys, wrong schema or package, non-canonical repository URL, credentials/query/fragment, malformed semantic version, non-lowercase 40-hex commit, non-lowercase 64-hex digest, absolute/backslash/traversal/non-normalized install paths, and a resolved path outside the explicit repository root; returns a frozen clone; resolves from an explicit `repoRoot`, never ambient `cwd`; derives `file:.civ-engine-pin`; and exports the existing expected-version/commit/tree-digest names for source compatibility.

Package metadata, lock metadata, `.npmrc`, `.gitignore`, CI checkout/build location, and the descriptor must agree under tests. The lock must contain no `../civ-engine` entry. CI uses the same nested checkout, sets least-privilege `contents: read`, disables persisted checkout credentials, builds the pin before root `npm ci --omit=dev`, and retains runtime digest verification as the immutable engine-content boundary. Mutable major action tags are pre-existing workflow supply-chain scope and are not represented as part of the civ-engine identity guarantee.

## Provenance and execution identity

Default provenance resolves `civ-engine/package.json` and `civ-engine` through ESM resolution without executing either, realpaths the package root and runtime entry, and requires the resolved runtime file to equal the validated runtime entry below that package root. It separately realpaths the configured isolated root and requires physical equality. This closes both the obsolete sibling link and a nested `scripts/node_modules/civ-engine` shadowing path before the recursive script dynamically imports engine-dependent modules.

An explicit `enginePackageRoot` remains available only for hermetic fixture capture and resolves relative values against `repoRoot`; an explicit expected root supports mismatch fixtures. Default execution has no fallback to `../civ-engine`. Location mismatch is never permitted by `--allow-dirty`; attributable version, commit, runtime-digest, and dirty-worktree canaries inside the correct isolated root retain the existing override semantics. Diagnostics include actual and expected roots plus every available version/commit/digest mismatch.

The persisted engine summary schema and `source-state-v2` tag remain unchanged so historical evidence remains structurally readable. Fresh full capture state may carry local expected-root and location-match details, but immutable historical summaries are not retroactively required to name today's location. Summary validation additionally requires the three match booleans to agree with their corresponding actual and expected values.

## TDD and validation

1. Add `test/civ-engine-pin.test.mjs` before the loader exists. The first isolated run must fail at module load because `scripts/civ-engine-pin.mjs` is absent.
2. Pin the exact descriptor and frozen loader behavior, malformed-schema rejection matrix, explicit-root/cwd independence, package/lock/npm/ignore/workflow parity, removal of every sibling path, and the unchanged 44-test baseline-name inventory.
3. Add provenance characterization for explicit repo-root-relative fixture paths, truthful match flags, wrong version, combined mismatch diagnostics, runtime-entry identity, and non-overridable wrong-location behavior while preserving existing commit, dirty, digest, CRLF, unavailable, recapture, and historical-summary tests.
4. Implement the loader and re-export its constants from `source-provenance-engine.mjs`; consume its version in `recursive-pass.mjs`; update fixture roots deliberately; then rewire package, lock, npm config, ignore, workflow, README, and architecture.
5. Materialize the exact ignored pin locally without mutating the sibling, build it, regenerate the lock through npm rather than hand-maintaining it, install the root graph with `npm ci --omit=dev`, and confirm `node_modules/civ-engine` realpaths to the isolated checkout without root-level extraneous packages.
6. Run the focused pin/provenance/recursive tests, the complete Node suite, a clean default recursive pass, full py313 core, and the exact RL environment. Run changed-path pre-commit, dependency/credential/cached-diff audits, `npm audit`, and scoped staging checks. Record actual counts and distinguish unavailable review lanes from approval.

## Review and delivery

This is a high-risk supply-chain and workflow change. Three independent in-process plan lanes read the live package, lock, workflow, provenance, tests, sibling, and roadmap. Their location preference differed, but all required a checked-in strict descriptor, package/lock/CI agreement, realpath identity, resolution-before-execution, stale-count correction, no sibling mutation, and fail-closed diagnostics. `/.civ-engine-pin/` is selected because it is a dedicated retained dependency checkout rather than generated run evidence, gives a stable root-level `file:` specification on Windows and POSIX, and is explicitly ignored. The exact substantive findings and disposition are preserved in `REVIEW.md` and `raw/`.

The fleet-pinned multi-CLI launch remains unavailable at the previously established repository-export authorization boundary. It is not retried or bypassed, and no external approval is claimed. Independently review the live implementation and tests after green local validation, resolve every substantive finding, and rerun affected gates.

Commit A contains the enforced pin contract, tests, workflow/package/lock changes, truthful docs, parent cursor/evidence/decision updates, and review artifacts. Suggested message: `build: isolate pinned civ-engine [GM-04a:A]`. Push A and wait for exact `build` and `rl-smoke` jobs.

Commit B is evidence-only: bind all local proofs and implementation review to A's exact remote result, finalize GM-04a, and open GM-04b while recording B's exact result in the next transaction. Suggested message: `docs: finalize civ-engine pin contract [GM-04a:B]`.

# GM-04 review synthesis

Status: GM-04a implementation review converged clean and Commit B is remotely finalized

## Baseline

All three live-state lanes reproduced `main == origin/main == be0b1e1`, only pre-existing untracked `.agents/`, a live `node_modules/civ-engine` junction to sibling version 2.4.1 at `2632daca...`, and the known 25/44 Node result with 19 attributable mismatches against the 2.2.0 pin. The parent acceptance count of 41 is stale.

## Converged safeguards

The lanes agreed that a JSON descriptor plus loader alone would be dishonest while package, lock, CI, and execution still used `../civ-engine`. GM-04a therefore enforces `file:.civ-engine-pin` across package and regenerated lock metadata, checks out/builds that same nested path in CI, pins npm link semantics, and makes provenance prove that the physical checkout it hashes is the package ESM resolution will execute.

The descriptor is checked in below `scripts/` so it participates in recursive source identity. Its strict loader accepts only the fixed public credential-free origin, normalized root-relative install path, exact schema/name, valid semantic version, full lowercase commit, and full lowercase runtime digest. Package, lock, npm configuration, ignore rule, workflow, and descriptor parity are executable contracts rather than prose assumptions.

The provenance lane identified a High-class shadowing risk: hashing root `node_modules/civ-engine` does not prove a bare import from `scripts/` will execute it because a nested `scripts/node_modules` can win resolution. The plan now resolves package metadata and the ESM runtime without importing them, realpaths both, proves the runtime is the package's declared entry, and proves the package root equals the isolated pin. Explicit fixture roots remain, but resolve from the explicit repository root rather than ambient cwd.

The cross-platform lane identified npm layout sensitivity and `npm ci` deletion order. The plan commits `install-links=false`, builds the retained checkout outside `node_modules` before root installation, and proves realpath equality. The setup command remains GM-04b scope and uses a Node entry point, argv arrays, and `shell: false`; D-017 supersedes the original `npm.cmd` forecast with a validated physical npm CLI launched by the real Node executable after live Windows evidence proved direct `.cmd` execution fails and `cmd.exe` reparsing is unsafe.

## Adjudicated differences

Two lanes preferred `output/dependencies/civ-engine` because `output/` is already ignored. One preferred `/.civ-engine-pin/` because it avoids conflating a retained dependency checkout with generated evidence. The selected `/.civ-engine-pin/` location is dedicated, explicitly ignored, stable across pin changes, directly expressible as `file:.civ-engine-pin`, and covered by the same containment/realpath requirements. Cleanup is always exact-path and never broad.

One lane recommended deferring all package rewiring to GM-04b. The stronger finding was that a descriptor which leaves actual package/CI resolution on the sibling is not an enforced contract. GM-04a therefore owns descriptor, dependency, workflow, and provenance enforcement plus accurate manual setup docs; GM-04b still owns the safe idempotent setup/verifier command and public pre-hooks, matching the parent substep boundary.

## Multi-CLI boundary

The fleet-pinned external workflow previously stopped before either reviewer executed because repository-context export to the external Claude destination was not authorized. That authorization has not changed. The launch is not bypassed, no external reviewer is represented as having read this plan, and no external approval is claimed.

## Implementation findings and disposition

The provenance and supply-chain lanes found two High isolation bypasses: the configured pin itself could alias the sibling, and a top-level `dist/` junction could escape the physical package. The implementation now requires a non-link contained configured root, a physical `dist/`, contained physical package metadata and declared runtime, and equality with ESM's resolved runtime. Dedicated junction, conditional-export, and nested-shadow regressions reject every identity mismatch even with `--allow-dirty`.

The provenance lane found that historical-summary stripping and forged full-state booleans could omit or falsify location/runtime identity. Historical summaries remain readable only through summary validators; execution policy now accepts only the exact unchanged object registered by a module-private capture snapshot, rejecting serialization, spreading, and in-place mutation. Match booleans in the persisted summary remain derived and truth-checked.

The supply lane found unsafe PowerShell continuation, an overly broad Node 20 declaration, incomplete checkout/order tests, and audit attribution against the wrong graph. Manual bootstrap refuses any existing pin path and checks every native exit, Node support is 20.6 or newer, workflow tests enumerate every checkout action and bind descriptor-derived repository/ref/path plus build/install/provenance/test/pass bodies and order, and evidence separately records root, pin-build, and pin-runtime audits.

The test/documentation lane found dangerous-but-normalized install paths, incomplete semantic-version validation, cwd-dependent relative repository roots, an oversized mixed provenance test, and stale architecture inventory. The install path is frozen to `.civ-engine-pin`, numeric prerelease leading zeroes reject, repository roots must be absolute, engine regressions and shared fixtures are split into focused files, and architecture names the new boundaries.

## Final review gate

The three independent final re-reviews returned `CLEAN`. Focused pin/provenance/source validation passes 22/22; the final serial Node suite passes 56/56 while preserving all 44 baseline names; full py313 passes 582 with 12 expected optional-RL skips; exact RL passes 585/585. Scoped pre-commit passes check-yaml, EOF, and trailing-whitespace for all 34 paths; Ruff hooks correctly skip with no changed Python. A direct YAML fallback caught and closed the inline-run scalar defect before this final pass. Exact scoped staging contains 34 paths with 3,769 insertions and 292 deletions, no unstaged tracked delta, clean cached whitespace and credential-signature checks, and only the preserved `.agents/` tree untracked. The fleet-pinned external workflow remains unavailable at the established repository-export authorization boundary, so no external approval is claimed. Commit A passed its exact remote gate.

## Remote implementation gate

Implementation Commit A `585dc6067d1c8c2c0a115bd31f1d4e238dc25ddc` passed exact workflow run `29730625404`: `build` succeeded in 35 seconds and `rl-smoke` in 3 minutes 44 seconds. Evidence-only Commit B binds that result before GM-04b begins.

Evidence-only Commit B `28a6c7e6082f03a0590fb27d99996837575d5062` passed exact workflow run `29731075431`: `build` succeeded in 34 seconds and `rl-smoke` in 4 minutes 41 seconds. GM-04a is remotely finalized.

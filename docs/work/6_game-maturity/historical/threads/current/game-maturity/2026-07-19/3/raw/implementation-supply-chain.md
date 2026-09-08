# Supply-chain and workflow implementation review

## Initial review

- **HIGH — configured-root alias bypass.** A `.civ-engine-pin` junction/symlink to `../civ-engine` can pass location identity. Require the configured pin root itself to be a physical non-link directory and add a configured-root-to-sibling rejection test.
- **HIGH — unsafe manual setup sequence.** In PowerShell, failure of `git clone` does not stop subsequent native commands. If `.civ-engine-pin` already aliases the sibling, checkout, `npm ci`, and build can continue through that alias. Add explicit fail-stop guards or defer setup to GM-04b's safe command.
- **MEDIUM — declared Node floor is too low.** Production uses unflagged synchronous `import.meta.resolve`, but package and docs promise all Node >=20. Raise the floor to `>=20.6.0` or use a compatible resolver.
- **MEDIUM — audit evidence targets the wrong build graph.** Root `npm audit --json` reports zero vulnerabilities, but CI builds the pin with `.civ-engine-pin/package-lock.json`. Audit that actual lock separately and do not describe root zero as the complete build-chain result.
- **MEDIUM — workflow contract tests are under-scoped.** Tests do not bind canonical repository, credentials, or build/install/provenance/test ordering to the relevant YAML blocks.

Verified clean at the initial review: focused pin tests 6/6; current pin root physical; installed engine linked to it; unrelated sibling clean and unchanged; current CI least privilege and ordering correct; all 150 registry resolutions use npm HTTPS URLs with integrity; no credential signatures found.

## Final re-review

CLEAN. The workflow contract now checks every checkout step, enforces `persist-credentials: false`, validates descriptor-derived repo/ref/path, and verifies build/install/provenance/test ordering.

Validation:

- `node --test test/civ-engine-pin.test.mjs`: 6/6 passed
- `npm ls --depth=0`: clean, with `civ-engine@2.2.0` linked from `.civ-engine-pin`

No remaining actionable supply-chain/workflow findings. Final audit evidence should still be reported from the parent's exact rerun, not inferred from this review.

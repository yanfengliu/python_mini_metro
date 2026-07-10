# Final in-process adversarial review

Verify each claim in the plan/diff against the live codebase — grep for the symbols, function signatures, column names, and file paths it references; do not approve based on prompt text alone.

1. **High — platform-specific runtime digest.** The initial `civ-engine` tree pin hashed raw Windows checkout bytes. Since the sibling uses `core.autocrlf=true`, Ubuntu's valid LF checkout would fail the default provenance gate. Canonicalize line endings for known text runtime files, recompute the pin, and exercise a default pass on Ubuntu CI.
2. **Medium — dangling final patch reference.** The mismatch error retained ending state but not ending provenance, while the driver expected `endProvenance.sourceDiff`; a changed final state could name a patch that was never written. Retain ending provenance and cover the full CLI artifact path.
3. **Medium — engine import before attribution.** `recursive-pass.mjs` statically imports `civ-engine`; importing it before the start snapshot lets executable bytes load before they are attested. Capture first, then dynamically import the engine-dependent pass/verifier modules.
4. **Low — architecture tree drift.** Include the split lock module and all Node tests/helpers in the file map.

While implementing the requested CLI regression, it exposed another correctness defect: finalization correctly changed the persisted manifests to `run-failed`, but the top-level CLI still printed and exited from the earlier success object. `finalize()` now returns the attributed result and the caller uses it for output and exit status.

Fresh re-review of the live fixes found no substantive remaining issue. It independently resolved the canonical runtime digest, verified capture-before-dynamic-import ordering, traced ending provenance into the final patch, checked the attributed CLI result, and ran the focused source/end-to-end suites (17/17). One duplicate architecture-tree entry was removed as cosmetic cleanup.

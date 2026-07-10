# In-process provenance re-review

Verify each claim in the plan/diff against the live codebase — grep for the symbols, function signatures, column names, and file paths it references; do not approve based on prompt text alone.

- **High:** a one-time start snapshot leaves a time-of-check/time-of-use gap. Recapture immediately before finalization and fail the pass if either summary changes.
- **High:** the live linked `civ-engine` runtime is executable source but was outside the repository inventory. Resolve the actual package path and attest version, commit, dirty state, and runtime files.
- **High:** Git status cannot detect the real sibling's ignored built `dist/`. Pin and verify the complete `package.json` plus `dist/` tree digest independently of Git dirtiness.
- **High:** manifest files were written before a recovery intent existed. Use a versioned intent containing both manifest payloads and target paths, then create files and ledger rows through reconciliation.
- **Medium:** an interrupted JSONL append leaves an unterminated final fragment that blocked recovery. Under the ledger lock, truncate only an unterminated last fragment; fail closed for terminated or earlier corruption.
- **Medium:** the architecture map omitted new provenance and lock boundaries, and final clean/canary evidence still had to be regenerated after commit.

Final re-review additionally found that the first runtime digest used raw Windows bytes, the ending provenance object was not attached to a mismatch error, and the pass module imported `civ-engine` before start capture. These were accepted for cross-platform canonicalization, complete final-patch evidence, and post-attestation dynamic import.

Re-review request: mutate a gitignored engine runtime file, compare start/end snapshots, and inject crashes after intent, each manifest, and each ledger row.

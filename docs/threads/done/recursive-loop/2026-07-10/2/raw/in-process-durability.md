# In-process durability review

Verify each claim in the plan/diff against the live codebase — grep for the symbols, function signatures, column names, and file paths it references; do not approve based on prompt text alone.

- **High:** stale lock recovery could remove a successor's lock after the original owner changed. Require an owner token, heartbeat, liveness check, and token-checked release.
- **High:** writing the two aggregate ledgers separately could expose a durable half-pair after interruption. Persist a recoverable pair intent and reconcile both rows under one lock.
- **Medium:** dirty-run provenance was only a boolean/digest, making accepted canary evidence hard to attribute. Preserve the relevant file inventory, Git status, and source patch.
- **Medium:** one-intent-at-a-time reconciliation repeated complete ledger scans. Load/index each ledger once and reconcile a batch.
- **Medium:** failure drills and review results need retained evidence rather than console-only claims.

Re-review request: verify token ownership against the live lock implementation, inject interruptions at every persistence boundary, and confirm retries are exact/idempotent.

# GM-06c schema and replay risk research

Read-only live-code audit; no files were edited by the research lane.

- Current recursive validation only special-cases locomotive actions; an unknown generic action can otherwise pass JSON validation. Adding carriage actions without a new schema would let an old v1-v4 document change behavior. Checkpoint v4, recursive v5, and agent-play v5 are therefore mandatory.
- Multiple locomotives per line exist while fleet actions select a path only. A deterministic Metro target must be fixed before tests; process-local Metro IDs must not enter persisted actions.
- The roadmap does not select starting inventory, per-carriage capacity, or a per-Metro limit. Six seats is structurally consistent with the existing locomotive; starting count must be an explicit provisional product choice.
- Canonical composition must not duplicate a global unassigned pool. Every attached identity belongs to exactly one canonical global Metro list; assigned and available derive from that ownership. Derived capacity avoids cached-counter rollback drift.
- Current checkpoint prefix validation covers queue state and aggregate capacity but not future carriage identities/order. V4 needs total inventory, structured entities, per-Metro references, full motion-union carriage state, exact stale-observation checks, count/type/duplicate/range/capacity rejection, and immutable legacy normalization.
- V1-v3 checkpoint generation must reject every attachment, including a path-only latent Metro suffix. Recursive/agent v1-v4 must reject carriage actions before reset or mutation. Persisted v5 carriage actions must contain only `type` and `path_index`.
- Route replacement and every attach failure seam need exact rollback tests over list object identity, ordered contents, capacity, passengers, and checkpoint state. Line removal refunds attached resources through derived global ownership, but GM-06d still owns occupied-rider cleanup.
- Rendering must use ordered bodies and passenger slices rather than expanding one locomotive body. A second control row and fourth HUD line require explicit hit/reachability/exclusion tests.

# GM-01c persistence plan review

NOT APPROVED before amendment. HIGH: preserve immutable v2 identifiers and replace latest-version equality routing before advancing either persisted format to v3.

Grounding: recursive validation currently accepts only legacy v1 plus the mutable current version; required reward fields and recorded-input reconstruction branch on equality with that mutable current version. Agent-play support similarly has only v1 plus a mutable current v2 identifier. Node verification preserves reward metadata only for exact v2, and the runner currently passes scenario version directly to the v1/v2-only checkpoint writer.

Required amendment: retain named v1/v2/v3 identifiers and explicit routing; preserve the delivery reward contract for v2/v3, add the threshold only in v3, map scenario v1 to checkpoint v1 and scenarios v2/v3 to checkpoint v2, and test literal v2 paths through Python inputs mode, zero-argument factories, agent replay, and fresh-process Node verification.

Amended-plan re-review: APPROVED with no remaining HIGH or MEDIUM persistence defect.

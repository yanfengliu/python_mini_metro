# GM-06c core/conservation RED evidence

Status: `CLEAN` test contract; intentionally RED product state; production unchanged

The first independent RED audit returned `NOT CLEAN`. It found target-local rollback coverage, vacuous custom-list failures, unpinned total inventory, missing exact list identity/order assertions, weak mixed-candidate selection, missing owner-removal rollback, single-carriage route-replacement checks, absent real-station reconciliation failures, shallow rejection fingerprints, equality where identity was required, missing zero-capacity/read-only/reset boundaries, and a factory seam pinned to `mediator` module placement.

The revised suite froze `CarriageManagement.attach(host, path, *, get_carriage_factory=..., reconcile_station_service=...)` and `CarriageManagement.detach(host, path, *, reconcile_station_service=...)`, expanded the rollback graph to two paths/Metros/plans, and added exact conservation, identity, lifecycle, route-replacement, corruption, cache, and rejection-purity cases. Subsequent cross-review found and closed target-ordering, nonvacuous detach corruption, topology aliasing, outer factory resolver, callback-footprint, mutable Carriage-state, lifecycle callback, BaseException identity, query purity, nonempty cache, zero capacity, explicit-detach retirement, malformed line removal, and multi-Metro replacement gaps.

The final fresh gate found only two narrow omissions: live detach extra-key tolerance and canonical checkpoint-v4 equality for rejected actions. Both were added and the bounded recheck returned `CLEAN`.

Final focused evidence:

- 47 core/conservation test methods collected.
- Ruff check and Ruff format-check passed for every core RED file.
- Compilation/collection had no harness defect.
- Remaining failures/errors terminate only on absent GM-06c product surfaces or explicit missing-behavior assertions.

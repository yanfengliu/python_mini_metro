# GM-06c implementation review - conservation

Status: `NOT CLEAN` on the initial live-code pass.

- Route-replacement rollback omitted `Metro.num_carriages` and the identity, capacity, and shape of attached `Carriage` objects.
- Successful replacement could leave stale station-service timing/action caches.
- Service-cache validation accepted noncanonical unbound state too broadly.
- Attach/detach could accept a no-op reconciliation because permissive preflight state was reused as the successful postcondition.

Each finding was reproduced against live code and returned for test-first correction.

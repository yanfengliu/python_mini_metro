CLEAN.

The direct `get_reduce_node_path()(list(node_path))` composition now matches `HEAD`:

- The reducer is resolved before copying the raw path.
- Its temporary callable is released immediately after invocation, before candidate-cost reads or bulk plan installation.
- The reduced path itself remains retained in the bulk generator frame through arrival fallback handling.
- Raw one-node arrival provenance and exact `len()` ordering are unchanged.
- Arrival effects still precede destination-iterator finalization.
- Finalization still precedes the fallback guard.
- Destination/prior-route locals remain alive through that guard.
- Adjacent-passenger live-list skipping is unchanged.

The new ephemeral-reducer facade test passed, along with the arrival lifetime/finalizer, route-provenance, resolution-order, adjacent-arrival, and iterator suites: 36 targeted tests passed.

Read-only audit complete; no files changed.

Current implementation is semantically correct for the two reported regressions:

- `RoutePlanner._iter_best_node_path_selections(...) -> Iterator[tuple[list[Any] | None, bool]]` classifies raw arrival before compression and preserves original `len()` call counts.
- `iter_bulk_route_proposals(...) -> Iterator[tuple[station, passenger, route, Literal["arrival", "route", "fallback"]]]` yields arrival while the destination iterator is suspended, closes it after caller-applied arrival effects, then yields fallback for the same passenger before advancing the live passenger list.
- The `try/finally` around the arrival yield is important: aborting or closing the proposal iterator still closes the suspended selector.
- `find_best_node_path(...)` closes its selector in `finally`, so a direct arrival return finalizes the destination iterator before control returns.
- Callable resolution now matches `HEAD`:
  - reducer getter before `list(node_path)`;
  - shared-path getter before `reduced_node_path[1]`;
  - plan-factory getter before `best_node_path[1:]`;
  - a fresh shared-path getter for final wiring.
- Facade getters must return the bound callable directly, as currently implemented. A wrapper such as `lambda: lambda nodes: self.skip_stations_on_same_path(nodes)` would reintroduce the timing defect.
- The facade no longer remeasures a route, so a raw multi-node route compressed to one node remains a route and follows the original assertion-producing behavior rather than becoming a false arrival.
- Arrival effects retain original order: station removal, global removal, destination flag, plan deletion; iterator finalization; fallback short-circuit guard.

Live verification:

- All 8 new observability and resolution-order tests pass.
- The broader route-contract facade tests pass.
- At the instant audited, older direct planner tests still needed their mechanical keyword and tuple updates; they produced 19 `TypeError`s from old `reduce_node_path`/`find_shared_path`/`make_plan` arguments and three-value unpacking, not production-semantic failures.

One exotic edge remains outside current tests: `HEAD` retains the destination iterable object in a mediator local through fallback, whereas the helper may release that iterable object when the selector closes. This is observable only through destructor/refcount side effects; normal iterators, generator finalizers, game objects, and all characterized mutation contracts are preserved. I would not complicate the design for it unless byte-for-byte Python object-lifetime equivalence is a stated requirement.

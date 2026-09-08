MEDIUM — `src/route_planner.py:223-234` releases selection-loop locals too early.

After an arrival, `selections.close()` correctly finalizes the destination iterator after arrival effects, but it also destroys the selection frame before yielding `"fallback"`. For non-arrivals it closes the frame before yielding the route/fallback proposal. In `HEAD`, the loop’s last `possible_dst_station`, `start`, `end`, `node_path`, and prior `reduced_node_path` locals remain alive through plan creation or the fallback guard.

I reproduced an observable difference with an ephemeral destination yielded by a generator whose `__del__` resets `passenger.is_at_destination`:

- Current code releases it during `selections.close()`, before the fallback guard, so the guard installs a fallback plan.
- `HEAD` retains `possible_dst_station` through the guard, so no plan is installed; the destination is released afterward.

The existing retention test covers the destination iterable container, not its yielded destination or other selection locals.

Recommended fix:

- For non-arrivals, keep the selection generator suspended through the caller’s route/fallback action and close it afterward.
- For arrivals, resume the selection normally after the arrival action so it exits the destination loop and finalizes that iterator, then suspend it once more after the loop while the fallback guard runs. Close it only after that guard. This preserves both required timings without trying to enumerate every local reference to retain.

No other actionable bulk-routing mismatch found:

- Raw one-node arrival provenance is preserved.
- Raw and reduced path `len()` counts match `HEAD`.
- Arrival effects precede destination iterator finalization.
- The fallback guard follows finalization.
- Live passenger-list removal preserves adjacent-passenger skipping.
- Current cleanup paths otherwise unwind safely.

Validation: 27 targeted mediator/route-planner contract tests passed.

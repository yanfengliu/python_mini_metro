# GM-03c plan refutation

The refuter found that the apparent routing cluster is not wholly pure. Destination lookup advances Python RNG; bulk planning mutates live passenger collections during iteration; `TravelPlan.get_next_station()` mutates its cached field; read-only boarding lookahead still shuffles and constructs plans; BFS ties depend on insertion order; and plans retain exact ephemeral graph nodes/path sets consumed by checkpoints and invalidation.

It also verified two easy-to-miss baseline behaviors: adjacent arrived passengers can be skipped until the next call because the live station list is mutated during iteration, and unreachable passengers consume RNG again on every retry. Those behaviors must be characterized rather than silently repaired.

Recommended correction: the stateless planner consumes already ordered candidates and fresh explicit graphs; Mediator retains RNG, mutation, topology, and effects. To satisfy the size gate without stealing GM-03d/e, extract the constrained planning portion of boarding-candidate discovery as a lazy proposal iterator. Mediator applies a yielded plan before the next passenger is requested, preserving callback and mutation timing. Hard acceptance is at most 1,111 mediator lines, target at most 1,100.

## Precise-plan finding

The first precise-plan review found one blocking compatibility gap: passing `bfs` or bound public methods directly captures the callable once, while baseline performs a fresh lookup on every destination/passenger iteration. A first callback can rebind the next call. The plan was corrected to require resolver thunks whose bodies perform each global/attribute lookup and to characterize rebinding between iterations. All other reviewed invariants aligned; the hard 1,111-line ceiling appeared feasible, while the 1,100 target remained intentionally tight.

The next re-review found one remaining object-identity gap: an unreachable retry already has a live `TravelPlan([])`, and baseline's exact guard preserves it rather than assigning a replacement. The bulk-proposal application contract and characterization matrix now require `not passenger.is_at_destination and passenger not in travel_plans` before inserting a new empty sentinel.

Final re-review result: **APPROVED**. The corrected plan preserves sentinel identity, constrained/bulk mutation order, fresh resolver lookup, lazy timing, public dispatch, graph access, and RNG order; the revised tight size budget is feasible.

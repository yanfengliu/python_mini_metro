Approved. With the stated constraints, sole scalar ownership in `Progression` is not materially less safe than a stateless host-Protocol helper and gives a clearer boundary.

Required invariants:

- Construct `_progression` before the first forwarded property access in `Mediator.__init__`.
- Forward the exact mutable list objects for milestones and prices.
- Property setters must perform raw assignment only—no validation, coercion, recomputation, or eager synchronization.
- Preserve one-time initialization semantics: sorted milestone copies, prices computed once, and externally changed purchase counts remaining stale until an explicit update.
- Limit ownership to progression fields. Keep metro limits, spawning state, time, RNG, stations, buttons, and other entities outside it.
- Keep real `Mediator` methods, including legacy aliases, and preserve per-passenger public-hook call ordering.
- Do not give `Progression` a mediator backreference or entity imports.

I found no live consumer of `Mediator.__dict__`, `vars()`, pickle, or deepcopy. Therefore, moving instance fields behind explicit properties does not break a current repository contract. Canonical checkpoints, environments, rendering, and tests use ordinary attribute access and remain compatible.

The only structural change is private reflection/pickle layout. That should not be preserved speculatively. For GM-07, serialize an explicit versioned snapshot through facade fields rather than pickling `_progression`. For GM-10, evolve the private component while retaining today’s public properties and methods.

Compared with a host Protocol, this design avoids a broad mutation interface and establishes genuine ownership without duplicating state. Add tests for direct writes, mutable-list identity, stale-until-update behavior, checkpoint equality, and constructor initialization order.

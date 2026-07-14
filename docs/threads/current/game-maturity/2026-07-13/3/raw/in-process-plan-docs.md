Recommendation: choose A, with a thin-adapter refinement.

`Progression` should be the sole owner of progression scalars/config. `Mediator` should retain explicit properties and method wrappers, while entity/UI collections remain on `Mediator` and are passed transiently or updated from returned transition data. Do not introduce a broad mutable-host `Protocol`.

| Dimension | A: stateful owner | B: stateless host controller |
| --- | --- | --- |
| Parent plan | Strong match: real “progression and purchase ownership” and a composed collaborator (`PLAN.md:106-109`, `DECISIONS.md:35`) | Weak match: moves functions, but progression state remains owned by the god facade |
| No duplicate state | Strong if facade uses properties only | Strong at runtime, but does not create the intended ownership boundary |
| Compatibility | Slightly riskier, but explicit properties/wrappers preserve current callers | Lowest immediate diff risk because raw fields remain |
| Debuggability | One inspectable progression source of truth; isolated transition tests | Every operation mutates a large host indirectly; stack traces and invariants span controller plus host |
| Typing | Narrow explicit constructor/method inputs | Requires a large mutable `Protocol` mirroring much of `Mediator`; high structural coupling |
| Future GM-07 saves | Progression state has a natural serialization boundary | Save code must continue scraping unrelated fields from `Mediator` |
| Future GM-10 upgrades | Clean foundation if this class remains scoped to current network progression | Host protocol expands as calendar, inventory, and upgrades arrive |
| GM-03b scope | Bounded if entity references are not retained | Smaller diff, but insufficient architectural outcome |

Why A is preferable:

- Current progression state and behavior are one responsibility cluster: configuration/state at `src/mediator.py:67-76,109-114`, aliases at `120-138`, and calculations/purchases/unlocks at `186-282`.
- The component can own `deliveries`, `line_credits`, `purchased_num_paths`, unlocked counts, milestone lists, and purchase prices without owning `stations`, `all_stations`, or `path_buttons`.
- Existing cross-domain consumers already use the `Mediator` surface, so explicit delegation preserves them: `env.py`, `recursive_checkpoint.py:390-405`, `game_renderer.py:176-178`, and `rl/player_env.py`.
- A host `Protocol` would need nearly every mutable field used by lines 186-282, becoming a structural duplicate of the mediator’s shape and permitting uncontrolled mutation. That is procedural extraction, not a meaningful composed boundary.

Recommended refinement:

- Store entity collections only on `Mediator`.
- Let `Progression` methods either:
  - accept `path_buttons`, current stations/pool, and `time_ms` transiently; or
  - return compact transition information such as newly unlocked path/station indices, which the facade applies.
- Prefer the simpler of those two after comparing wrapper size. Do not add a second stateless controller.
- Keep active `stations` on `Mediator`; keep only `unlocked_num_stations` in `Progression`.
- Keep unrelated state such as overdue threshold, passenger spawning, paths, and metros outside `Progression`.
- Document the class as current line/station/economy progression so GM-10 does not automatically turn it into another god object.

Blocking conditions for A:

1. No scalar/config duplication. `Mediator` must not retain separate authoritative values alongside `Progression`.
2. Use explicit properties; no magical `__getattr__`/`__setattr__`.
3. Preserve writable behavior for `deliveries`, `line_credits`, `score`, `total_travels_handled`, and `purchased_num_paths`.
4. Preserve all existing public method signatures and instance-level mocking behavior.
5. Preserve list/value semantics for milestones and `path_purchase_prices`; do not return fresh copies that change identity/mutation behavior accidentally.
6. Preserve atomic delivery behavior: one delivery increments both counters before unlock evaluation (`mediator.py:909-912`).
7. Preserve UI/entity effects exactly: foreign-button rejection, lock checks, sequential purchase, multi-unlock blinking, relocking behavior, and non-shrinking active station lists.
8. Do not capture `Mediator`, station lists, or button lists inside `Progression`; that would create a cyclic state graph and weaken save/debug boundaries.
9. Add isolated progression tests plus facade compatibility/differential tests before accepting the move.

B is acceptable only as a documented temporary fallback if explicit properties demonstrably break a real supported contract—such as current serialization, monkeypatching, or direct-write behavior that cannot be retained. No such blocker is visible in the live code. If B were chosen, it should not be claimed as completed “progression ownership”; a later state-ownership extraction would remain required.

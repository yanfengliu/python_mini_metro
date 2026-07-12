# GM-01c implementation scope

## Runtime mechanic

- `config.overdue_passenger_threshold` and `Mediator.overdue_passenger_threshold` make `2` the canonical fresh-game default; the config value alias and writable mediator `max_waiting_passengers` property remain compatible.
- Inclusive station-queue counting ends a default game at the second overdue passenger. Metro riders remain excluded and explicit threshold `1` preserves the former rule.

## Persisted compatibility

- Recursive scenario/input v3 records `overduePassengerThreshold`; immutable v1/v2 routes reconstruct threshold `1`, v2/v3 retain deliveries reward, and scenario v1 maps to checkpoint v1 while v2/v3 map to checkpoint v2.
- Agent-play v3 records the post-reset threshold. Schema-less/v1/v2 reconstruct threshold `1`; malformed v3 records and environments without a real threshold control fail closed.
- The default recursive fixture advances to v3 and a checked-in literal v2 fixture protects fresh-process compatibility. Node input projection retains reward for v2/v3 and threshold for v3.

## Tests, docs, and identity

- Focused new modules cover runtime overload, recursive v3 migration, and agent-play v3 migration without enlarging the oversized mediator test. Pixel terminal precedence, checkpoint aliases, and fresh-process Node paths are pinned.
- README, game rules, architecture, progress, the directional 12-seed baseline, and persistent state/evidence are synchronized.
- Protocol remains `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`; default task remains `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`; environment content intentionally changes from `feb81d5d64e8304318c54cffc44cc105d6c16e9ef06cbe24c45d9ba3f01958cf` to `3fa9b5b78750d9a1c113e4da76ea669466f485a14d8df6702705610ed868dd60`.

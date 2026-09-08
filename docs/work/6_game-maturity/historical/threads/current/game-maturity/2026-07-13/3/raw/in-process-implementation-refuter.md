# GM-03b purchase-dispatch refutation

The initial extraction delegated affordability entirely to `NetworkProgression`, bypassing the mediator's public next-index and price methods. A price override of `999` with `90` credits incorrectly allowed purchase and produced `-909` credits.

The first correction resolved both public queries eagerly. That preserved overrides but still queried price for skipped or fully purchased targets, unlike the baseline's next-index short circuit.

The final implementation restores the exact order:

1. Resolve the public next-index method.
2. Return `False` immediately for `None` or a mismatched target.
3. Only then resolve the public price method and evaluate affordability.

Verified:

- A raising price method is not called for skipped or full targets.
- Price `999` with `90` credits yields `can_purchase=False` and `purchase=False`.
- Credits remain `90`; purchased and unlocked counts remain `1`.
- Both override-affordability and short-circuit regression tests pass.

Final conclusion: **CLEAN**.

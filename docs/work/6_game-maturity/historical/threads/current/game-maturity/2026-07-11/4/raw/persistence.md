# Persistence adversarial review

Initial findings:

- HIGH: `PlaythroughRecord.overdue_passenger_threshold = 1` manufactured a required v3 field when callers omitted it.
- MEDIUM: threshold-blind environments could record or accept a v3 threshold that their game-over logic did not consume.

Independent agents and the driver confirmed both. The field now defaults to `None`, which v3 rejects before reset while v1/v2 ignore it and reconstruct threshold 1. Capture/replay now require either the canonical or legacy mediator control. Re-review verified schema-less/v1 threshold 1, literal v2 deliveries plus threshold 1, explicit v3 recorded threshold, 36/36 focused Python tests, 6/6 Node verifier tests, literal-v2 fresh replay, and complete v3 fresh replay. APPROVED with no remaining HIGH or MEDIUM finding.

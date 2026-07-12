# Runtime adversarial review

Initial findings:

- HIGH: a public v3 `PlaythroughRecord` omitted threshold inherited dataclass default `1` and replayed successfully, silently changing a fresh environment from threshold 2 to 1.
- MEDIUM: capture defaulted to threshold 1 and replay dynamically created an inert field when a supplied mediator exposed neither canonical nor legacy threshold control.

Both claims were reproduced against live code. After fixes, actual-dataclass omission, threshold-blind capture, and threshold-blind replay all fail closed; legacy-only and canonical controls still apply correctly. Focused regression set passed 48/48. Re-review: APPROVED with no remaining HIGH or MEDIUM finding.

Review found five issues:

- Medium: compact JSON’s documented size/SHA hashes current CRLF bytes, but Git will normalize to LF. Committed bytes become 17,654 bytes / `d6d1a800...`, not 17,655 / `43d4e2cf...`.
- Medium: README overstates authentication; per-run `run-summary.json` and `worker-result.json` lack exact byte hashes/sizes.
- Medium: “decision-recomputable” rows omit per-run `batchSize` and `nEpochs`, required by `evaluate_promotion`.
- Low: parameter text says ~1.51M excluding MLPs; exact core is 1,450,005, while full policy is 1,491,221 including MLPs.
- Low: “448–509 KiB” should be 438.2–497.4 KiB, or 449–509 decimal kB.

All measured values, gates, raw directory totals, offsets/fingerprint, defaults, state cursor, YAML, and embedded PowerShell otherwise verified clean.

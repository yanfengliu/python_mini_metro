# GM-06c schema/replay RED evidence

Status: `CLEAN` test contract; intentionally RED product state; historical controls GREEN; production unchanged

Frozen controls were created before production changes:

- `scripts/fixtures/checkpoint-v3.json`: 16,262 LF bytes, SHA-256 `9ca2f5bce174a8c59c608cb08bc3e5903151ab0ad04df6553c21f166bed63c02`.
- `scripts/fixtures/recursive-playtest-v4.json`: 1,608 LF bytes, SHA-256 `807429bf99283a79341c1e78d4984880ec53deaccab1d5bc36ec2b4cf9610cee`.
- `scripts/fixtures/gm06c-pre-carriage-outcomes.json`: 6,486 LF bytes, SHA-256 `d070943f3de09df8cb18ef6e96caea875dd72541f5b5598c669e35563459e67a`.

The first independent RED audit returned `NOT CLEAN`. It found a malformed positive suffix fixture, nonexhaustive Python/Node bijection oracles, incomplete v4 scalar/UUID/cache/capacity negatives, missing recorded-input and agent full-record preflight, partial legacy forward-field rejection, and an in-process-only hash-seed claim. Those were corrected with fresh `PYTHONHASHSEED=0` subprocesses and focused split modules.

The second cross-review closed seven remaining gaps: v1/v2 forward carriage fleet state, malformed and valid-detach v5 recorded inputs, valid-versus-stale nonempty service cache, isolated list aliases plus global/suffix duplicate identities and IDs, normalized count/total/overcapacity/queue invariants, float/string/None and UUID-bearing fields, and raw multi-owner flattening order.

Final focused evidence:

- 37 schema/replay product test methods collected; intentionally RED with 53 failures and 26 errors against the untouched v3/v4 implementation.
- Python historical controls: 4/4 GREEN, including two fresh hash-seed-zero processes.
- Node historical controls: 2/2 GREEN.
- Node v5 product tests: 0/2, both failing on the intended absent v5 projection/redrive behavior.
- Ruff check and Ruff format-check passed on all six Python schema/replay files; Node syntax checks passed.
- Frozen bytes and hashes remained exact.
- Final fresh independent verdict: `CLEAN`; all 15 enumerated audit findings were closed nonvacuously without implementation overconstraint.

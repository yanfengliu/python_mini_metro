# GM-06b schema and replay final recheck

Status: `CLEAN`

The latest plan binds fleet total to `progression.limits.num_metros` with exact non-boolean integer typing. Canonical generation validates ordered unique observation Metro IDs against the live global sequence before building the union, and normalized JSON compares every executable shared prefix field with the correct declared-owner mapping plus position, station, ordered passengers, and queue. Swaps, stale supplied observations, duplicate IDs, total-alias drift, and queue disagreement all have explicit rejection rules.

V1/v2 generation/bytes and false-injection normalization remain isolated and testable. Recursive/agent/Node v4, UUID-free index persistence, the pre-tick legacy adapter, named fixtures/oracles, and production file-size gates remain coherent. No substantive schema or replay finding remains.

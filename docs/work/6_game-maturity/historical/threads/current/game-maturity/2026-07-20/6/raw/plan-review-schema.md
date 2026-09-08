# GM-06b schema and replay plan review - first pass

Status: `NOT CLEAN`

1. `P1` - Legacy automatic-assignment timing is not tight enough. Historical completion created and initialized the metro before the operation's one tick. Require create, public assignment when the pre-action inventory predicate allowed it, the original single tick, then fresh observation/reward, with exactly one outward action row. Compare nonzero-dt recursive v1-v3 and agent v1-v3 against frozen legacy evidence.

2. `P1` - Checkpoint-v3 correspondence and normalization are ambiguous. Structured metros contain only global assigned metros, while `metroMotion` is the ordered unique union of global and path-owned metros. Specify exact boolean types, the global-prefix correspondence, allowed path-only suffix, queued-count basis, false injection into both lists for v1/v2, full-union refusal for old generation, exact old serialized bytes, and input immutability.

3. `P1` - Recursive v4 is incomplete at the Node verifier boundary. `scripts/playtest-verify.mjs` currently projects only v2/v3 reward fields and the v3 threshold. Add a v4 branch that preserves all three v4 contract fields, default v4 drive/redrive coverage, and literal v1/v2/v3 projection preservation.

4. `P1` - Persisted replay is not guaranteed UUID-free. Decide whether v4 persisted actions canonicalize fleet IDs or reject `path_id`; define the exact agent-v4 contract field and make v1-v3 reject that field and explicit fleet actions before mutation. Test that persisted/replayed fleet actions contain no entity UUIDs.

5. `P1` - The file-size plan misses the 475-line `InputCoordinator`. Select an extraction boundary for selector/dispatch work and record physical counts for every changed production file.

6. `P2` - Preserving recursive v1-v3 fixtures needs an exact artifact action. Freeze the current default v3 bytes under a historical v3 filename and identify a durable v1 source before the default advances to v4.

Evidence inspected: `src/env.py:63-84`, `src/path_lifecycle.py:258-273`, `src/recursive_checkpoint.py:126-195,198-234,330-384`, `src/recursive_playtest.py:224-241,277-329`, `src/agent_play.py`, `scripts/playtest-verify.mjs:270-285`, current recursive fixtures, and the candidate iteration-6 plan.

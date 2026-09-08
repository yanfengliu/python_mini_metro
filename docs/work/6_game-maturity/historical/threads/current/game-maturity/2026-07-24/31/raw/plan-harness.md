# GM-10h plan review — harness lane

## VERDICT: REVISE

All ten load-bearing premises (schema v3 structure, the `within_tunnel_budget` trap + fix, the KeyError hazard, restore defaulting, checkpoint/RL invariance, state-legality, fleet stored-total soundness, the `{V2,V3}` gate) hold against live code. But the plan omits two existing contract-test files that hard-break under a v3 bump, and its `_require_running_config` snippet would KeyError on every v1/v2 load.

### Findings
1. **[MAJOR] Omitted `test/test_gm07b_save_schema.py`** — `:159` pins `SAVE_SCHEMA_VERSION == 2`, `:160` `SUPPORTED == {1,2}`, `:168` fresh doc `schemaVersion == 2`, `:221` `assertEqual(set(document), TOP_LEVEL_KEYS)` (lacks bonus keys), and `:183` the forward-version probe sets `schemaVersion=3` which becomes a NO-OP at v3 → `assertRaises` FAILS. Fix: add to scope; bump pins; add the keys; move the forward probe to 4.
2. **[MAJOR] Omitted `test/test_gm09f_save_map.py`** — `:64` `schemaVersion == 2` fails; `_as_v1` (`:46-52`) strips only the map keys, not the new bonus keys, so its "v1" doc carries them and `_exact_keys` rejects `test_a_v1_document_loads_as_classic`. Fix: repoint `:64`; strip the bonus keys in `_as_v1`.
3. **[MAJOR] `_require_running_config` snippet would KeyError on every v1/v2 load** — it runs for all versions after `_exact_keys` guarantees v1/v2 carry no bonus key, so a literal `document["numMetrosBonus"]` bricks loading. Fix: make the `.get(key, 0)` guard NON-optional (0-default = the old strict pin for v1/v2).
4. **[MINOR]** The determinism repoint is understated — restructure into v1→v3, v2→v3, and a NEW v3→v3 self-idempotence; repoint the worker; add v3 byte pins. v1/v2 byte pins stay frozen.
5. **[MINOR]** TDD test #4 must DESERIALIZE (not just validate) — the regression guard for the KeyError fix.
6. **[MINOR/info]** `tunnelBonus` widens the forged-save envelope (by design, matching the threat model) — record in D-045.
7. **[NIT]** "header-only upgrade" → "additive-keys upgrade".
8. **[NIT]** Use `getattr` in the `num_tunnels` property for defensive symmetry.

Bottom line: fold the three MAJORs (two omitted contract-test files + the `.get` guard) and the plan is implementable and safe. The core migration design is correct against live code.

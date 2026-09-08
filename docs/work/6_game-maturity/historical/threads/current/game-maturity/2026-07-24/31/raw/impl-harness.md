# GM-10h impl review — harness lane 1 (with real mutation testing)

## VERDICT: SHIP

GM-10h is correct on every load-bearing invariant. Ran real mutation testing in an ISOLATED copy: all five load-bearing mutations (drop the serialize guard, drop the `within_tunnel_budget` bonus, v3 pin `== config`, drop the reachability reject, and the map-identity gate) are caught by a test that turns red. Full suite 1566, targeted 58, ruff check + format all green.

### Claims confirmed (1-8)
1. **Serialize-time guard (BLOCKER-1) — CONFIRMED.** `_require_valid_upgrade_state` is the FIRST statement in `serialize_game` (`save_game.py:275`), before `_require_serializable_map` and before building the doc; `save_game` calls it before `mkstemp`/`os.replace`. The only save-doc disk writer is `save_game`. A desynced/forged state cannot reach the atomic write. Below-config check is uniquely load-bearing (`validate_save` only type-checks).
2. **`within_tunnel_budget` fix — CONFIRMED.** Folds `+ getattr(host, "tunnel_bonus", 0)` after the `None` early-return; the test proves the UNBLOCK (4 crossings rejected at budget 3, accepted at 3+2). All three gate sites pass the mediator as host.
3. **Version-gated pin — CONFIRMED.** No KeyError on v1/v2; `== config` for v1/v2, `>= config` for v3, `numPaths == config` always.
4. **v3 schema — CONFIRMED.** `_TOP_LEVEL_KEYS_V3`, `_validate_tunnel_bonus` (rejects bool/negative/float), map-identity gate `{V2,V3}`; v1/v2-with-bonus and v3-missing-bonus both rejected.
5. **Restore + reachability — CONFIRMED.** `.get("tunnelBonus", 0)`; `_require_legal_map_state` rejects a forged nonzero bonus on an unbounded map.
6. **Fixture + contract tests — CONFIRMED.** Independent byte-diff: `save-v3-classic.json` = v2 + one sorted `"tunnelBonus":0` + schemaVersion 3, LF-frozen, SHA matches the pin. v1/v2 byte pins untouched. Repoints are deliberate contract updates.
7. **No checkpoint/RL drift — CONFIRMED.** No recursive_checkpoint change; RL holds `num_metros == config`, `tunnel_bonus == 0`, no `tunnel` in the checkpoint.
8. **Test strength — STRONG** (M1-M4, M7 caught empirically).

### Findings
1. **[MINOR — test gap; code correct]** `_require_legal_map_state`'s consumed-vs-budget check correctly uses the bonus-aware `num_tunnels`, but no test pins the fold (the only bonus round-trip uses `consumed=0`). Low impact (path unreachable until GM-10g). Fix: add the load-path analogue of the unblock test.
2. **[NIT]** The `.get(...,0)` comment overstates the fail-open risk for this field (0 is the only falsy valid value, so `or 0` is behavior-identical here).
3. **[NIT]** README "may EXCEED it on a v3 save" understates `>= config`.
4. **[NIT — not a bug]** `_require_valid_upgrade_state` dereferences `map_definition.tunnel_budget` without a None-guard; unreachable (map_definition always defaults CLASSIC).

Nothing touched the working tree; mutation testing ran in a scratch copy.

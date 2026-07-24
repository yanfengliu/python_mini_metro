# GM-10h — review synthesis (D-045)

## Plan review — harness REVISE, Codex BLOCK → the design PIVOT

Both lanes verified the core migration design sound against live code (the additive-v3 shape mirroring GM-09f, the `within_tunnel_budget` trap, the version-gated pin, restore defaulting, checkpoint/RL invariance). The two-lane review earned its keep decisively — Codex went far deeper (2 BLOCKER + 5 MAJOR) and drove a SIMPLER design.

- Harness (`raw/plan-harness.md`, **REVISE**): 3 MAJOR — two omitted contract-test files (`test_gm07b_save_schema`, `test_gm09f_save_map`) that hard-break under v3, and the `_require_running_config` snippet KeyErroring on v1/v2 — plus minors.
- Codex ultra (`raw/plan-codex.md`, **BLOCK**): 2 BLOCKER + 5 MAJOR. BLOCKER-1: `serialize_game` would accept a desynced total/bonus and ATOMICALLY clobber a valid autosave with an unloadable one (load-time rejection is too late). BLOCKER-2: "no checkpoint change" vs the tunnel checkpoint/replay boundary. MAJOR-3: a `num_carriages_bonus` field would sit OUTSIDE the carriage-rollback contract. MAJOR-4: the plan silently dropped D-041's mid-offer persistence obligation. MAJOR-5/6/7/8: the validator's reachability, the omitted tests, the doc scope, the content fingerprint.

**Load-bearing decision — the PIVOT (three bonus fields → relax-pin + one `tunnelBonus`).** BLOCKERs 1 + 3 both pointed to a simpler design Codex itself suggested ("derive fleet bonuses from the stored totals"): DROP the fleet bonus field and just v3-relax the pin (`>= config`). That dissolved the serialize-clobber desync, the rollback-contract gap, and the v1/v2 KeyError, and collapsed v3 to ONE key. BLOCKER-2 → scope GM-10h to save/Continue + document the tunnel bonus never reaches the RL/replay path. MAJOR-4 → re-home mid-offer persistence to GM-10i. MAJOR-5 → reject a nonzero tunnel bonus on unbounded maps + document the forged-total threat model. All folded into PLAN v3. The serialize-time guard (`_require_valid_upgrade_state`, run before the atomic write) is the BLOCKER-1 fix.

## Implementation review — harness lane 1 SHIP, harness lane 2 SHIP; Codex DECLINED (compensated)

Codex's impl lane hit its **cybersecurity-risk filter** on the adversarial persistence-review framing (a documented failure mode; `raw/impl-codex.md`) — NOT a code finding. Per the fleet rule, a safety decline is NOT worked around by reframing to bypass the filter; it was COMPENSATED by a SECOND independent harness lane (distinct byte-identity/determinism lens). BOTH harness lanes SHIP, independently.

- Lane 1 (`raw/impl-harness.md`, **SHIP**): confirmed all 8 axes with REAL mutation testing in an isolated copy — the five load-bearing mutations (drop the serialize guard, drop the `within_tunnel_budget` bonus, v3 pin `== config`, drop the reachability reject, break the map gate) each turn a test red. 1 MINOR (load-legality bonus-fold under-tested) + 3 NITs.
- Lane 2 (`raw/impl-harness-2.md`, **SHIP**): independently reconstructed byte-identity (three ways), backward-compat, the serialize-before-write ordering, the `within_tunnel_budget` fold (with a REAL committed crossing line), the version-gated pin math (all 7 cases), and determinism-suite invariance (56 checks + 127 determinism tests). Same MINOR (load-legality) + the unreachable None-deref.

## Folds — landed (both lanes' findings)
- **Load-legality bonus-fold** (both lanes' MINOR): `test_load_legality_uses_the_bonus_aware_budget` pins that `_require_legal_map_state` compares `consumed_tunnels` against the BONUS-AWARE `num_tunnels` (a synthetic host with consumed in `(budget, budget+bonus]` — mutation-verified: a raw-budget mutant wrongly rejects it). The full committed-crossing round-trip lands with the TUNNEL effect in GM-10g (D-045).
- **Comment softening** (NIT): the `.get("tunnelBonus", 0)` comment no longer overstates the risk for this field.
- **README wording** (NIT): "may meet or exceed" (a fresh v3 save equals config).
- **`_require_valid_upgrade_state` None-deref** (both lanes): NO fix — unreachable (`map_definition` always defaults CLASSIC); both lanes concur.

## Result
Both plan lanes drove the pivot; both impl lanes independently SHIP (Codex declined, compensated per protocol). All findings folded or consensus-no-fix. Full `py313` suite green (1567 tests); ruff + pre-commit clean; v1/v2 fixtures byte-frozen, the new `save-v3-classic.json` pinned. Ready to deliver [GM-10h:A] → CI → [GM-10h:B]; GM-10e (a trivial `num_metros += 1` arm) opens next.

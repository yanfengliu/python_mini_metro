# GM-10h impl review — harness lane 2 (compensating for the Codex decline)

Independent second pass with a determinism / byte-identity / backward-compat lens,
reconstructing every load-bearing invariant from scratch (distinct from lane 1).

## VERDICT: SHIP (concurs with lane 1)

56 independent in-process checks pass, plus the full 1567-test suite (OK), 127
determinism/checkpoint/roundtrip/manifest tests (OK), and ruff check + format
(clean). Nothing in the working tree was modified/staged/reverted.

### Byte-identity claim: CONFIRMED (three ways)
- `save-v1.json`/`save-v2-classic.json` are UNTOUCHED by the diff.
- `save-v3-classic.json` = `save-v2-classic.json` + a single sorted-inserted
  `"tunnelBonus":0` + schemaVersion 2→3, nothing else — proved by (a) reconstructing
  the bytes, (b) an exact key-set delta, (c) a +16-byte length delta (15485→15501).
  Sorted insert lands correctly (`travelPlans` < `tunnelBonus` < `unlockedNumPaths`).
- LF-only, 15501 bytes, SHA `50d7d2c4…6400df` matches the pin; the STAGED git blob has
  0 CR bytes; no `.gitattributes` rule pins `fixtures/*.json eol=lf` (trap avoided).
- Idempotence: serialize→deserialize round-trips are byte-identical across 8 seeds × 4
  maps; `load(v1)`/`load(v2)`/`load(v3)` all re-serialize to the identical frozen v3 bytes.

### Backward-compat claim: CONFIRMED
- Real v1 + real v2 docs both deserialize cleanly with `tunnel_bonus == 0` and
  `num_metros/num_carriages == config`; `_require_running_config` does NOT KeyError; the
  v1/v2 fleet pin stays strict `== config`, only v3 relaxes to `>= config`.

### The 7 points — all CONFIRMED
Serialize-before-write ordering (the only save-doc writer is `save_game`, guard runs
first); the `within_tunnel_budget` fold (reconstructed WITH a real committed crossing
line on a tight-budget river — legality flips exactly at the bonus); the version-gated
pin math (all 7 enumerated cases correct); determinism suites unmoved (the RL content
fingerprint is a live `src/**` hash, so src edits are expected inputs with no frozen
literal to break; the checkpoint carries no tunnel/bonus key); and a second adversarial
pass — a grown-fleet v3 save (`num_metros=99`) passes ALL downstream load checks and
`available_locomotives`/`available_carriages` stay sane with grown totals.

### Minor observations (none blocking)
1. **[MINOR — test gap, not a code bug]** The over-base-budget → within-folded-budget
   LOAD-legality case is not pinned (the code is correct; reconstructed the flip with a
   real crossing line). [Folded post-review as `test_load_legality_uses_the_bonus_aware_budget`.]
2. **[MINOR — unreachable]** `_require_valid_upgrade_state` reads `map_definition.tunnel_budget`
   directly rather than via getattr; unreachable for a real Mediator (defaults CLASSIC).
3. **[INFO]** Commit by explicit pathspec covering all scoped files (partially staged).

The byte-identity and backward-compat invariants are genuine and hold.

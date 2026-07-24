# GM-10h plan v3 — fleet/tunnel upgrade persistence (save/Continue) (D-045)

## Scope (minimal coherent unit)
The SAVE/CONTINUE persistence that lets a weekly-offer upgrade growing the fleet or tunnel budget
survive save/load — the prerequisite the still-stub GM-10e/f/g effects need. Tested with
DIRECTLY-SET grown state (no effect writes one yet).

**In scope:** additive save-schema **v3** (a single new `tunnelBonus` key); the version-gated
`_require_running_config` relaxation (fleet totals `>= config` on v3); a stored `tunnel_bonus` folded
into `num_tunnels`; the `within_tunnel_budget` fix; a SERIALIZE-TIME invariant guard; serialize/restore;
a new `save-v3-classic.json` fixture; the three affected schema/map/determinism contract tests; the
full doc reconciliation.

**Explicitly OUT (reconciled below, NOT silently dropped):**
- The LOCOMOTIVE/CARRIAGE/TUNNEL apply-arm EFFECTS (still `pass` stubs) → **GM-10e/f/g**.
- **Mid-offer persistence** (persisting a PENDING offer set so a mid-offer save/Continue re-presents
  it) — a DIFFERENT mechanism (pending pause reason + the offer tuple), NOT the applied-bonus
  persistence. Saving mid-offer is currently BLOCKED (`_require_quiescent`) and window-close resolves
  with no choice. Re-homed to a named followup **GM-10i**; reconcile the `main.py`/`save_game.py`
  comments + D-041 that currently say "GM-10h" (review Codex MAJOR-4).
- Nonzero-tunnel-bonus CHECKPOINT/REPLAY representation → not needed: the checkpoint drops the tunnels
  block and the RL/replay path never applies an offer (bonus always 0 there), so there is nothing to
  reconcile; documented, no checkpoint change (review Codex BLOCKER-2).

## Design PIVOT (v1/v2 three-bonus-fields → v3 relax-pin + one tunnelBonus)
Dual plan review: harness REVISE (omitted tests + the `.get` guard), Codex BLOCK (2 BLOCKER + 5 MAJOR).
Codex BLOCKER-1 (`serialize_game` accepts a desynced total/bonus and atomically CLOBBERS a valid
autosave with an unloadable one — load-time rejection is too late) + BLOCKER-3/MAJOR-3 (a
`num_carriages_bonus` field sits OUTSIDE the carriage-rollback contract → desync) both point to a
SIMPLER design, which Codex suggested ("derive fleet bonuses from the stored totals"):
- **Fleet: NO bonus field.** `num_metros`/`num_carriages` are ALREADY stored totals (the authoritative
  state; grown by GM-10e/f). Just RELAX the load pin, version-gated: v1/v2 keep `== config`; **v3 allows
  `>= config`**. No new field → no total/bonus desync, no rollback-contract gap, GM-10e/f are a 1-line
  `+= 1`. (Empirically: `num_metros` starts at config and only grows; a `< config` total is a forge.)
- **Tunnel: one persisted `tunnelBonus`** (v3 key) — the tunnel has NO stored total (`num_tunnels`
  derives from the map constant), so a bonus is the only way. `num_tunnels = None if budget is None
  else budget + tunnel_bonus`.

## Empirically proven premises
1. Blocker real: `num_metros=5`/`num_carriages=3` serialize but fail load (`_require_running_config`
   `== config`). 2. `tunnelBonus` on CLASSIC is INERT: `num_tunnels` stays `None` (derivation
   early-returns on `budget is None`) → reject nonzero `tunnelBonus` on unbounded maps as unreachable
   (Codex MAJOR-5). 3. RIVER budget is a real int (3) → `budget + bonus` meaningful. 4. Blast radius:
   17 tests + the carriage rollback assign `num_metros`/`num_carriages`, so they MUST stay stored
   settable totals (relax-the-pin fits this; a derived property would not).

## Design (per file)

### Serialize-time invariant — the BLOCKER-1 fix — `src/save_game.py`
- Add `_require_valid_upgrade_state(mediator)` run in `serialize_game` BEFORE the atomic write AND
  before `_require_serializable_map` (map legality calls the now-bonus-aware `num_tunnels`): asserts
  `num_metros >= config.num_metros`, `num_carriages >= config.num_carriages`, `tunnel_bonus` is a
  nonnegative int, and `tunnel_bonus == 0` when `map_definition.tunnel_budget is None` (CLASSIC — a
  nonzero tunnel bonus is unreachable). Named errors. So a desynced/forged in-memory state is REJECTED
  before it can clobber the autosave (`save_game.py:299-316`) — load-time rejection alone is
  insufficient (Codex BLOCKER-1). The TEST must drive `serialize_game`/`save_game` and assert the
  reject, not only the loader.

### Fleet pin relaxation (version-gated) — `src/save_load.py:44-55`
- `_require_running_config` gains the doc's version (or is called with it): keep `numPaths == config`
  for all; metros/carriages `== config` for v1/v2, **`>= config` for v3**. Clear named message
  ("numMetros below the running config" / "disagrees with the running config"). Reading the version:
  `deserialize_game` already read it; thread it in or re-read `document["schemaVersion"]` (present +
  validated). No `document["numMetrosBonus"]` — there is NO such key (Codex BLOCKER-1/harness MAJOR-3
  KeyError hazard DISSOLVES with the no-fleet-field design).

### Tunnel — `src/mediator.py` + `src/crossings.py`
- ADD `self.tunnel_bonus = 0` (`__init__`). Rewrite `num_tunnels` (`:269-278`): `budget = self.
  map_definition.tunnel_budget; return None if budget is None else budget + getattr(self,
  "tunnel_bonus", 0)` (getattr for the defensive symmetry NIT). Fixes `available_tunnels`, the env
  `tunnels` observation, and `_require_legal_map_state` for free.
- **LOAD-BEARING TRAP (both lanes): `within_tunnel_budget` (`crossings.py:120-121`) reads
  `map_definition.tunnel_budget` DIRECTLY** — add `+ getattr(host, "tunnel_bonus", 0)` AFTER the
  `None` early-return (`:122`). Covers all 3 gate sites (`path_lifecycle.py:479,516`,
  `path_replacement.py:448`). Regression: a bonus UNBLOCKS a real over-budget crossing, not just the count.

### Save schema v3 (additive, ONE key) — `src/save_schema.py`
- `SAVE_SCHEMA_VERSION_V3 = 3`; `SAVE_SCHEMA_VERSION = V3`; add V3 to `SUPPORTED_...`. Contract/rules
  STABLE.
- `_TUNNEL_BONUS_KEY = frozenset({"tunnelBonus"})`; `_TOP_LEVEL_KEYS_V3 = _TOP_LEVEL_KEYS_V2 |
  _TUNNEL_BONUS_KEY`; extend `_top_level_keys_for`.
- `_validate_tunnel_bonus(document)`: one `_nonnegative_int` (rejects bool + negative — `_int` uses
  `type(value) is not int`), gated `if version == V3`.
- **map-identity gate `:279` → `if version in {V2, V3}:`** (v3 ⊇ map keys — both lanes; the ONLY other
  `== V2` is `_top_level_keys_for`, already extended).

### Serialize / restore — `src/save_game.py`, `src/save_load.py`
- Serialize: add `"tunnelBonus": getattr(mediator, "tunnel_bonus", 0)`. (Fleet totals already
  serialized as-is.)
- `_restore_scalars` (`:104-131`): `mediator.tunnel_bonus = document.get("tunnelBonus", 0)` — **default
  on ABSENCE, never `x or 0`** (GM-09f fail-open lesson: 0 is falsy). Restored before path restore +
  `_require_legal_map_state` (`:346`→`:350`→`:360`), so legality uses the effective budget.

### Contract tests the migration MUST touch (review MAJOR-6, both lanes)
- **`test/test_gm07b_save_schema.py`**: version pins (`:159`→3, `:160`→{1,2,3}), fresh-doc
  `schemaVersion` (`:168`→3); add `tunnelBonus` to `TOP_LEVEL_KEYS` (`:26-35`) so the exact-set assert
  (`:221`) holds; MOVE the forward-version probe (`:183` `schemaVersion=3`) to **4** (3 is now current
  → setting it is a no-op → `assertRaises` would FAIL). Add exact v1/v2/v3 builders + genuine finite-map
  v2 coverage (Codex MAJOR-6).
- **`test/test_gm09f_save_map.py`**: `:64`→3 (all four maps); extend `_as_v1` (`:46-52`) to `del`/pop
  `tunnelBonus` too (else a v1 doc carries it → `_exact_keys` rejects `test_a_v1_document_loads_as_classic`).
- **`test/test_gm07b_save_determinism.py`**: keep v1/v2 byte pins (`:53-61`) + frozen-fixture asserts
  (`:341-366`); restructure "re-save == latest" into v1→v3, v2→v3, and a NEW v3→v3 idempotence; repoint
  the worker (`:281-284` `FIXTURE_V2_PATH`→`FIXTURE_V3_PATH`); add v3 byte pins.

### Fixture
- v1/v2 stay BYTE-FROZEN. Add frozen `scripts/fixtures/save-v3-classic.json` (the deterministic
  ADDITIVE-KEY v2→v3 upgrade: adds `tunnelBonus: 0`).

### Docs (review MAJOR-7 — full reconciliation, same unit)
- `README.md:217-233` (schema v2 → v3, running-config equality → v3 `>= config` for fleet + persisted
  tunnel bonus, `{1,2}`→`{1,2,3}`, the v3 latest fixture). `src/save_game.py:30-42` + `src/save_load.py:
  305-311,332-333` module docstrings (v2→v3, accepts v1/v2/v3). `ARCHITECTURE.md`, `PROGRESS.md`. The
  nested `DECISIONS.md` D-045 (records: additive v3, the relax-pin-not-field fleet choice, the
  `within_tunnel_budget` fix, the serialize-time guard, the forged-total threat model, the mid-offer
  split to GM-10i, the checkpoint-inertness). Reconcile `main.py:327-337` + `save_game.py:76-84` +
  D-041 (mid-offer "GM-10h" → GM-10i). STATE/EVIDENCE at :B.
- **Content fingerprint (Codex MINOR-8)**: editing mediator/crossings/save rotates the LIVE RL content
  fingerprint (expected; `EXPECTED_LF_TRAINING` pins only training sources) — distinct from the
  zero-bonus observation/checkpoint BYTE stability. Note it, no repin.

### No change: recursive checkpoint/schema (BLOCKER-2 — scoped out + documented), env observation
(reflects the mediator; RL path 0).

## TDD tests (`test/test_gm10h_persistence.py`)
1. **Fleet grow round-trip**: `num_metros=5, num_carriages=3` directly → `serialize_game`
   (does NOT raise; v3) → `deserialize_game` (runs the relaxed pin) → both survive.
2. **Serialize-time reject (BLOCKER-1)**: `num_metros = config-1` (below config) → `serialize_game`
   RAISES the named error (before any write); likewise a nonzero `tunnel_bonus` on CLASSIC raises.
3. **Tunnel round-trip + UNBLOCKS a crossing (the trap)**: RIVER, `tunnel_bonus=2` → `num_tunnels==5`;
   round-trips; AND a route needing 4-5 crossings (rejected at budget 3) is ACCEPTED with the bonus —
   drive `within_tunnel_budget`/the real route-edit path, not just the count.
4. **v1/v2 load-as-0 via DESERIALIZE (review MINOR-5)**: `deserialize_game(save-v1/v2)` (runs
   `_require_running_config`) succeeds, `tunnel_bonus==0`; re-serialize → the v3 fixture bytes; a v1/v2
   doc carrying `tunnelBonus` is REJECTED (`_exact_keys`); a v3 doc missing `tunnelBonus` is rejected.
5. **v3 validator**: negative / bool / non-int `tunnelBonus` rejected (named); the map-identity gate
   still fires on a v3 doc (forged `mapId` rejected).
6. **RL/headless unchanged**: `MiniMetroEnv`/`PlayerPixelEnv` past a boundary → `num_metros==config`,
   `tunnel_bonus==0`; the env `fleet`/`tunnels` blocks + a recursive checkpoint byte-identical to
   pre-GM-10h (import + run the GM-09a/checkpoint determinism locks).
7. **State-legality bites**: a forged v3 save with `consumed_tunnels > budget + tunnel_bonus` rejected.
8. **Forged-total accepted (threat-model doc)**: `num_metros=99` v3 loads (like a forged `deliveries`)
   — pins the DECISION that fleet totals are authoritative editable state.

## Risks / review foci (HIGH-RISK persistence migration, D-026 → multi-cli-review escalation)
- **BLOCKER-1**: serialize MUST reject before the atomic write (autosave clobber). Test via serialize.
- **The `within_tunnel_budget` trap**: test the UNBLOCK, not the count.
- **The `{V2, V3}` map gate** + the forward-version-probe move to 4.
- **`.get("tunnelBonus", 0)`** not `or 0`.
- **No checkpoint/RL drift** (bonus 0 off the human path) + the content-fingerprint rotation documented.
- **Mid-offer split** reconciled in docs, not silently dropped.
- No dep change; no lockfile re-resolve.

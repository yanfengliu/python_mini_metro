===BEGIN-REVIEW===

Verdict: BLOCK

1. [BLOCKER] The plan does not make its claimed save-time fleet invariant enforceable.

   `serialize_game` currently performs map/quiescence/fleet-ownership checks, writes the mutable totals, and runs only structural schema validation (`src/save_game.py:237-296`). That validation checks merely that `numMetros` and `numCarriages` are nonnegative integers (`src/save_schema.py:128-142`). Configuration agreement is checked only during loading (`src/save_load.py:44-54,332-340`).

   A live probe confirmed that `num_metros = 5` serializes successfully but its own document then fails to deserialize. Under the proposed v3, a mismatched total/bonus pair could therefore pass serialization and atomically replace a valid autosave at `src/save_game.py:299-316`, leaving Continue unable to load it. Test 3 explicitly permits this by accepting “serialize raises OR deserialize rejects.”

   Concrete fix: require exact nonnegative bonus types and both total/base/bonus equations during serialization as well as loading. The save test must require serialization—and `save_game` before replacement—to reject desynchronization; loader rejection alone is insufficient. Perform live bonus validation before `_require_serializable_map`, because map legality will call the bonus-aware `num_tunnels`.

2. [BLOCKER] “No checkpoint change” contradicts the stated checkpoint/replay delivery boundary for tunnel upgrades.

   Fleet totals are captured in checkpoint limits (`src/recursive_checkpoint.py:375-384`) and internally cross-checked (`src/recursive_checkpoint_schema.py:241-254,308-314`), so locomotive/carriage bonuses are behaviorally absorbed into their totals. Tunnel state is different: the environment exposes it at `src/env.py:231-238`, but checkpoint normalization retains only the fleet block and drops the tunnels sibling (`src/recursive_checkpoint.py:125-157`). The existing test explicitly confirms that omission (`test/test_gm09c_crossings.py:298-310`).

   Consequently, changing a tunnel bonus changes route legality and the raw observation while leaving canonical checkpoint bytes unchanged. Test 6 only proves the zero-bonus RL path remains stable; it cannot prove nonzero tunnel persistence or replay reconciliation.

   Concrete fix: either narrow GM-10h and its canonical documentation to save/Continue persistence, explicitly deferring nonzero tunnel checkpoint/replay representation, or add a new checkpoint version containing effective tunnel/bonus state. If versioned, preserve recursive v5→checkpoint v4 and add a new recursive schema mapping; the historical mapping is fixed at `src/recursive_playtest.py:292-300`.

3. [MAJOR] The proposed duplicate mutable fleet counters are outside the existing rollback contracts.

   Carriage transactions capture, compare, and restore `num_carriages` but no corresponding bonus (`src/carriage_transaction_snapshot.py:41-44,151-160,302-308`). Path replacement does the same (`src/path_replacement_snapshot.py:93-107,188-214`). A live probe changing only a synthetic `num_carriages_bonus` showed `transaction_state_matches` still returned true and restoration left the mutation intact.

   A later save/load pin can reject that leaked state, but it cannot restore exact rollback behavior. Normal rollback with an unchanged bonus is sound; the hazard arises through the effectful factories/reconcilers these snapshots are specifically designed to police.

   Concrete fix: either derive persisted fleet bonuses from the stored totals, avoiding duplicate mutable runtime state, or extend every relevant capture/compare/restore contract to cover the paired bonus fields. Add a failure-path regression proving rollback restores both values.

4. [MAJOR] The plan silently drops GM-10h’s existing mid-offer persistence obligation.

   Saving while an offer is pending is explicitly rejected and documented as deferred to GM-10h (`src/save_game.py:76-84`). Closing during the offer currently resolves with no choice and saves past the boundary, with “mid-offer persistence proper” assigned to GM-10h (`src/main.py:327-337`). D-041 makes the same assignment (`docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:257-259`).

   This plan leaves that behavior unchanged without redefining the roadmap boundary.

   Concrete fix: either include pending week state and ordered-offer restoration in GM-10h, or split it into a named later unit and reconcile the source comments, decision record, and roadmap before claiming GM-10h complete.

5. [MAJOR] The proposed validator proves arithmetic consistency, not upgrade provenance or gameplay reachability.

   A large `tunnelBonus` raises the effective limit used by `_require_legal_map_state` (`src/save_load.py:324-329`), so a forged document can make arbitrarily many crossings appear legal. A positive tunnel bonus on Classic is also unreachable and dead state: Classic excludes TUNNEL from its pool (`src/offers.py:53-67`), while the proposed `num_tunnels` correctly remains `None`.

   More generally, exactly one offer can be applied per resolved boundary (`src/weekly_offers.py:52-70`), and completed weeks are derivable from persisted steps (`src/mediator.py:699-703`). Three independent nonnegative counters do not enforce that history.

   Concrete fix: define the contract explicitly. If bonuses are authoritative editable state, stop describing them as provenance and acknowledge that matched forged bonuses are accepted. If v3 promises reachable-state validation, reject nonzero tunnel bonuses on unbounded maps and constrain aggregate bonuses against schema-pinned resolved-week history—or persist an applied-upgrade ledger.

6. [MAJOR] Existing migration tests omitted by the plan will fail or cease testing genuine historical documents.

   The schema suite pins current version 2, supported `{1,2}`, forward version 3, and the exact v2 key set (`test/test_gm07b_save_schema.py:25-35,153-190,217-228`). The map suite constructs “v1” by removing only v2 map keys (`test/test_gm09f_save_map.py:46-52`) and obtains its v2 cases directly from the current serializer (`test/test_gm09f_save_map.py:55-68,98-102`). Once serialization emits v3 bonuses, those are no longer genuine v1/v2 documents and some rejection tests can pass for the wrong extra-key reason.

   Concrete fix: add exact v1, v2, and v3 document builders; move the forward-version test to 4; retain genuine finite-map v2 coverage; and test v1→v3, v2→v3, and v3→v3 byte idempotence.

7. [MAJOR] The documentation scope is incomplete for a public schema migration.

   README still promises schema v2, exact running-config equality, `{1,2}` support, the v2 latest fixture, and no persisted tunnel state (`README.md:217-233`). Source documentation also says serialization is v2 and deserialization accepts only v1/v2 (`src/save_game.py:30-42,237-239`; `src/save_load.py:305-311,332-333`). The live roadmap requires checkpoint/replay reconciliation (`docs/threads/current/game-maturity/2026-07-11/1/STATE.md:25`).

   Concrete fix: D-045 alone is insufficient. Include README, affected module documentation, ARCHITECTURE, PROGRESS, and current STATE/EVIDENCE reconciliation in the same unit, accurately recording whichever checkpoint and mid-offer boundaries are chosen.

8. [MINOR] “No RL drift” is true only for observation/checkpoint values, not stored RL artifact compatibility.

   The content fingerprint hashes nearly every file under `src/` (`src/rl/training.py:296-323`). These mediator/crossing/save changes therefore rotate it, and strict resume/evaluation rejects older manifests unless content drift is explicitly allowed (`src/rl/manifest.py:231-242`).

   Concrete fix: distinguish zero-bonus observation/checkpoint byte stability from the expected content-fingerprint change, and validate/document the latter. This does not require repinning the separate training-source fingerprint.

Claims verified against live code:

- The additive v3 shape is correct. The two production v2-only branches are `_top_level_keys_for` and the map-identity gate (`src/save_schema.py:76-79,279-280`). V3 needs its own exact key set, and map validation must cover `{V2,V3}`. No other production `SAVE_SCHEMA_VERSION_V2` branch was found.
- The v1/v2 KeyError hazard is real. `validate_save` performs version selection and exact-key validation before `_require_running_config` (`src/save_schema.py:265-280`; `src/save_load.py:337-340`). Use zero bonuses for validated v1/v2 documents and direct required-key reads for v3. `document.get(key, 0)` in restoration is functionally correct after validation.
- The tunnel gate trap is real. Actual route admission reads `map_definition.tunnel_budget` directly (`src/crossings.py:103-133`); changing only `Mediator.num_tunnels` would be a half-fix. No other functional `src/` tunnel-budget reader bypasses the mediator. The base-`None` check must occur before adding `getattr(host, "tunnel_bonus", 0)`.
- Stored fleet totals are used throughout runtime behavior, and no additional production `config.num_metros`/`config.num_carriages` consumer was found beyond initialization/load agreement. The total/bonus split is viable only after findings 1 and 3 are resolved.
- V1 and v2 fixtures should remain byte-frozen. Their pins are at `test/test_gm07b_save_determinism.py:53-61`; existing “latest” comparisons target v2 at `:281-284,386-394`. A separately pinned v3 fixture is required.
- Restoring the tunnel bonus in `_restore_scalars` occurs before path restoration and final map legality (`src/save_load.py:349-360`), so the legality check will correctly use the effective budget once implemented.
- With calendar/offers unreachable on the RL path and bonuses initialized to zero, observation and checkpoint values remain unchanged. This does not resolve the nonzero checkpoint omission or content-fingerprint change.
- Classic remains unbounded and therefore continues excluding TUNNEL offers through `host.num_tunnels is not None` (`src/weekly_offers.py:45-49`).

===END-REVIEW===

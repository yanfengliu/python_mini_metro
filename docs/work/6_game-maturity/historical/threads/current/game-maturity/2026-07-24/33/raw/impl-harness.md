# GM-10i impl review — harness lane

Verdict: **SHIP** (with 2 MINOR test-strength gaps worth a follow-up test; neither is a code defect)

Evidence: full suite `1592 tests OK` in `py313`; `ruff check` + `ruff format --check` clean on all
12 changed files; all 5 frozen fixtures load correctly; all 7 checklist mutations independently
caught by a red test (verified in isolated `src` copies via `PYTHONPATH`, not just mentally).

## Confirmed (against live code)

1. **v4 version-gate matrix complete.** `_top_level_keys_for` v4 branch (`save_schema.py:124-131`);
   `_validate_map_identity` `(V2,V3,V4)` (`:375-380`); `_validate_tunnel_bonus` `(V3,V4)` (`:381`);
   `_require_running_config` grown-fleet pin `(V3,V4)` (`save_load.py:63-66`);
   `_pause_reason_vocabulary_for` "week" only v4 (`:81-84`); `_validate_pending_offers` `==V4`
   (`:384-385`). M1 (fleet pin → `(V3,)`) reds `test_a_grown_fleet_at_a_boundary_round_trips`; M3
   (vocab always v4) reds `test_week_pause_reason_rejected_for_v3`.
2. **Serialize integrity guard sound + non-bypassable.** `_require_valid_pending_offers` runs
   unconditionally before any write; same single derivation source as the hold. Read-only (no draws).
   M5 (drop the guard) reds `test_serialize_rejects_desynced_current_offers`.
3. **Load verbatim + fail-closed, correct order.** `_restore_pending_offers` maps via
   `describe(OfferKind(v))` verbatim, rejects TUNNEL-on-unbounded; called after rng/scalars/map +
   after `_require_legal_map_state`; no `WEEK_LENGTH_STEPS`/`OFFERS_PER_WEEK` coupling. Schema rejects
   week+isGameOver + week/offers inconsistency. M4/M6/M7 each red.
4. **Backward compat.** `SUPPORTED = {1,2,3,4}`; loaded all fixtures with live source; `save-v4-classic`
   is the exact deterministic v3→v4 re-save (15501→15520, the 19-byte sorted insert; SHA pinned,
   LF-clean); `_as_v1` strips all four superset keys; the forward-version mutation is now 5.
5. **RL/headless invariance** (calendar off → never pending → `pendingOffers` always `[]`; checkpoint
   schema untouched). 6. **Window-close persists without resolving** (`main.py:331-337`; end-to-end
   `test_a_loaded_pending_save_promotes_to_the_offer_modal`). 7. **Native-version tests still prove
   their claims** after the down-conversion edits.

## Findings

1. **[MINOR] `pendingOffers` pairwise-distinct guarantee has zero test coverage + no load backstop.**
   `save_schema.py:202-204` rejects a duplicate, but M9 (remove it) leaves the whole gm10i+gm07b+gm10h
   suite green, and `_restore_pending_offers` has no fallback (`OfferKind("new_line")` twice both
   succeed). Low impact (a forged save showing two identical buttons; `resolve`'s membership still
   works) but the schema's own documented invariant is unproven. Fix: a `["new_line","new_line"]`
   validate/deserialize reject test.
2. **[MINOR] `pendingOffers` "known kind" guarantee untested at the `validate_save` boundary.**
   `save_schema.py:200-201` rejects an unknown kind, but M8 (remove it) leaves the same suite green;
   `deserialize_game` has an incidental backstop (`OfferKind("bogus")` raises) but the public validator's
   guarantee would silently regress. Fix: a `validate_save`-level `["bogus_kind", ...]` reject test.

## Non-findings
- Forged `"week"` at non-boundary `steps` accepted BY DESIGN (offers stored verbatim, decoupled from
  the provisional GM-11 constants; within the D-045 forged-authoritative-state threat model; the
  serialize guard prevents any *legitimate* save reaching that state). Not a defect.
- Docs deferred to `:B` — consistent with the repo's `feat …[:A]` / `docs: finalize …[:B]` convention.
- `test_gm10i_pending.py:194` calls the river-pending fixture "byte-frozen" but only asserts load
  behavior (no SHA/length pin, unlike the classic determinism fixture) — wording overstates the guarantee.

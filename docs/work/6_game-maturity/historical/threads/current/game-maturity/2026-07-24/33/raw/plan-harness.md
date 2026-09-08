# GM-10i PLAN review — harness lane

Verdict: **REVISE**

The core design is sound and its load-bearing claim was verified empirically (re-derivation
is exact because the RNG is frozen at a held boundary). One BLOCKER (the v4 fleet-pin gate
silently breaks the feature's own target scenario) plus several MAJOR gaps where the plan's
"v4 = v3 unchanged" premise is false against the code. All fixable without redesign.
(NOTE: this lane reviewed the ORIGINAL re-derive plan; the Codex lane's cross-version
BLOCKER later drove the pivot to persist-the-offers, which subsumes several items below.)

## Findings

1. **[BLOCKER] The v3 fleet-pin relaxation does NOT extend to v4 — a grown fleet at a
   boundary fails to load.** `save_load.py:55` gates on `== SAVE_SCHEMA_VERSION_V3`; a v4
   doc takes the legacy exact-equality branch and requires `numMetros`/`numCarriages ==
   config`. Realistic target: week-1 pick LOCOMOTIVE (`num_metros = config+1`), week-2 mid-
   offer save (v4, `numMetros=5`, `pauseReasons=["week"]`) → Continue fails
   ("numMetros disagrees with the running config"). This is exactly the case GM-10i exists
   for. The plan's TDD all starts FRESH (fleet at config), so every listed test passes while
   the real bug ships. Fix: gate on membership `in (V3, V4)` (or `>= V3`). Add a v4-boundary-
   with-grown-fleet round-trip test.
2. **[MAJOR] Map-identity + tunnelBonus validators don't run for v4** (`save_schema.py:309`
   `(V2,V3)`, `:311` `==V3`). Reusing `_TOP_LEVEL_KEYS_V3` for v4 makes those keys required
   but their VALUES unvalidated on v4. Fix: extend both gates to include v4.
3. **[MAJOR] `_top_level_keys_for` has no v4 branch → v4 falls through to the v1 key set**
   (`save_schema.py:93-98`), so `_exact_keys` rejects every v4 save. Fix: add the v4 branch.
4. **[MAJOR] Pause-vocab version-gate not threaded** — `_validate_scalars` uses the module
   constant unconditionally and has no `version` param (`save_schema.py:62/172/313`). Fix:
   thread `version` in and select the vocabulary.
5. **[MAJOR] Test-repoint blast radius under-counted (only 3 files listed).** Missing:
   `test_gm10h_persistence.py:124` (schemaVersion 3); `test_gm07b_save_schema.py:159-161/169`
   and CRITICALLY `:186` (`forward schemaVersion` mutation `4` becomes SUPPORTED → its
   `assertRaises` fails; repoint to 5); `test_gm09f_save_map.py:67`. Fix: enumerate every pin.
6. **[MAJOR] Determinism chain needs a separate `save-v4-classic.json` upgrade fixture** the
   plan doesn't name (`test_gm07b_save_determinism.py:295/413-419` pin the re-save of v1/v2/v3
   classic to the current-version bytes). The plan named only a river-boundary fixture.
7. **[MINOR] Re-derivation duplicates the hold's offer generation** — extract one
   `WeeklyOffers.derive_current_offers(host)` used by both. `save_load` also needs new imports.
8. **[MINOR] Stale `deserialize_game` docstring** ("v1 or v2 save document").

## Confirmed
- Offers are a pure function of frozen persisted state WITHIN A BUILD (probe-verified: while
  pending, `is_paused` blocks `increment_time`, so no draw occurs between generation and save;
  python rng + steps→week_index + map→num_tunnels all round-trip; speed-4 at steps=1202 →
  week_index 1 both times). (Codex later showed this is NOT stable ACROSS builds → the pivot.)
- Deserialize ordering achievable (re-derive after `_restore_scalars`); nothing else about the
  boundary is lost (`build_from` re-enables `week_calendar`; per-frame `reconcile_week_boundary`
  promotes to OFFER guarding `is_game_over is not True`); save-block removal scoping holds;
  dropping the window-close force-resolve is safe; RL/headless unaffected.

## Open-question answers
1. Version-gate — correct AND required (but needs the threading of Finding 4).
2. No hard legality invariant needed; do NOT add a steps-near-boundary check (false-rejects
   1200/1202). An `is_week_boundary_pending`-consistency assertion is nice-to-have only.
3. Re-derive (now: restore) in DESERIALIZE, not at promotion — a loaded pending mediator must
   satisfy the same invariant for all consumers.

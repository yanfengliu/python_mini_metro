# GM-10i — review synthesis (D-047)

Mid-offer PENDING-offer persistence (save-schema v4): a mid-offer save persists the held
week boundary so a Continue reloads INTO the modal re-presenting the SAME offers. Offers are
STORED (a `pendingOffers` key), not re-derived on load.

## Plan review — harness REVISE, Codex ultra BLOCK → a design PIVOT

HIGH-RISK persistence migration → dual plan review (multi-cli escalation). Both lanes CONVERGED
on a version-gate BLOCKER; Codex caught a deeper one that drove the pivot.

- Harness (`raw/plan-harness.md`, **REVISE**): 1 BLOCKER — the v3 fleet-pin relaxation gates on
  `==V3`, so a v4 mid-offer save carrying a GROWN fleet (from an earlier locomotive/carriage
  upgrade) fails Continue; invisible to a fresh-start TDD. + 5 MAJOR (the other `==V3`/`(V2,V3)`
  gates, the pause-vocab threading, the under-counted test-repoint blast radius incl. the
  forward-mutation `4`→`5`, the second fixture) + 2 MINOR. Confirmed the flow integration holds.
- Codex ultra (`raw/plan-codex.md`, **BLOCK**): 2 BLOCKER + 3 MAJOR + 1 MINOR. BLOCKER-2 = the
  harness's fleet-pin BLOCKER. **BLOCKER-1 (the pivot driver):** re-deriving offers on load is exact
  only WITHIN a build — `WEEK_LENGTH_STEPS`/`OFFERS_PER_WEEK`/the pool are provisional-for-GM-11, so
  a v4 save re-derived after a balance change would re-present the WRONG offers, violating README
  "Continue resumes exactly".

**The PIVOT (re-derive → persist the shown kinds).** Both lanes pointed to storing the resolved
offer OUTPUT + validating `== canonical` at serialize. This is the REVERSE of GM-10b's pivot (which
dropped a persisted RNG STREAM): here we persist the resolved output, self-contained across a rules
change. The v4 capability matrix was made explicit (grown-fleet pin `in (V3,V4)`, map-identity
`(V2,V3,V4)`, tunnel `(V3,V4)`, pause-vocab week-only-v4, pending-offers `==V4`). We deliberately did
NOT add Codex's steps-reachability load check — it would recouple the loader to the provisional
`WEEK_LENGTH_STEPS`, reintroducing the fragility the pivot removes. All folded into PLAN v2 + the
implementation; empirically probed (a full serialize→deserialize at a river boundary re-presents the
exact offers).

## Implementation review — harness SHIP, Codex FIX-FIRST → matrix correct by BOTH; one design fold

Both lanes independently CONFIRMED the production v4 capability matrix complete + correct, and all 8
requested mutations (V3-only fleet gate, missing v4 key, week-in-v3, re-derive-on-load, dropped
serialize guard, dropped week+game-over reject, dropped tunnel-unbounded reject, forward-`5`) turn a
test red. The harness ran REAL mutation probes in isolated `src` copies.

- Harness (`raw/impl-harness.md`, **SHIP**): all 7 axes confirmed; 2 MINOR — the `pendingOffers`
  distinct-kind + known-kind guarantees are untested at the `validate_save` boundary (mutations M8/M9
  leave the suite green; the distinct check has no load backstop).
- Codex (`raw/impl-codex.md`, **FIX-FIRST**): confirmed the same matrix; 1 BLOCKER + 2 MAJOR + 2 MINOR.

**Codex BLOCKER-1 (re-save instability) — the design fold.** The pivot made LOAD cross-version safe
(verbatim restore), but the serialize-time guard still RE-DERIVED + demanded `== canonical` — so a v4
pending save made under old rules LOADS fine yet cannot be RE-SAVED once GM-11 retunes the derivation
(reproduced: `OFFERS_PER_WEEK` 2→1 → the fixture loads, re-save rejects; the mid-offer QUIT swallows
the failure). My own serialize guard reintroduced the exact provisional-constant coupling the pivot
exists to remove. **Fix:** make serialize LOAD-SYMMETRIC — drop `== canonical`, keep only what LOAD
rejects (element types + pool legality: a TUNNEL offer needs a bounded map), so serialize never writes
an unloadable save AND a loaded-under-old-rules pending state stays re-savable. The now-unused
`Mediator._derive_current_offers` seam was removed.

## Folds — landed (all findings)

- **[BLOCKER, Codex] re-save instability** → the serialize guard is now load-symmetric (drop
  `== canonical`; keep element-type + pool-legality checks with actionable errors). New tests: a
  pending state whose `current_offers` is NOT the live derivation still re-saves (would raise under
  `== canonical`); a TUNNEL-offer-on-CLASSIC serialize reject; malformed-offer actionable errors.
- **[MAJOR, Codex] weak version/validation matrix + unpinned river fixture** (overlaps harness MINORs)
  → added: unknown-kind + duplicate-kind `validate_save` rejects; a v1/v2-REJECT-a-grown-fleet test
  (the relaxation is v3/v4 only); a LF/length/SHA byte-pin for `save-v4-river-pending.json`.
- **[MAJOR, Codex] OFFER+QUIT test doesn't prove persistence** (the GM-10a fake uses `current_offers=()`
  which the real serializer rejects) → a new test drives the REAL autosave writer on a REAL pending
  mediator through a redirected `AUTOSAVE_PATH`, then loads the file and confirms the boundary + offers
  survived on disk.
- **[MINOR, Codex] malformed live offer state** → folded into the load-symmetric guard (named
  ValueError for a non-tuple / non-Offer element).
- **[MINOR, Codex] source docstrings contradict v4** → corrected `save_game` module + `serialize_game`
  docstrings (v3→v4), the `Mediator.current_offers` comment (was "transient/re-derived"), the
  `weekly_offers.resolve` docstring (the `None` path is no longer the window-close path), and README's
  schema section (added a v4 paragraph; grown fleets v3/v4).

## Result

Both plan lanes drove the pivot + the v4 gate matrix; both impl lanes confirmed the matrix correct,
and Codex's BLOCKER made serialize genuinely cross-version-consistent with load. All findings folded.
Full `py313` suite green (1599 tests); ruff + format + pre-commit clean; v1/v2/v3 fixtures byte-frozen,
the new `save-v4-classic.json` + `save-v4-river-pending.json` pinned. GM-10 is COMPLETE. Ready to
deliver [GM-10i:A] → CI → [GM-10i:B]; GM-11 (balance/recursive playtest) opens next toward v1.0.

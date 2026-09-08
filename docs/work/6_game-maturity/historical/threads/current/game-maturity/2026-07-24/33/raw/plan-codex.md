===BEGIN-REVIEW===

## Verdict: BLOCK

The same-build reconstruction path is sound, but the plan is not persistence-safe as written. Two blockers must be resolved before implementation.

## Findings

1. **[BLOCKER] Offers are not purely a function of persisted state across save-schema lifetime.**

   The RNG state and steps are persisted, but the derivation also depends on live, unpersisted rules:

   - `week_index` uses live `WEEK_LENGTH_STEPS`: [src/mediator.py:710](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:710).
   - Offer count uses live `OFFERS_PER_WEEK`: [src/weekly_offers.py:45](/C:/Users/38909/Documents/github/python_mini_metro/src/weekly_offers.py:45).
   - Pool ordering, labels, and sampling are live code: [src/offers.py:53](/C:/Users/38909/Documents/github/python_mini_metro/src/offers.py:53), [src/offers.py:70](/C:/Users/38909/Documents/github/python_mini_metro/src/offers.py:70).
   - Both constants are explicitly provisional for GM-11: [src/config.py:88](/C:/Users/38909/Documents/github/python_mini_metro/src/config.py:88), [src/config.py:95](/C:/Users/38909/Documents/github/python_mini_metro/src/config.py:95).
   - Exact sequences are coupled to CPython 3.13’s `random.sample`: [test/test_gm10b_offers.py:45](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10b_offers.py:45).

   Merely bumping future writes to v5 would not help: a future loader would still accept v4 and re-derive it using changed constants/code. A v4 save at `steps=1202` could derive a different week or offer count after GM-11.

   **Fix:** either persist the ordered offer kinds in v4, validating them against the canonical derivation at write time, or introduce a frozen schema-version-dispatched derivation that preserves v4’s week length, count, pool order, labels, and sampling algorithm indefinitely. Add a test proving v4 reconstruction remains unchanged when current rules differ.

2. **[BLOCKER] “v4 inherits v3” must explicitly cover every version branch, especially grown fleets.**

   The plan states this intention, but the live gates do not inherit features automatically:

   - `_require_running_config` relaxes fleet totals only when `schemaVersion == V3`; v4 would take the legacy exact-equality branch: [src/save_load.py:44](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:44), [src/save_load.py:55](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:55).
   - Unhandled versions fall back to the v1 top-level key set: [src/save_schema.py:93](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:93).
   - Map validation names only v2/v3, and tunnel validation only v3: [src/save_schema.py:303](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:303).

   Consequently, a legitimate pending v4 save after an earlier locomotive or carriage upgrade would fail Continue.

   **Fix:** make the capability matrix explicit:

   - Exact keys: v1; v2; v3/v4.
   - Map identity: v2/v3/v4.
   - Tunnel bonus: v3/v4.
   - Grown fleet: v3/v4.
   - Pause vocabulary: v1–v3 exclude `week`; v4 includes it.

   Use explicit membership sets, not `>=`, and test a v4 pending bounded-map save with grown metro/carriage totals and nonzero tunnel bonus.

3. **[MAJOR] The plan needs pending-state reachability and canonical-offer validation.**

   A genuine hold is created only immediately after a crossing, only when not game-over, and only after offers have been generated: [src/weekly_offers.py:30](/C:/Users/38909/Documents/github/python_mini_metro/src/weekly_offers.py:30). Resolution applies, clears, and releases in a defined order: [src/weekly_offers.py:52](/C:/Users/38909/Documents/github/python_mini_metro/src/weekly_offers.py:52).

   Once the week save block is removed, serialization records `pauseReasons` but not `current_offers`: [src/save_game.py:279](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:279). A mediator with `week` plus empty, reordered, or stale offers would therefore save successfully and reload with different buttons. A forged v4 document could also add `week` at step 0 and receive an otherwise unreachable free upgrade, contradicting the plan’s “no forgery gain” claim.

   **Fix:**

   - At serialization, require pending `current_offers` to equal the version-specific canonical derivation; require it to be empty when not pending.
   - At validation/load, reject `week` with `isGameOver=true`.
   - For frozen v4 rules, require `steps >= 1200` and `steps % 1200 < 4`. Do not use the saved current speed: speed can change while the hold remains, as tested at [test/test_gm10a_calendar.py:108](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:108).
   - Centralize this logic in `WeeklyOffers`; do not duplicate the formula in `save_load`.

4. **[MAJOR] The fixture plan requires two distinct v4 fixtures.**

   Existing upgrade tests require v1, v2, and v3 Classic saves to re-save to one same-state current-version Classic fixture: [test/test_gm07b_save_determinism.py:408](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:408). A pending River save cannot be that target.

   **Fix:** define both:

   - `save-v4-classic.json` for v1/v2/v3→v4, v4 idempotence, and cross-process canonical-byte tests.
   - `save-v4-river-pending.json` for the new `week` capability and exact offer reconstruction.

5. **[MAJOR] Current-version tests will silently stop exercising native v3 behavior after the bump.**

   Several tests build documents through `serialize_game`; after the bump those become v4-only, including grown-fleet and tunnel validation coverage: [test/test_gm10h_persistence.py:54](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10h_persistence.py:54), [test/test_gm10h_persistence.py:136](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10h_persistence.py:136), [test/test_gm07b_save_schema.py:303](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_schema.py:303).

   **Fix:** retain explicit native-version cases proving v1/v2 reject grown fleets, v3/v4 accept them, and v3/v4 both retain strict map/tunnel validation. Mutate each real frozen v1/v2/v3 fixture with `pauseReasons=["week"]` to prove rejection at the vocabulary gate. Change the forward-version test from v4 to v5 at [test/test_gm07b_save_schema.py:185](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_schema.py:185).

6. **[MINOR] Documentation scope is incomplete, and `current_offers` is described with the wrong type.**

   The README still identifies v3 as current, `{1,2,3}` as supported, and only v3 as allowing grown fleets: [README.md:232](/C:/Users/38909/Documents/github/python_mini_metro/README.md:232), [README.md:234](/C:/Users/38909/Documents/github/python_mini_metro/README.md:234). The active project state still describes serializing the offer tuple rather than settling on reconstruction: [STATE.md:25](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:25), [STATE.md:102](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/STATE.md:102). Also, `current_offers` initializes to `()`, not `[]`: [src/mediator.py:170](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:170).

   **Fix:** update the README schema section, source persistence docstrings, active STATE/EVIDENCE, and the plan’s tuple wording in addition to GAME_RULES/ARCHITECTURE/PROGRESS/DECISIONS.

## Claims confirmed

- **Current-build derivation is exact.** `offer_rng_for_current_week` reads only the host RNG state and `week_index`, consuming no gameplay draws: [src/weekly_offers.py:101](/C:/Users/38909/Documents/github/python_mini_metro/src/weekly_offers.py:101). Python RNG state is serialized at [src/save_game.py:325](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:325) and deep-tuple-restored before `setstate` at [src/save_load.py:68](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:68).

- **Map boundedness is ready before reconstruction.** The map-backed mediator is constructed before RNG/scalar restoration, and `num_tunnels` derives from the map budget plus restored bonus: [src/save_load.py:368](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:368), [src/mediator.py:275](/C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:275). Strictly, bonus magnitude does not affect pool selection—only whether the map budget is finite.

- **The speed-4 `steps=1202` case works today.** Floor division produces week 1 and the crossing logic deliberately permits overshoot: [src/weekly_offers.py:35](/C:/Users/38909/Documents/github/python_mini_metro/src/weekly_offers.py:35), [test/test_gm10a_calendar.py:93](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm10a_calendar.py:93). A live read-only probe across Classic, River, Delta, and Lake reproduced identical tuples after RNG JSON round-trip, including `1198→1202`.

- **v4 plus gated vocabulary is the right compatibility discipline.** Existing code support-checks the version before selecting keys, so today’s v3 reader rejects v4 wholesale: [src/save_schema.py:107](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:107), [src/save_schema.py:301](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:301). Skipping the bump would silently redefine the language called “v3,” even though older code would eventually reject `week`.

- **No additional legitimate UI state needs persistence.** Continue loads, releases only `menu`, rebuilds the session, and enters PLAYING: [src/app_controller.py:249](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:249). Interactive `build_from` re-enables `week_calendar`: [src/main.py:239](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:239). Per-frame game-over reconciliation runs before week promotion, which cancels gestures, clears arming, and derives the OFFER screen: [src/main.py:378](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:378), [src/app_controller.py:184](/C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:184). Direct `deserialize_game` intentionally does not enable future calendar pauses; the interactive shell owns that policy.

- **Removing only the week quiescence branch is correctly scoped.** The gesture/draft/redraw/edit checks at [src/save_game.py:68](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:68) should remain. Such state can briefly coexist with a raw hold before controller promotion, but modal promotion cancels it; direct pre-promotion serialization should continue to fail. Canonical fleet, upgrade, and map-legality guards pass a genuine quiescent modal state.

- **The window-close branch is safe once the blockers above are fixed.** Remove only `resolve_week_boundary()` at [src/main.py:331](/C:/Users/38909/Documents/github/python_mini_metro/src/main.py:331). The game-over and OFFER states are mutually exclusive under the producer/reconciler ordering, while the writer remains atomic through `os.replace`: [src/save_game.py:335](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:335). The proposed test should inspect the real autosave because the shell intentionally swallows write failures.

- **Deserialize is the correct reconstruction owner.** Restore map, RNG, scalars—including steps, tunnel bonus, and pause reasons—and graph state; run legality checks; then reconstruct pending offers immediately before returning: [src/save_load.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:115), [src/save_load.py:357](/C:/Users/38909/Documents/github/python_mini_metro/src/save_load.py:357). Controller-only reconstruction would leave direct deserialization consumers with an incomplete mediator.

The focused existing suites (`test_gm10a_calendar`, `test_gm10b_offers`, and `test_gm10h_persistence`) passed all 61 tests; they establish a clean baseline but do not cover the blockers above.

## Open questions

1. **Version-gated vocabulary?** Yes. Add `week` only in v4; preserve the exact v1/v2/v3 languages.

2. **Boundary legality invariant?** Yes. Require non-terminal, historically reachable v4 boundary steps, plus canonical offer validation. The plan’s “no forgery gain” argument is incorrect because a forged step-0 `week` grants an early upgrade.

3. **Deserialize or controller?** Deserialize, after complete state restoration and legality validation, through one shared version-aware `WeeklyOffers` helper.

===END-REVIEW===

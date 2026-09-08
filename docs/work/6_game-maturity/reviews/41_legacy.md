# GM-10b — dual adversarial review synthesis (D-042)

## Plan review — harness REVISE, Codex BLOCK → the option-B pivot

Both lanes verified the deterministic-generator CORE sound (import-safe `offers.py`, `rng.sample` distinctness, the CLASSIC-excludes-TUNNEL pool, gating, tick ordering, zero-save-bytes). The two-lane review earned its keep decisively — the lanes DISAGREED on the load-bearing question, and Codex's BLOCKER drove a better design.

- Harness (`raw/plan-harness.md`, **REVISE**): verified every load-bearing claim against live code (+ an empirical spawn byte-compat check); 1 MAJOR (the plan's `draw_offer_screen` signature change breaks the GM-10a `_drive_run_game` harness — `_LoopMediator.current_offers` + arity-3 patch) + 3 minors. Rated deferring offer-stream persistence to GM-10h "clean".
- Codex ultra (`raw/plan-codex.md`, **BLOCK**): confirmed the same core claims, but BLOCKED on persistence — plan v1's dedicated `SeedSequence.spawn(3)` `offer_random` stream, unpersisted (deferred to GM-10h), would RESET on Continue, so the next week's offers DIVERGE from uninterrupted play, violating `README.md:66` "Continue … resumes exactly". Its suggested fix: "redesign generation as stateless from already-persisted inputs."

**Load-bearing decision — the pivot (option A → option B).** Verified Codex's BLOCKER against `README.md:66` (contract is real) and proved the fix empirically: `python_random.getstate()` at a week boundary is byte-IDENTICAL after a mid-game `serialize_game`→`deserialize_game` (seeds 0/1/7). So the per-week offer RNG is derived READ-ONLY from `python_random.getstate()` + `week_index` (sha256 over the repr) — Continue-exact with ZERO new persisted state, gameplay-inert (getstate consumes no draws), and STRICTLY simpler than v1 (no `SimulationContext` change, no save-schema migration, dissolves the gesture-rollback-snapshot concern). The harness MAJOR + all minors folded into PLAN v2.

Four premises were empirically proven BEFORE planning (observer-predicate lesson): games last ~4–6 weeks (offers meaningful); a separate offer stream is gameplay-inert; `spawn` is byte-back-compatible (moot after the pivot); and the load-bearing one — boundary `python_random` state is Continue-exact.

## Implementation review — harness SHIP, Codex FIX-FIRST → BOTH confirm the code CORRECT

Both lanes independently confirmed the PRODUCTION code CORRECT on every axis — the pivot resolves the BLOCKER (`getstate` read-only, sha256 unsalted, isolated `Random` does not advance gameplay RNG; save/load restores the exact state), zero save/checkpoint bytes, gating, ordering, and the offer pools all verified. **Every finding was TEST-STRENGTH** — the review-coverage lesson yet again, with the two lanes catching DIFFERENT mutation gaps.

- Harness (`raw/impl-harness.md`, **SHIP** + 3 findings): ran the suites/gates; 1 MINOR (the BOUNDED tunnel-pool ORDER isn't locked — a `LOCOMOTIVE`/`CARRIAGE` swap survives the whole suite, empirically confirmed) + 2 NITs (regenerate test over-claims; frozen-sequence CPython coupling).
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST** + 6 findings, each mutation-audited): the visible-offer path is mutation-weak (replacing `current_offers` with `()` in `main.py` survives the spy; removing the label blit survives because offer COUNT alone moves panel geometry); Continue-exact tested only with seed 0 (= the deserialize constructor seed, so a constructor-seed-salted derivation would pass yet diverge on seed 3); the inertness test checks `python_random` but not `numpy_random`; import-safety doesn't verify no-pygame; `count<1` tested only at zero; the RL content-fingerprint drift is undocumented.

## Folds — ALL 9 landed (each re-run green; the two Codex MAJORs on the visible path verified as genuine mutation-killers)
- Harness MINOR (bounded-pool order) → a FROZEN river-seed-0 sequence (`_RIVER_SEED0_SEQUENCE`, week 3 = TUNNEL) locks the order behaviorally; a swap now turns it red.
- Harness NITs → `test_derivation_depends_on_week_index` (isolates week_index directly); CPython-coupling comment on the frozen literals.
- Codex MAJOR (main forwards offers) → `test_run_loop_forwards_the_mediators_real_offers_to_the_modal` drives real `main.run_game` with a sentinel `current_offers` and asserts it reaches `draw_offer_screen` (replacing it with `()` turns red).
- Codex MAJOR (label glyphs painted) → `test_label_glyphs_are_actually_painted_not_just_the_panel` counts TEXT-color pixels (offers add 1631 glyph pixels beyond heading+Continue; removing the blit zeroes the delta → red).
- Codex MAJOR (Continue-exact non-zero seed) → the Continue-exact test now loops seeds (0, 3), catching a constructor-seed-salted derivation.
- Codex MAJOR (numpy inertness) → the inertness tests now assert `numpy_random.bit_generator.state` unchanged too.
- Codex MINOR (import-safety) → the subprocess now asserts `pygame not in sys.modules`.
- Codex MINOR (negative count) → `count<1` tested at 0, -1, -5.
- Codex MINOR (content-fingerprint doc) → ARCHITECTURE.md notes the expected live-content-fingerprint rotation (no fixture repin).

## Result
Both lanes confirmed the production code; all 9 test/doc gaps folded and re-run green (23 GM-10b tests + the GM-10a harness update). Full `py313` suite green (1529 tests); ruff + pre-commit clean. ORDERING CONSTRAINT recorded in D-042: GM-10c (apply a choice) must not trail GM-10h (applied-offer persistence). Ready to deliver [GM-10b:A] → CI → [GM-10b:B].

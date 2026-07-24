# GM-10d — review synthesis (D-044)

## Plan
Self-reviewed (a small, empirically-proven effect: a free line via the already-persisted `purchased_num_paths`). The whole design was probed BEFORE implementing — a grant takes `purchased_num_paths` 1→2 and `unlocked_num_paths` 1→2 with `line_credits` unchanged, the save round-trips both, and it caps at `num_paths` — confirming Continue-safe standalone (D-043). HIGH-RISK (game-mechanic) → dual IMPL review.

## Implementation — dual review (harness SHIP, Codex FIX-FIRST) → BOTH confirm the code CORRECT

Both lanes verified the PRODUCTION effect correct on every axis — the cap (`>= num_paths`), the cache refresh (identical to the purchase flow: `grant_free_path` → `update_unlocked_num_paths` recomputes `unlocked_num_paths` + the unlock-blink + button locks), no credit spend, Continue-storage (`purchasedNumPaths` already serialized/restored; `_require_running_config` pins the total `numPaths`, unchanged), RL/headless gating, and the correct GM-10c inertness-test narrowing. The harness even ran an in-process mutation probe confirming M1–M5 (cap, credit-spend, missing-refresh, no-op-arm, stub-granting) all turn a test red.

- Harness (`raw/impl-harness.md`, **SHIP** + 1 NIT): the offer pool isn't cap-aware (the documented wasted-pick limitation) — no change required.
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST** + 2 MAJOR + MINOR + NIT, each mutation-probed): a real robustness gap the harness's mutation probe couldn't surface (it only mutated the implementation, not the MISSING guard) + 3 test/comment gaps.

## Folds — ALL landed (each re-run green; Codex's MAJORs verified as genuine)
- **Confinement guard** (Codex MAJOR — robustness): `resolve_week_boundary(offer)` now raises unless the offer is one of `current_offers` at a held boundary, so no out-of-band/headless call can grant an upgrade and bypass the economy (test: resolve with no pending boundary, and with an unpresented kind, both raise and grant nothing).
- **Above-cap test** (Codex MAJOR — the `>=` cap wasn't pinned): a `==` mutant survived because a loaded save can hold `purchased > num_paths`; now `grant_free_path` is tested at `num_paths`, `+1`, `+3` → all no-op.
- **Unlock-blink test** (Codex MINOR): a mutant eagerly bumping `unlocked_num_paths` inside `grant_free_path` would suppress the blink; a test now asserts the free line's button blinks.
- **Stale comment** (Codex NIT): the `_apply_offer` "every arm is a no-op" comment corrected (NEW_LINE now grants).

## Additional: WeeklyOffers facade extraction (behavior-preserving)
Adding the GM-10d effect pushed `mediator.py` past the 1000-line HARD ceiling (test-enforced, 1002). Per the fleet canon "split rather than grow god-objects" (D-023), the GM-10a–d week-boundary hold + offer generate/apply LOGIC was factored into a new `src/weekly_offers.py` `WeeklyOffers` facade (like `NetworkProgression`/`PassengerFlow`). The facade is stateless — it reads/writes the host mediator's already-owned state with no new fields, and invokes the spy-able seams (`_apply_offer`/`_grant_free_line`/`_offer_rng_for_current_week`) through the host so tests patching those still intercept and the mediator keeps its public API. `mediator.py` drops to 940 lines. The extraction is behavior-preserving — every offer/calendar test (66) and the full py313 suite (1550) stay green — and relocates already-reviewed logic without changing behavior, so it is verified by the suite rather than a re-review; the one NEW behavior (the confinement guard) was reviewed by Codex.

## Result
Both lanes confirmed the production effect; all findings folded and re-run green (15 GM-10d/progression tests + the extraction). Full `py313` suite green (1550 tests); ruff + pre-commit clean; `mediator.py` back under the 1000-line ceiling. Ready to deliver [GM-10d:A] → CI → [GM-10d:B].

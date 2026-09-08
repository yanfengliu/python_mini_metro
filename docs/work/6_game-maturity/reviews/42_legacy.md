# GM-10c — review synthesis (D-043)

## Plan
Self-reviewed (proportionate: an additive `resolve_week_boundary(offer=None)` + a no-op-apply selection UI extending the GM-10a/b patterns just dual-reviewed). The arity ripple was grep-verified pre-implementation (`offer_menu_layout`/`resolve_week_boundary`/`draw_offer_screen` callers); the HIGH-RISK public-mediator-surface gate was honored at the IMPL stage with the dual review below.

## Implementation — dual review (harness SHIP, Codex FIX-FIRST) → BOTH confirm the code CORRECT

Both lanes independently verified the PRODUCTION code correct on every axis — arming/routing (armed down→matching up; a stale gameplay release cannot choose; index parse + bound guard safe; offers frozen between events so no wrong-offer race), the additive backward-compatible `resolve_week_boundary(offer=None)`, the no-op `_apply_offer` match-dispatch (all four `OfferKind`, named `ValueError` on unknown), the arity ripple (every caller updated, the GM-10a run-loop harness intact), the 0–4 layouts (on-screen, disjoint, byte-stable at 1920×1080), and NO GM-10d–g effect / GM-10h persistence leak. **Every finding was TEST-STRENGTH** — the review-coverage lesson again, with the two lanes catching DIFFERENT mutation gaps.

- Harness (`raw/impl-harness.md`, **SHIP** + 1 MINOR + 3 NITs): a stale `main.py` OFFER-render comment; an imprecise "defensive" comment; apply-before-clear order untested; the `_LoopMediator` fake missing the new `offer=None` default.
- Codex ultra (`raw/impl-codex.md`, **FIX-FIRST** + 4 MAJOR + 1 MINOR, each mutation-probed): release-ordering mutation-weak (a release-before-apply mutant passed); the inertness test not per-kind and blind to non-serialized runtime state (current_offers/week_calendar); the render tests don't bind each label to its rect and skip counts 3/4 (painting offer 0's label on every button, or dropping offer_2/3, survived); the arming test doesn't prove a mismatched release DISARMS (a clear-after-guard mutant let a later bare up choose); and stale docs (GAME_RULES:160, main.py QUIT comment, README "records the pick").

## Folds — ALL 9 landed (each re-run green; the Codex MAJORs verified as genuine mutation-killers)
- **Release ordering** (Codex MAJOR): the order test now captures BOTH `current_offers` AND `is_week_boundary_pending` at apply time and asserts `(week_offers, True)` — a release-before-apply OR clear-before-apply mutant turns it red.
- **Per-kind inertness** (Codex MAJOR): applied PER-KIND on a FRESH mediator (no cross-kind cancellation) over runtime state (`current_offers`/`week_calendar`/`is_paused`/`steps`/`time_ms`/…) PLUS the full `serialize_game` doc.
- **Label→rect binding + counts 3/4** (Codex MAJOR): renders 1..4 offers with DISTINCT labels and asserts `len(set(button-regions)) == count` (painting one label on every button collapses the set) plus every button painted and pairwise disjoint.
- **Mismatched-release-disarms** (Codex MAJOR): down offer_0 → up offer_1 → then a bare up offer_0 must NOT choose (a clear-after-guard mutant would wrongly choose).
- **Docs** (Codex MINOR + harness MINOR): GAME_RULES:160 calendar bullet (resolve via choosing an offer, not "Continue"), the `main.py` OFFER-render + QUIT comments (selectable buttons / no-choice forced resolve), README ("resolves the week", not "records the pick").
- **Harness NITs**: apply-before-clear order test (subsumed by the release-ordering fold), the imprecise defensive comment reworded, the `_LoopMediator` fake `offer=None`.

## Result
Both lanes confirmed the production code; all findings were test-strength/docs and are folded and re-run green (12 GM-10c tests + the GM-10a arming migration). Full `py313` suite green (1541 tests); ruff + pre-commit clean. D-043 records the per-EFFECT refinement of the D-042 ordering constraint (NEW_LINE Continue-safe via `purchased_num_paths`; locomotive/carriage/tunnel need GM-10h). Ready to deliver [GM-10c:A] → CI → [GM-10c:B].

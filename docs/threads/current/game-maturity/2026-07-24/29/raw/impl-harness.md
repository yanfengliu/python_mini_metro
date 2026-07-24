# GM-10c implementation review — harness lane (adversarial, live-code verified)

## Verdict: SHIP

The GM-10c implementation is correct on every dimension and the tests are genuinely mutation-resistant. One MINOR stale-comment fix should be folded into this commit (docs-as-part-of-change); it does not affect correctness. All checks done against live working-tree code, tests green (GM-10c 11/11; full GM-10a/b/c 56/56), ruff + format clean on all five changed files; no dangling arity-2 callers, no leftover `_OFFER_GAP`, no stale offer `"continue"` key.

## Confirmed correct
1. **Arming/routing** (`app_controller.py:326-351`) — down arms the key whose rect contains the press (or `None`); up fires only when `armed is not None and _clicked(layout, armed, position)`. On OFFER entry `reconcile_week_boundary` clears `_armed_menu_control` to None, so a stale gameplay mouse-up hits `armed is None` → early return. `int(armed.removeprefix("offer_"))` is safe (armed is always a layout key). Layout recomputed from `len(current_offers)` at both events; offers frozen (sim paused) between them → no wrong-offer race.
2. **`resolve_week_boundary(offer=None)`** — additive/backward-compatible; `main.py:335` (no-arg window-close) and every GM-10a/b test valid. Order: apply → clear → release.
3. **`_apply_offer` inertness** — every arm is `pass`; `match` covers all four `OfferKind`; `case _` raises a named `ValueError`. `test_applying_any_offer_is_state_inert` is a real lock (full `serialize_game` doc + 11 counters before/after applying every kind).
4. **Arity ripple** — every `offer_menu_layout(` caller passes `count`; `draw_offer_screen` was already arity-3; the GM-10a `_drive_run_game` harness still works.
5. **Render** — N disjoint buttons at `offer_i` rects; empty case uses the `else` branch (no KeyError); at the 4-offer max the stack spans y∈[540,850], disjoint, on-screen at 1920×1080.
6. **Test strength** — wrong-index routing / dropped-armed-match / broken-inertness / `case _`-not-raising / dropped-render-button all have a red-turning test.
7. **Scope** — no GM-10d-g effect and no GM-10h persistence leak; inertness against the full save doc proves zero new persisted bytes.

## Findings (all MINOR/NIT — production correct)
1. **[MINOR] Stale inline comment** at `src/main.py:432-433` ("previewed read-only (GM-10b)") — GM-10c makes them selectable buttons. Fix the comment (docs-as-part-of-change). FOLDED.
2. **[NIT] Imprecise "defensive" comment** at `app_controller.py:346-347` — a genuine shrink would `KeyError` at `_clicked(layout, armed, position)` before the index check; the race is architecturally impossible. Reworded. FOLDED.
3. **[NIT] Apply-before-clear order untested** — a clear-before-apply mutant turns no test red (no-op `_apply_offer` never reads `current_offers`). Added an order-pinning test (spy captures `current_offers` at apply time). FOLDED.
4. **[NIT] `_LoopMediator.resolve_week_boundary` missing `offer=None`** — harmless today (harness only drives the no-arg window-close path), but a future offer-click run-loop test would `TypeError`. Added the default. FOLDED.

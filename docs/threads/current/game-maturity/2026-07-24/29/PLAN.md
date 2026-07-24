# GM-10c plan — week-boundary offer CHOICE CONTROLS (D-043)

## Scope (minimal coherent unit)
Turn the GM-10b read-only offer PREVIEW into an interactive SELECTION: the week-boundary
modal shows a button per offer; the player arms+clicks one to CHOOSE it; the mediator
records/applies the choice through a per-kind dispatch and resumes play.

**In scope:** the multi-offer button layout + render; `_handle_offer` arm/click routing to a
chosen offer; `Mediator.resolve_week_boundary(offer=None)` + a `_apply_offer` per-kind DISPATCH
(no-op stubs); window-close still resolves with no choice.

**Explicitly OUT of scope (roadmap split):**
- The per-kind EFFECTS (what New Line / +1 Locomotive / +1 Carriage / +1 Tunnel actually DO) →
  GM-10d–g. In GM-10c the dispatch arms are no-op `pass` stubs.
- APPLIED-offer persistence / replay reconciliation → GM-10h.

## Continue-safety / ordering (D-042 constraint honored)
GM-10c's `_apply_offer` is a NO-OP dispatch — it changes NO game state — so nothing new needs
persisting and every save/checkpoint fixture stays byte-frozen (as GM-10a/b). The D-042 ordering
constraint (don't apply a persistent effect ahead of GM-10h) is satisfied vacuously: the first
unit that adds a REAL persistent effect (GM-10d line, GM-10e/f/g fleet/tunnel) inherits the
constraint — GM-10d's line grant can flow through the already-persisted `purchased_num_paths`
(Continue-safe), while GM-10e/f/g touch `_require_running_config`-pinned `num_metros`/`num_carriages`
or the immutable tunnel budget and MUST land with GM-10h. Record this refinement in D-043.

## Design (per file)

### `src/ui/menu_screens.py`
- `offer_menu_layout(width, height, count)` gains `count`: return `_stacked_buttons(width,
  tuple(f"offer_{i}" for i in range(count)), height // 2)` — one button per offer, keyed
  `offer_0..offer_{count-1}`. `count == 0` → an empty layout (defensive; the modal is only shown
  with offers, but the boundary can be reached with an empty pool on a hypothetical 0-offer config).
- `draw_offer_screen(surface, week_index, offers)`: render each offer as a BUTTON (via `_draw_button`)
  at its `offer_i` rect, labeled `offer.label`; heading above. (Replaces the GM-10b read-only panel —
  the offers are now interactive.) Byte-stable on repeat (buttons already are).

### `src/app_controller.py`
- `_handle_offer(event)`: layout from `offer_menu_layout(screen_width, screen_height,
  len(self.mediator.current_offers))`; arm on mouse-down over an `offer_i` key; on mouse-up over the
  SAME armed `offer_i` (the GM-10a arming discipline — a stale gameplay mouse-up cannot choose),
  resolve with that offer: `self.mediator.resolve_week_boundary(self.mediator.current_offers[i])`
  then `state = PLAYING`. Index parsed from the key suffix; guard the index against the live
  `current_offers` length (a shrunk-offers race resolves without applying).

### `src/mediator.py`
- `resolve_week_boundary(self, offer: Offer | None = None)`: `if offer is not None: self._apply_offer(offer)`;
  then `self.current_offers = ()`; `release_pause_reason(_WEEK_REASON)`. Backward-compatible — the
  GM-10a window-close path (`main.py`) calls `resolve_week_boundary()` (no arg) → no apply, just
  clear+release (a forced skip on window close).
- New `_apply_offer(self, offer: Offer) -> None`: a `match offer.kind` dispatch with one arm per
  `OfferKind`, each a no-op `pass` carrying a `# GM-10d/e/f/g: <effect>` comment. A named
  `ValueError` on an unknown kind (defensive; every enum member is covered so it is unreachable, but
  a future kind without a handler must fail loud, not silently no-op).

### `src/main.py`
- No change needed — the OFFER-QUIT path already calls `resolve_week_boundary()` (no arg); the render
  still calls `draw_offer_screen(..., current_offers)`. (The signature is unchanged.)

### `src/config.py`
- No change.

## TDD tests (`test/test_gm10c_choice.py`)
1. **Selection routing**: with 2 offers, an armed down+up on `offer_0` resolves with
   `current_offers[0]`; on `offer_1` with `current_offers[1]` (spy `resolve_week_boundary`).
2. **Arming discipline**: a bare mouse-up (no matching in-offer down) does NOT resolve; a
   down on `offer_0` then up on `offer_1` does NOT resolve (armed control must match) — mirrors the
   GM-10a Continue arming.
3. **Resume**: after a valid pick the controller returns to PLAYING and `current_offers` is cleared.
4. **`resolve_week_boundary(offer)` applies then clears**: passing an offer calls `_apply_offer`
   (spy/subclass) with THAT offer before clearing; `resolve_week_boundary()` (no arg) clears WITHOUT
   applying (window-close path).
5. **No-op apply is state-inert (Continue-safe)**: applying every `OfferKind` leaves deliveries,
   line_credits, num_metros, num_carriages, purchased_num_paths, num_tunnels, and the full
   `serialize_game` doc byte-identical (the effects are GM-10d-g; GM-10c must change nothing).
6. **`_apply_offer` covers every kind**: parametrize over all `OfferKind` — none raises; an
   unknown/forged kind raises the named `ValueError`.
7. **Index-guard race**: a resolve whose parsed index is out of range for the live `current_offers`
   resolves without applying (no IndexError).
8. **Render**: `draw_offer_screen` paints N distinct offer buttons at the `offer_i` rects (each
   label's glyphs present, byte-stable on repeat); the rects are disjoint.
9. **Gating unaffected**: RL/headless still never reach the offer path (`current_offers == ()`); the
   GM-10a/b run-loop OFFER harness still promotes+renders (updated for the new layout arity).
10. **GM-10a/b harness update**: `offer_menu_layout` callers now pass `count`; verify the existing
    GM-10a arming test (`test_continue_requires_an_offer_local_down_up_pair`) is migrated to the
    per-offer buttons (there is no longer a "continue" key).

## Risks / review foci
- **HIGH-RISK**: `app_controller`/`mediator` public surface + a game-mechanic (`src/`). Dual plan +
  dual impl review.
- **The GM-10a `test_continue_requires_an_offer_local_down_up_pair` test + `offer_menu_layout`'s
  arity change** ripple to any caller — grep every `offer_menu_layout(` / `draw_offer_screen(` /
  `resolve_week_boundary(` site (main, app_controller, the GM-10a/b tests) and update.
- **No-op apply must be genuinely inert** — test 5 locks it; a stray effect would be a scope leak.
- **Arming/index parsing** — the `offer_i` key suffix parse must be robust; guard the index.

## Decision record: D-043 (append to DECISIONS.md).

# GM-10d plan — the NEW_LINE offer effect: a free line (D-044)

## Scope
Fill the `OfferKind.NEW_LINE` arm of `Mediator._apply_offer` (a no-op stub since GM-10c) with
its real effect: GRANT A FREE LINE — unlock the next metro line without spending line credits.
The first REAL per-kind offer effect; the locomotive/carriage/tunnel arms stay no-op stubs
(GM-10e/f/g).

## Design (empirically proven Continue-safe — probe this session)
### `src/progression.py`
- `grant_free_path(self) -> bool`: if `purchased_num_paths >= num_paths`, return False (already at
  the line cap — no-op); else `purchased_num_paths += 1` and return True. Mirrors
  `record_path_purchase` MINUS the `line_credits -= price` spend, and adds the cap the purchase path
  gets for free (a purchase is only offered while `unlocked < num_paths`).

### `src/mediator.py`
- New `_grant_free_line(self) -> None`: `if self._progression.grant_free_path(): self.update_unlocked_num_paths()`
  — exactly the purchase flow's cache refresh (`record_path_purchase` → `update_unlocked_num_paths`,
  which recomputes `unlocked_num_paths` and the path-button lock states).
- The `_apply_offer` `case OfferKind.NEW_LINE:` arm calls `self._grant_free_line()` (replacing the
  `pass`). The other three arms stay no-op.

## Continue-safety (proven, no schema change)
- `purchased_num_paths` is ALREADY persisted (`purchasedNumPaths`); a grant bumps it, and the save
  round-trips it exactly (probe: grant → purchased 1→2, unlocked 1→2, credits UNCHANGED;
  serialize→deserialize reproduces both; `numPaths`=4 unchanged so `_require_running_config` is
  satisfied). So GM-10d is Continue-safe STANDALONE and precedes GM-10h (D-043). NO new persisted
  bytes, NO save/checkpoint-schema change.
- RL/headless never reach `_apply_offer` (offers gated to the human shell); a grant only happens on
  an interactive pick.

## Known limitation (documented, not blocking)
When all `num_paths` lines are already unlocked, a NEW_LINE grant is a no-op (a wasted pick).
Excluding NEW_LINE from the offer POOL when maxed would couple `generate_offers` to
`purchased_num_paths`; deferred as a GM-11 balance refinement. Rare in practice (4 lines is late-game).

## TDD tests (`test/test_gm10d_line.py`)
1. **Grant unlocks a line**: `grant_free_path` on a fresh progression: `purchased_num_paths` 1→2,
   `unlocked_num_paths` 1→2 (after the mediator cache refresh), `line_credits` UNCHANGED.
2. **Cap**: grant repeatedly → `purchased_num_paths` stops at `num_paths`; a further grant returns
   False and is a no-op.
3. **Applying the NEW_LINE offer unlocks a line**: `resolve_week_boundary(describe(NEW_LINE))` bumps
   `unlocked_num_paths` by 1 (and clears offers, releases pause) — the full pick→effect path.
4. **Continue-exact**: grant → mid-game `serialize_game`→`deserialize_game` reproduces
   `purchased_num_paths`/`unlocked_num_paths`; the save still loads (no `_require_running_config`
   failure); `numPaths`/`numMetros`/`numCarriages` unchanged.
5. **No credit spend**: a grant does not change `line_credits` (distinct from a purchase).
6. **The other kinds stay inert**: applying LOCOMOTIVE/CARRIAGE/TUNNEL still changes nothing
   (they are GM-10e/f/g) — narrow the GM-10c all-kinds-inert test to the three still-stub kinds.
7. **Grant refreshes the path-button lock states** (the new line's button unlocks), mirroring a
   purchase.

## Ripple
- **GM-10c `test_applying_each_offer_is_state_inert`** now FAILS for NEW_LINE (it is no longer
  inert). Narrow it to the three still-stub kinds (LOCOMOTIVE/CARRIAGE/TUNNEL); NEW_LINE gets its
  own effect test in `test_gm10d_line.py`. Grep every "all kinds inert" assertion.

## Risks / review foci
- **HIGH-RISK**: game-mechanic/economy change in `src/` (mediator + progression). Dual impl review.
- The cap (must not exceed `num_paths`); the cache refresh (unlocked_num_paths + button locks);
  Continue-exactness (proven); no credit spend; the GM-10c inertness-test narrowing.

## Decision record: D-044.

# GM-10e/f/g impl review — harness lane

Verdict: **SHIP**

Independent adversarial review of the three filled offer arms in `src/weekly_offers.py`
(`apply_offer`) and their tests, against the live code. Ran the full `py313` suite
(1572 at review time), the targeted `test_gm10efg_effects` + `test_gm10c_choice` +
`test_gm10d_line` (26/26), and `ruff check`/`format --check` (clean).

## Refutation targets — all HOLD

1. **Containment** — LOCOMOTIVE touches only `num_metros`, CARRIAGE only
   `num_carriages`, TUNNEL only `tunnel_bonus`. Confirmed against the arms and the
   per-test containment assertions; swapping an arm turns the exact-growth assertion
   red.
2. **Fleet-growth soundness** — `available_locomotives`/`available_carriages` derive
   from the totals as caps (`max(0, total - assigned)`), the per-tick reconcile and
   carriage attach read the totals, none treats them as a collection length. A bumped
   total is one more unassigned slot.
3. **TUNNEL safety** — `generate_offers` excludes TUNNEL when `num_tunnels is None`,
   so the arm only runs on a bounded map; the `resolve_week_boundary` confinement
   guard + the GM-10h serialize guard together bar an unbounded-map bonus.
4. **Persistence Continue-exact** — grown totals + `tunnelBonus` round-trip through
   `serialize_game`/`deserialize_game` under the v3 relaxed pin.
5. **RL-gating** — the arms are reached only through the calendar-gated human
   `resolve_week_boundary(offer)`; a 1200+-tick headless env keeps fleet at config and
   `tunnel_bonus == 0`.
6. **Correct test removal** — retiring `test_applying_a_stub_offer_kind_is_state_inert`
   was correct (its premise — the kinds are no-ops — is now false); no dead code left
   (the `_INERT_ATTRS` constant + the now-unused `serialize_game` import were removed).
7. **Test strength** — `+= 2`, swapped arms, and unconditional TUNNEL each turn a
   test red.

## Finding

- **[LOW] containment is pinned only against the other two upgrade quantities.** The
  per-test containment assertions (e.g. LOCOMOTIVE checks `num_carriages` +
  `tunnel_bonus` unchanged) do not pin the rest of the game state. A hypothetical arm
  that ALSO did `line_credits += 1` would survive the new tests. Fix: add a broad
  before/after check over the full `serialize_game` doc, permitting only the one
  designated key to differ.

## Result

Production code correct; ship after folding the LOW (broad-doc containment). The one
LOW overlaps the Codex lane's MAJOR-1.

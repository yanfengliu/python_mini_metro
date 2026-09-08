# GM-10e/f/g — PLAN (self-reviewed; D-046)

## Scope

Fill the last three per-kind offer arms in `weekly_offers.apply_offer`, delivered as
ONE unit (deviating from the roadmap's GM-10e / GM-10f / GM-10g split):

- `OfferKind.LOCOMOTIVE` → `host.num_metros += 1`
- `OfferKind.CARRIAGE` → `host.num_carriages += 1`
- `OfferKind.TUNNEL` → `host.tunnel_bonus += 1`

## Why one unit, and why NO dual plan review

Each arm is a SINGLE line on the shared GM-10h (D-045) persistence infrastructure,
which was already built + twice-SHIP'd expressly so these effects would be trivial
(the `within_tunnel_budget` bonus-fold, the v3 relaxed pin, the reachability rule, the
serialize guard all landed in GM-10h). The design was fully SETTLED by D-045, so:

- **Delivered together** (the "strong defaults, not law" clause): three separate
  explore→plan→review→A/B/CI cycles for ~3 lines would be pure overhead; one coherent
  "all upgrade effects work" delivery is more valuable and end-to-end testable.
- **Self-reviewed plan, not dual plan review**: no design decision is open — a single
  line per arm against a settled contract. The residual risk (an arm touching the
  wrong/extra quantity) is a CODE risk caught by the containment tests, so the review
  effort belongs at the IMPLEMENTATION stage (dual impl review), not the plan stage.

## Derived-readout & persistence claim (verified before writing tests)

No cache refresh is needed (unlike NEW_LINE's `update_unlocked_num_paths` button-lock
refresh): `available_locomotives`/`available_carriages`/`num_tunnels`/
`available_tunnels` all DERIVE, so a bumped total/bonus flows to every readout for
free, and the grown state persists via save-schema v3 with no further schema work.
Empirically probed end-to-end first (per the observer-predicate lesson): LOCOMOTIVE
grows `num_metros` 4→5 (`available_locomotives` 5) and round-trips; CARRIAGE 2→3;
TUNNEL on RIVER grows `tunnel_bonus` 0→1 and `num_tunnels` 3→4 and round-trips.

## TUNNEL needs no bounded-map guard

`offers.generate_offers` excludes TUNNEL from the pool when `num_tunnels is None`
(CLASSIC), so the arm only ever runs on a bounded map where the bonus is reachable
(pinned by `TestGM10efgUnbounded`).

## Tests (TDD)

New `test/test_gm10efg_effects.py`: per-kind growth + persistence + containment + the
applied-TUNNEL-unblocks-a-real-crossing path through the live `within_tunnel_budget`
gate + RL-unaffected + never-offered-on-unbounded. Retire the now-false GM-10c
"stub kinds are state-inert" test.

## Delivery

Dual impl review → fold → gates → [GM-10e/f/g:A] → exact-head CI → [GM-10e/f/g:B].

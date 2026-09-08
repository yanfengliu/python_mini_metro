# GM-10e/f/g — review synthesis (D-046)

The last three per-kind offer arms filled on the GM-10h persistence infrastructure,
delivered together (each a single line): LOCOMOTIVE `num_metros += 1`, CARRIAGE
`num_carriages += 1`, TUNNEL `tunnel_bonus += 1`.

## Plan — self-reviewed (no dual plan review; see PLAN.md)

The design was fully SETTLED by D-045 (GM-10h built the persistence + the
`within_tunnel_budget` fold + the reachability rule so these effects would be trivial),
so no plan review was warranted — a single line per arm against a settled contract, with
the residual risk (an arm touching the wrong/extra quantity) belonging to the impl
stage. Empirically probed end-to-end before writing tests (observer-predicate lesson).

## Implementation review — harness SHIP, Codex FIX-FIRST → code correct by BOTH lanes

Both lanes independently confirmed the ARMS THEMSELVES CORRECT; every Codex finding is
TEST-STRENGTH or doc, not a code defect. (17th two-lane instance where the second lane
deepens coverage a green suite hid.)

- Harness (`raw/impl-harness.md`, **SHIP**): all 7 refutation targets HOLD (containment,
  fleet-growth-as-caps, TUNNEL safety, Continue-exact persistence, RL-gating, correct
  test removal, test strength — `+= 2`/swapped arms/unconditional TUNNEL each turn a test
  red). 1 LOW: containment pinned only against the other two upgrade quantities.
- Codex (`raw/impl-codex.md`, **FIX-FIRST**): CONFIRMED the arms are correct one-line
  `+= 1` mutations, fleet totals are caps (availability/assignment/attach/reconcile all
  subtract assigned, none treats a total as a length), TUNNEL excluded on unbounded +
  rejected at save/load, persistence correct (v3 accepts `>= config`, stores/restores
  all three), RL/headless unaffected. 2 MAJOR + 2 MINOR, all test-strength/doc.

Codex's impl lane ran clean this time (exit 0) under a non-adversarial framing — the
prior-unit cybersecurity-filter decline mode did not recur.

## Folds — landed (all four findings)

1. **[MAJOR, both lanes] Containment not pinned against the full state.** The per-test
   containment checks only the OTHER two upgrade quantities; an arm that also bumped
   `line_credits`/`deliveries`/etc. would survive. → `TestGM10efgContainment.
   test_each_effect_changes_only_its_own_save_field`: applies each kind on a played-in
   mediator and asserts the full `serialize_game` doc differs in EXACTLY the one expected
   key (`numMetros`/`numCarriages`/`tunnelBonus`).
2. **[MAJOR, Codex] Slot-usability not proven — only the derived count.** The growth
   tests upgrade an EMPTY fleet and check the count; a consumer that clamped
   assignment/attachment to the original config would pass. → `TestGM10efgSlotUsable`:
   EXHAUST config capacity (assign 4 locomotives / attach 2 carriages through the real
   fleet/carriage path), confirm the next is rejected, upgrade, then confirm exactly one
   MORE is genuinely assignable/attachable and the one after is rejected. This drives the
   grown total through `fleet_management.can_assign` / `carriage_management._attach_candidate`,
   which read `num_metros`/`num_carriages` — so a clamp-to-config regression turns red.
3. **[MINOR, Codex] `available_tunnels` untested.** The TUNNEL test checked
   `tunnel_bonus`/`num_tunnels`/persistence/the crossing gate but not the derived
   remaining-budget readout; a readout that ignored the bonus would stay green. → the
   TUNNEL test now asserts `available_tunnels == before + 1`. (Structurally, `available_
   tunnels = max(0, num_tunnels - consumed)` and `num_tunnels` folds the bonus, so the +1
   holds off any consumed base below the floor; the zero-consumed boundary case exercises
   the fold the readout reads.)
4. **[MINOR, Codex] Stale GM-10d test name/doc.** `test_gm10d_line.py` still called the
   non-line kinds "stub no-ops" that "grant nothing," though its body only checks they
   don't unlock a LINE. → renamed to `test_non_line_offer_kinds_do_not_unlock_a_line` +
   corrected the module docstring/comment (they grow the fleet/tunnel budget, not lines).

## Result

Both lanes agree the code is correct; all four findings folded (2 MAJOR + 2 MINOR).
Full `py313` suite green (1575 tests, +3: containment + 2 slot-usability); ruff +
format clean on all changed files. GM-10 now has its full weekly upgrade set (New Line +
Locomotive + Carriage + Tunnel, all persisted). Ready to deliver [GM-10e/f/g:A] → CI →
[GM-10e/f/g:B]; GM-10i (mid-offer PENDING-offer persistence) completes GM-10.

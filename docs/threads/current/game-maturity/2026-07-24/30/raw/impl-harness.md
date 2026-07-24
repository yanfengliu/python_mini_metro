# GM-10d implementation review — harness lane (adversarial, live-code verified)

## Verdict: SHIP

Read the live working-tree code (`progression.py`, `mediator.py`, `input_coordinator.py`, `path_lifecycle.py`, `save_load.py`, `save_schema.py`, `save_game.py`, `offers.py`, `app_controller.py`, `main.py`, both test files); ran the two suites (18 pass), the full suite (1547 pass), ruff (clean), and an in-process mutation probe confirming every load-bearing behavior has a red-turning test.

## Claims verified against live code
1. **Cap** — `grant_free_path` caps via `if purchased >= num_paths: return False`; never exceeds. `get_unlocked_num_paths = min(max(1, purchased), num_paths)` returns `num_paths` at/after the cap. The off-by-one `>` mutation is caught red (M1).
2. **Cache refresh** — `_grant_free_line` calls the SAME `update_unlocked_num_paths()` the purchase flow uses (`try_purchase_path_button` → `record_path_purchase` → `update_unlocked_num_paths` → recompute unlocked + unlock-blink + `update_path_button_lock_states`). No refresh the purchase does that the grant skips. Grant refreshes only on an actual grant (a no-op grant warrants no refresh) — correct. Skipping the refresh is caught red (M3).
3. **No credit spend** — `grant_free_path` never touches `line_credits`. A credit-spending grant is caught red (M2).
4. **Continue-safety** — no `save_*.py` touched; `purchasedNumPaths`/`unlockedNumPaths` already serialized+restored; `_require_running_config` pins `numPaths` (total, unchanged) not `purchasedNumPaths`; schema `_validate_progression`/`_validate_buttons` stay consistent because the grant refreshed both; round-trip reproduces `purchased=2`/`unlocked=2` and load does not raise (M3 shows dropping the refresh makes the round-trip fail). ZERO new save bytes.
5. **RL/headless gating** — `week_calendar` default False, set only by `main.run_game` on `max_frames is None`; `env.py` never touches it; `_apply_offer` reached only from the human choice + window-close paths. RL can never grant a line.
6. **GM-10c narrowing** — `test_applying_a_stub_offer_kind_is_state_inert` now iterates only (LOCOMOTIVE, CARRIAGE, TUNNEL); the other `for kind in OfferKind` loops (handles-every-kind = must-not-raise; render) are unaffected. Because `_INERT_ATTRS` includes `purchased_num_paths`/`unlocked_num_paths`, this narrowed test ALSO catches a stub arm accidentally granting (M5).
7. **Test strength** — mutation probe: off-by-one cap (M1), credit spend (M2), missing refresh (M3), NEW_LINE arm no-op (M4), stub arm granting (M5) — all caught red; baseline green.
8. **Scope** — locomotive/carriage/tunnel arms remain `pass`; no save-schema change; the NEW_LINE-at-cap wasted pick is documented + tested as a state-inert no-op.

## Findings
1. **[NIT / informational]** The offer pool is not cap-aware (`generate_offers` has no `purchased_num_paths >= num_paths` awareness), so a maxed-out player can pick NEW_LINE and receive nothing — exactly the documented known-limitation, correctly handled as a safe no-op. NOT a bug; GM-10h-or-later scope to filter. Flagged only to keep the "don't offer NEW_LINE at cap" decision conscious. No change required for this increment.

No BLOCKER/MAJOR/MINOR. The change is correct, Continue-exact with no schema change, gated off RL, and its tests are genuinely mutation-resistant.

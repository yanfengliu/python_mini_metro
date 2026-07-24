# GM-10i — mid-offer PENDING-offer persistence (save-schema v4, D-047) — REVISED after dual plan review

## Dual plan review outcome → a PIVOT

- Harness: **REVISE** — 1 BLOCKER (v3 fleet-pin relaxation gates on `==V3`, so a v4 grown-fleet boundary save fails Continue) + 5 MAJOR (the other `==V3`/`(V2,V3)` gates, test-repoint blast radius, second fixture) + 2 MINOR. Confirmed the re-derivation is exact WITHIN THE BUILD and the flow integration holds.
- Codex ultra: **BLOCK** — 2 BLOCKER + 3 MAJOR + 1 MINOR. Converged with the harness on the version-gate breakage (Codex BLOCKER-2 = harness BLOCKER-1), and caught a DEEPER one the harness missed:

**Codex BLOCKER-1 (the pivot driver): re-derivation is NOT cross-version stable.** The offer set is a function of `WEEK_LENGTH_STEPS`, `OFFERS_PER_WEEK`, the pool order/labels, and CPython's `random.sample` — all LIVE code, and the two constants are EXPLICITLY provisional-for-GM-11 (config.py:88/95; GM-11, the next milestone, tunes balance). A v4 pending save re-derived after GM-11 changes them would re-present DIFFERENT offers (or a different week/count), violating README "Continue resumes exactly." A version bump doesn't help — a future loader still accepts v4 and re-derives with changed code.

### PIVOT: persist the shown offer kinds (Option A), do NOT re-derive on load
Store the resolved offer OUTPUT (the kinds shown), not a recipe to recompute it. Self-contained, cross-version-stable, and semantically what a mid-offer save means ("store what it was showing"). This is the REVERSE of GM-10b's pivot (which dropped a persisted RNG STREAM); it does not conflict — next-week offers still derive statelessly from the RNG state; only the CURRENTLY-PRESENTED tuple is persisted, and only while a boundary is held. Crucially, the loader must NOT couple to `WEEK_LENGTH_STEPS`/`OFFERS_PER_WEEK` (that would reintroduce the very cross-version fragility the pivot removes — see the reachability decision below).

## The v4 capability matrix (explicit version membership — both lanes)
Every capability gate becomes an explicit version set, NOT `==V3` and NOT `>=` (Codex asked for explicit sets):
- Exact top-level keys: v1 → V1; v2 → V2; v3 → V3; **v4 → V4 = V3 ∪ {`pendingOffers`}**.
- Map identity validator: **v2/v3/v4**.
- Tunnel-bonus validator: **v3/v4**.
- Grown-fleet pin relaxation (`_require_running_config`): **v3/v4** (`in (V3, V4)`) — fixes the BLOCKER (a v4 grown-fleet boundary save loads).
- Pause vocabulary: v1/v2/v3 → {menu,user}; **v4 → {menu,user,week}** (thread `version` into `_validate_scalars`).

## Changes

### 1. `src/save_schema.py` — v4
- `SAVE_SCHEMA_VERSION_V4 = 4`; `SAVE_SCHEMA_VERSION = V4`; `SUPPORTED = {1,2,3,4}`.
- `_PENDING_OFFERS_KEY = frozenset({"pendingOffers"})`; `_TOP_LEVEL_KEYS_V4 = _TOP_LEVEL_KEYS_V3 | _PENDING_OFFERS_KEY`; add a v4 branch to `_top_level_keys_for`.
- Version-gate the pause vocab: thread `version` into `_validate_scalars` (or a dedicated `_validate_pause_reasons(document, version)`); allow "week" only for v4.
- New `_validate_pending_offers(document)`: a list of KNOWN OfferKind string values (`new_line/locomotive/carriage/tunnel`), pairwise DISTINCT; consistency `bool(pendingOffers) == ("week" in pauseReasons)`. Do NOT pin `len == OFFERS_PER_WEEK` (provisional constant — a stored tuple is what was shown). Gate map-identity to (V2,V3,V4), tunnel to (V3,V4), pending-offers to (V4,) in `validate_save`'s version dispatch.

### 2. `src/save_load.py`
- `_require_running_config`: gate the relaxation on `schemaVersion in (V3, V4)` (import V4).
- Restore `current_offers` from `pendingOffers`: `tuple(describe(OfferKind(v)) for v in document["pendingOffers"])` (v4; empty→()). NO generate_offers/re-derivation.
- Load-time fail-closed checks (version-stable, NOT coupled to WEEK_LENGTH_STEPS):
  - reject "week" pause reason when `isGameOver` is true (a terminal tick skips the hold — impossible/forged);
  - reject a pending offer kind NOT in the restored map's pool (e.g. TUNNEL on an unbounded map) — mirrors `_require_legal_map_state`.
- Update the `deserialize_game` docstring (drop "v1 or v2").

### 3. `src/save_game.py`
- Remove ONLY the "week" branch of `_require_quiescent` (keep gesture/draft/redraw/edit).
- serialize writes `schemaVersion = V4` and `"pendingOffers": [o.kind.value for o in current_offers]`.
- Serialize-time INTEGRITY guard (the GM-10h `_require_valid_upgrade_state` analog, via a shared `WeeklyOffers` helper): when a boundary is pending, `current_offers` MUST equal the canonical derivation (catch a desynced/reordered/stale offers before the atomic write); when not pending, `current_offers` MUST be () and no "week" reason. This ties the STORED offers to the genuine derivation at write time, so a legit v4 save is never stale — while load stays derivation-free for cross-version safety.

### 4. `src/weekly_offers.py`
- Extract `WeeklyOffers.derive_current_offers(host)` (the `generate_offers(_offer_rng_for_current_week(), OFFERS_PER_WEEK, num_tunnels is not None)` call) used by BOTH `maybe_hold_boundary` and the serialize-time integrity guard (single source; preserves the spy seam). (Harness MINOR-7 + Codex.)

### 5. `src/main.py`
- OFFER + QUIT: drop `resolve_week_boundary()`; just `write_autosave(controller.mediator)` with the pending boundary intact. Update the comment.

### 6. Fixtures (both lanes — TWO distinct v4 fixtures)
- `save-v4-classic.json` — a menu-paused CLASSIC line game (NOT pending), the v1/v2/v3→v4 upgrade target + v4 idempotence + cross-process canonical bytes. `EXPECTED_SAVE_V4_*` pins.
- `save-v4-river-pending.json` — a v4 River save AT a pending boundary (`pauseReasons` includes "week", non-empty `pendingOffers`), pinning the new capability + exact offer restoration.
- v1/v2/v3 fixtures stay byte-frozen.

### 7. Docs (wider scope — Codex MINOR-6 + harness MINOR-8)
- README schema section (v4, SUPPORTED {1,2,3,4}, grown fleets v3/v4), the window-close-mid-offer line; GAME_RULES (mid-offer Continue RE-PRESENTS the modal); ARCHITECTURE (v4 + persisted pendingOffers); PROGRESS; DECISIONS (D-047); the `deserialize_game` docstring; STATE/EVIDENCE (they currently say "serialize the offer tuple ... re-derive is an option" — settle on persist-the-kinds).

## TDD (tests first) — closing the review-found gaps
- **Grown-fleet-at-boundary (the BLOCKER):** a v4 River save with `numMetros=config+1`, `numCarriages=config+1`, `tunnel_bonus=1`, "week" pending → round-trips + restores the exact `pendingOffers`. (My original TDD started fresh — invisible to this bug.)
- **Cross-version robustness (Codex BLOCKER-1):** a v4 pending save restores its STORED offers even when the live derivation would differ — simulate by loading a doc whose `pendingOffers` is a fixed value and asserting it is restored verbatim (not recomputed); + a serialize-time test that a desynced `current_offers` (≠ canonical) is REJECTED before write.
- **Native-version retention (Codex MAJOR-5):** explicit v1/v2 docs REJECT a grown fleet; v3 AND v4 ACCEPT it; v3 and v4 both keep strict map/tunnel validation (don't let the bump erase native-v3 coverage).
- **Vocab gate:** a v1/v2/v3 doc carrying "week" is REJECTED; a v4 doc with "week" + consistent `pendingOffers` is accepted; forged inconsistency (week w/o offers, or offers w/o week) rejected; "week"+isGameOver rejected; TUNNEL offer on classic rejected.
- **Full Continue path:** v4 boundary save → controller promotes to OFFER on reconcile → choosing an offer applies + resumes (end-to-end past the restored modal).
- **Window-close:** the OFFER+QUIT autosave persists the PENDING state (not a forced resolve).
- **Repoints (both lanes, enumerated):** `test_gm07b_save_schema.py:159-161/169/186` (VERSION/SUPPORTED→{1,2,3,4}, add V4=4, forward-mutation 4→**5**), `test_gm09f_save_map.py:48/67`, `test_gm07b_save_determinism.py:32/295/408-419` (v3→v4 upgrade target = the new classic fixture), `test_gm10h_persistence.py:54/124/136` (schemaVersion 3→4; keep native-v3 grown-fleet cases). Frozen v4 SHA pins.
- **RL/headless unaffected:** no calendar → never pending → `pendingOffers` always [] → v4 bump doesn't touch checkpoint/observation.

## Threat model (Codex MAJOR-3, with a documented deviation)
Persisted `pendingOffers` are AUTHORITATIVE editable state (like `num_metros`/`deliveries`): a forged "week"+offers grants at most ONE deterministic upgrade on Continue — no worse than forging `purchased_num_paths` directly (D-045 model). Serialize-time canonical validation keeps LEGIT saves genuine; the isGameOver-reject and pool-consistency rejects close the clearly-impossible forgeries. **Deviation from Codex's steps-reachability suggestion:** we do NOT add `steps % WEEK_LENGTH_STEPS < 4` at load — it would couple the loader to the PROVISIONAL `WEEK_LENGTH_STEPS`, reintroducing the exact cross-version fragility this pivot removes (a v4 save at old steps=1200 would fail after GM-11 retunes the length). The residual forge (a hand-crafted "week" at a non-boundary step) yields ≤1 deterministic upgrade, within the accepted threat model. Reviewers: weigh this at impl.

## Review path
Dual PLAN review done (both lanes; a pivot + the version-gate matrix folded). The pivot is the reviewers' own recommended fix and is a well-trodden persist-authoritative-state + validate-at-serialize shape (GM-10h's `_require_valid_upgrade_state`). Proceed to TDD → implement → DUAL IMPL review (multi-cli escalation; the schema-v4 + serialize-integrity surface is the load-bearing part) → [GM-10i:A] → CI → [GM-10i:B]. COMPLETES GM-10.

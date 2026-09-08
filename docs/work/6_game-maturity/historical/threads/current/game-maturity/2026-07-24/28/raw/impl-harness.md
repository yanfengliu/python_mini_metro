# GM-10b implementation review — harness lane (adversarial, live-code verified)

## Verdict: SHIP

The production code is correct on every axis the task asked me to refute — Continue-exactness, gameplay-inertness, gating, the offer model, the modal render, and zero save/checkpoint bytes. I found **one MINOR test-strength gap** (empirically confirmed) worth closing, but it does not block.

Gates run (all green): GM-10b `test_gm10b_offers` (20 ok), `test_gm10a_calendar` + `test_gm09a_maps` (35 ok, determinism suite unchanged), `ruff check` + `ruff format --check` (pass) on all 7 changed files.

### Findings

**1. [MINOR] The BOUNDED (tunnel) pool ordering is not locked by any exact-value test — a reorder survives the whole suite.** `src/offers.py:57-62` `_BOUNDED_POOL` is only exercised by set-membership tests (`test_tunnel_excluded_...` compares a set; `test_river_pool_can_offer_a_tunnel` checks `"TUNNEL" in kinds`); the frozen `_SEED0_SEQUENCE` only exercises the CLASSIC pool. Empirically confirmed: swapping `LOCOMOTIVE`/`CARRIAGE` in `_BOUNDED_POOL` leaves all three green (mutation survived). Fix: assert the exact pool tuples OR add a frozen river-seed-0 exact offer sequence. Not blocking: bounded ordering affects only the exact offers on river/delta/lake, has no gameplay effect in GM-10b (choosing is GM-10c).

**2. [NIT] `test_offers_regenerate_distinctly_each_week` does not isolate `week_index`** — `len(set(seq)) > 1` passes even if `week_index` were dropped, since the python_random state already differs each week. (Independently verified the frozen sequence DOES catch the week_index-drop, so it is not an actual gap — the test just over-claims its intent.)

**3. [NIT] The frozen `_SEED0_SEQUENCE` is implicitly pinned to CPython 3.13's `random.sample`** — worth a one-line comment noting the coupling (the repo pins py313).

### Claims verified as correct (with evidence)
1. **Continue-exactness — HOLDS.** `_offer_rng_for_current_week` reads `python_random.getstate()` + `week_index`; `_restore_rng` restores that exact state; derivation is `repr` → `sha256` → `int` (cross-process stable, NOT salted `hash()`). Independent stricter probe: saved mid-week-2 (steps 2000, before the 2400 boundary), reloaded, weeks 2/3/4 reproduced byte-exact.
2. **Gameplay-inertness — HOLDS.** `getstate()` read-only (probed before==after); generation last in `increment_time` behind the calendar/game-over guard. Zero save/checkpoint bytes (explicit dicts; `_exact_keys` would reject). GM-09a parity unchanged.
3. **Gating — HOLDS.** `week_calendar` default False; only `build_game`/`build_from` set it; RL/pixel/tutorial never do. `TestGM10bRLGatedOff` + `TestGM10aGating` pass.
4. **Offer model — CORRECT.** distinct sampling, `min` clamp, named `count<1` error, CLASSIC excludes TUNNEL, stdlib-only.
5. **Modal render — CORRECT.** opaque panel byte-stable; layout has no overlap at 1920x1080 even at 4 offers; `main.py` wiring + the harness fix correct.
6. **No regressions.** Only reader of `current_offers` is `main.py`'s OFFER branch; `reconcile_week_boundary` does not read it, so `_offer_controller` needs no change. Docs updated and accurately scope-limited.

Mutation checklist (a)-(h): all caught except the bounded-pool-order case (Finding 1); week_index-drop confirmed caught by the frozen sequence via independent probe.

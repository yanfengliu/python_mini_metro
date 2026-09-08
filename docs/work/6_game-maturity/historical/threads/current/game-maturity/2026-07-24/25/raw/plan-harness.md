# Adversarial PLAN review — GM-09f2 (high-score map identity, D-039) — harness general-purpose lane (agentId a30e2635fbf33423e)

**Verdict up front: REVISE.** The core design is sound — unifying both game-over paths on the real mediator, reading `map_definition` directly with fail-safe swallow-to-None, keeping the state contract stable, and keying the board on the full map identity are all correct and well-argued. But the plan's **test-surgery enumeration is materially incomplete**: implemented as written it leaves a **red unit suite** (gate failure), because the `record(deliveries)`→`record(mediator)` seam change and the `mediator.map_definition` read break spies/stubs in files the plan either mislabels "UNCHANGED" or omits entirely. Plus two under-specified spots in the migration/ranking logic.

## Findings

### MAJOR — file:many — incomplete test enumeration ⇒ red suite

The seam contract change (controller now hands the seam `self.mediator`, and `record_highscore` reads `mediator.map_definition`) breaks tests the plan does not account for. The plan's "Touched" list names only `test_gm07d_highscores.py`, `test_gm07d_recorder_controller.py`, and `test_gm07d_run_game_loop.py` ("UNCHANGED"). Concrete breaks:

1. **`test_gm07d_run_game_loop.py` is NOT unchanged.** `TestGM07dRecordHighscoreIsReadOnly.test_record_highscore_reads_deliveries_and_mutates_no_mediator_state` (:209-228) drives the **real** `main.record_highscore(SimpleNamespace(deliveries=7))` (:214/219). That stub has **no `map_definition`**, so the planned `map_definition = mediator.map_definition` raises `AttributeError` → the existing `try/except` swallows to `None`. Then :220 `assertTrue(target.exists())` FAILS and :222 `result.document["entries"][0]` raises on `None`. Order-independent. Additionally `_LoopMediator` (:39-51) also lacks `map_definition`, making the RecursionError-swallow test (:190-206) order-fragile: reading map before `load_highscores` short-circuits and `load_spy.assert_called_once()` (:205) FAILS.

2. **`test_gm07e_game_over_reconcile.py` is omitted entirely.** It defines its own local `_SpyHighscores` (:85-94) whose `record(self, deliveries)` appends the raw argument; after the seam change `deliveries_seen` holds `_DeliveringMediator` instances, failing `assertEqual(spy.deliveries_seen, [42])` (:178), `[7]` (:201), and `[5]` (:265). (Its run-loop assertion at :396-398 reading `recorded_arg.deliveries` survives.)

3. **Within `test_gm07d_highscores.py`, the helper enumeration misses `_empty_doc`.** It hard-codes `schemaVersion: 1` (:43-44); since `validate_highscores` becomes v2-only, `test_accepts_a_valid_document` (:97) will raise and `test_start_empty...` comparisons mismatch the v2 `_empty_document()`.

**Fix:** Add `test_gm07e_game_over_reconcile.py` to the touched set + update its `_SpyHighscores.record` to `record(self, mediator)` appending `mediator.deliveries`. Correct the `test_gm07d_run_game_loop.py` "UNCHANGED" claim (stubs need `map_definition`; pin load-first). Update `_empty_doc` to `schemaVersion: 2`.

### MINOR — highscores.py `_migrate_v1_document` — bool/float-unsafe v1 detection

`if schemaVersion == 1`: `True == 1` and `1.0 == 1`, so a forged `{"schemaVersion": true}` or `1.0` v1-shaped board would be migrated+accepted, contradicting the current strict `_int` rejection. Fail-open, not data-loss. **Fix:** strict int detection (reuse `_int(...) == HIGHSCORES_SCHEMA_VERSION_V1`).

### MINOR — highscores.py:144-149 — rank loop not included in the identity-key change

The plan moves `target`/`_sort_key`/cap to the triple but not the rank loop (`item["map"] == map and item["rulesVersion"] == rules_version`). Board `classic@1 [10,8]` + record `classic@2=5` → buggy rank 3/is_best False instead of 1/True. The cap-only test would not catch it. **Fix:** include `mapDefinitionVersion` in the rank predicate + add a rank-across-versions test.

### NIT — `HIGHSCORES_MAP_CLASSIC` fate + `_sort_key` annotation

Drop the main.py import/hardcode but KEEP the constant (test_versioned_constants asserts it). `_sort_key` annotation → `tuple[str, int, str, int]`.

### NIT — "mirrors the save" loosely stated

The save is version-aware-accept-both with construction-time synthesis + a `resolve_map` guard; the plan is migrate-then-validate-v2-only with no `resolve_map` guard. Both valid; note the deliberate asymmetry rather than implying a strict mirror.

## Attack items with NO finding (verified sound)
1. Seam change / MAJOR-3 / both paths agree — correct and improved; passing the whole mediator is REQUIRED to preserve MAJOR-3 (a tuple would force the controller to read `map_definition`). 2. Direct `mediator.map_definition` read, swallow to None — correct fail-safe; rejecting `or classic` is consistent with GM-09f. 3. stateContract stable — correct. 4. mapDefinitionVersion in the key — correct, not over-engineering. 5. cross-key isolation — correct (subject to the rank-loop MINOR). 6. blast radius — highscores stays gameplay-free; no committed highscores fixture; `record_score` has no other caller. 7. ordering — safe and correct; no non-classic map reaches the recorder before GM-09f3.

## Disposition: **REVISE**
One MAJOR (red suite from incomplete/incorrect test enumeration) + two MINOR correctness gaps (migration predicate, rank loop). All fixes bounded and local; no design rework needed.

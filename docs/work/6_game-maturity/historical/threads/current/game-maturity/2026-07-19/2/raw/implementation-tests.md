# GM-03f implementation process and test review messages

The following reviewer payloads are preserved verbatim in emission order.

Review in progress; 17 new tests pass. Concrete undercoverage found: direct `try_purchase_path_button_by_index` only asserts a stubbed `True` and never checks selected live button (`test_input_coordinator.py:231-236`, Host stub logs but always succeeds at support:174-180), so wrong-index/bool dispatch mutants survive; `is_speed_button_active` is tested only once for unpaused `speed_4` (`test_input_coordinator.py:405`) while legacy renderer tests inject a stub, leaving pause/speed_1/speed_2/unknown truth table unprotected. Also implementation docs/review are changing concurrently; I’m checking final differential coverage and stale claims before final findings.

Re-review: your index identity/bool/implicit/bounds assertions and full active-state truth table are good. Remaining substantive test gaps: a line trace of the entire discovered suite (577/577 green) still never executes coordinator outcomes at `src/input_coordinator.py:160` (price hook None), `:171` (implicit next index None), `:221` (nonterminal click), `:264` (locked-button mouse purchase), `:338/:340` (apply_speed_action speed_1/speed_2), `:382` (remove_path without selector), or `:391` (unknown string action). Differential covers 221/264/391, but not 160/171/338/340/382, and unittest/CI will not guard any of the eight. Add direct mutation-sensitive cases, likely split into another test file because `test_input_coordinator.py` is already 487 lines. Also PLAN promises late entity-type lookup and live-list replacement, but facade/diff only patch Station/PathButton/SpeedButton/Button before calls (`test_mediator_input_contract.py:277-318`, differential input:90-94,136-143); no hit-test callback rebinds those types, and no contains callback replaces `host.buttons` between station and button loops. Eager type capture or collection pre-capture would false-green. Recommend one facade/differential rebind scenario plus one direct live-list timing case.

One high-confidence reproducibility finding: the checked-in facade contract is no longer baseline-runnable. `test/test_mediator_input_contract.py:16-19` unconditionally evaluates `mediator_module.InputCoordinator()`, but baseline `7ff9d9c` has no `InputCoordinator` symbol (`git grep` finds none). Thus the documented claim that the 9 facade characterizations pass against the unextracted baseline cannot be replayed from the final test artifact (8 tests calling `bare_mediator` would AttributeError). Make `bare_mediator` conditionally install `_input` only when the symbol exists, as differential support already does at `scripts/input_coordinator_differential_support.py:86-93`, then actually replay the final facade file against an archived baseline and candidate. This is substantive evidence/TDD quality, not just stale wording.

Final live code/test re-review is semantically clean: 22/22 focused pass, every executable InputCoordinator body statement is now hit by the full discovered 582-test suite, and all new files remain <500 (edge 126, facade 427, direct 487, component 391, verifier max 308; Mediator 605<625). One remaining process finding: durable docs are now materially stale after the accepted fixes. `EVIDENCE.md:529-533` still says facade 9/9, focused 17/17, full 577, exact RL 580, five changed Python files, and differential unfinished; `REVIEW.md:3,21` repeats those counts/statuses; `PLAN.md:3` says pre-production characterization active; `STATE.md:11,23-24` says plan/TDD/implementation remain the resume work. Current facts are facade 10/10 baseline+candidate, focused 22/22, core 582 (independently green; 12 skips), exact-RL must be rerun/recorded as likely 585 rather than inferred, differential/clean-checkout complete, implementation review converged. Refresh those surfaces and rerun exact RL before claiming final validation; after that I expect CLEAN.

CLEAN.

Final live review confirmed:

- Focused direct/edge/facade suite: 22/22.
- Full discovered suite: 582 tests; every executable `InputCoordinator` body statement exercised.
- Exact RL: 585/585.
- Differential: 4 cases, 16 records, 90 events; baseline/candidate/expected bytes match.
- All new Python files remain under 500 lines; `Mediator` is 605, below its 625 ceiling.
- Baseline facade replay, late type resolution, live-list timing, short-circuit branches, and durable documentation are corrected.
- `git diff --check` passes.
- No task-owned processes or temporary artifacts remain.

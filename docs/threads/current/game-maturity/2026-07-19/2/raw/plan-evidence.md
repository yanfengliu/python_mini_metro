# GM-03f process and evidence plan review messages

The following reviewer payloads are preserved verbatim in emission order.

GM-03f plan audit has substantive findings: (1) TDD order is wrong—PLAN steps 2-3 implement/direct-green before step 4 adds facade signature/effect characterization, so wrapper compatibility tests never prove baseline-green; move/add/run them before production. (2) clean-checkout byte equality is not Windows-portable yet: core.autocrlf=true and `.gitattributes` has rules only for iteration 1; proposed iteration-2 artifact/summary paths currently resolve `text/eol: unspecified`. Freeze exact LF rules and an external-output clean-checkout replay. I’m finishing exact regression-scope/measurability checks.

Re-review: TDD order, LF attributes, dict-subclass wording, and size ceiling are corrected. Two remaining process findings: (1) PLAN lines 9/48/53 still give only category labels plus 75/156 counts, not the exact unittest module command; counts alone do not freeze regression scope. Record the exact 75- and 156-test module lists/commands used. (2) differential line 52 still lacks mechanical isolation/drift/cardinality requirements. Add separate bytecode-disabled children, target-module origin assertions, pre/post runtime+verifier hashes, canonical schema/scenario plus nonzero fixed case/record/event cardinality assertions, and exact baseline/candidate/expected byte+digest reporting. External output + LF fixes raw checkout portability, but without these guards `--expected` can pass while ignored pycache/source/verifier drift or scenario shrinkage goes undetected.

Likely exact scopes from the live test counts (and they sum exactly): 75 = test_gameplay(16), test_mediator_interaction(12), test_game_renderer(13), test_game_clock(14), test_main(3), test_headless_render(1), test_player_env(16). 156 = those plus test_mediator_progression(19), test_network_progression(8), test_mediator_path_contract(10), test_mediator_path_failure_contract(7), test_mediator_paths(8), test_path_lifecycle(10), test_render_layout(10), test_render_purity(3), test_spawn_cadence(6). Please confirm against the command actually run rather than trusting my reconstruction.

Final re-review is substantively clean on TDD, exact 75/156 scopes (the listed modules sum correctly), differential isolation/cardinality/digests, LF/core.autocrlf replay, cursor, boundary, and 735−228+43≈550 line math. One process wording gap remains if you want literal AGENTS parity: PLAN line 44 only keeps generic handwritten files below the 1,000 hard ceiling, while AGENTS says target under 500 and split rather than grow. Require each new test/support/verifier file below 500 (or explicitly justify any >500) so the acceptance doesn’t normalize the hard ceiling.

CLEAN.

Verified:

- TDD order now characterizes the 19 facade methods against baseline before the import-only red and production work.
- Exact 75- and 156-test commands sum correctly.
- Differential acceptance now fixes isolation, module origins, drift hashes, cardinalities, byte lengths, SHA-256 digests, and external-output clean-checkout replay.
- Exact iteration-2 artifact paths resolve to `text eol=lf` under `core.autocrlf=true`.
- `735 - 228 + 43 ≈ 550` supports the ≤600 target and 625 hard ceiling without adjacent scope theft.
- New Python files must split before 500 lines.
- Parent cursor/evidence correctly advance from green GM-03e Commit B into `[GM-03f:A]`.
- `git diff --check` passes. No files edited by this reviewer.

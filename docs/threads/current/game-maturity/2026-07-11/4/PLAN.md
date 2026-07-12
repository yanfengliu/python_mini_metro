# GM-01c threshold and replay migration plan

Status: Commit A remotely green; Commit B staging in progress

## Intent

Replace the one-overdue-passenger failure cliff with an initial default threshold of two while preserving exact historical replay. One overdue station passenger remains a visible warning and the second ends a default game. This is an initial directional balance correction backed by the existing paired-seed baseline, not a claim of final game balance.

## Non-negotiable contracts

- `config.overdue_passenger_threshold = 2` becomes the canonical repository default while the imported module symbol `config.max_waiting_passengers` remains as a deprecated value alias. `Mediator.overdue_passenger_threshold` is the canonical runtime field; writable `Mediator.max_waiting_passengers` remains a compatibility property over the same value. The public runtime alias does not add new validation or change legacy zero/negative assignment behavior in this migration. Tests pin both config imports and both runtime assignment directions.
- Only station passengers at or above the inclusive wait boundary count. Metro riders remain excluded. Explicit threshold `1` preserves the old one-passenger terminal behavior.
- Checkpoint schema stays at v2 because it already records both `overdue_passenger_threshold` and `max_waiting_passengers`, normalizes v1 from the legacy field, and rejects v2 disagreement.
- Recursive scenario/input schemas use immutable named v1, v2, and v3 identifiers and an explicit supported-version set; advancing the current alias to v3 must not erase literal v2 routing. V1 reconstructs line-credit-delta reward plus threshold `1`; v2 preserves its required deliveries reward plus threshold `1`; v3 requires positive non-boolean integer `overduePassengerThreshold` and preserves its required deliveries reward. Required-key selection, normalization, and recorded-input reconstruction dispatch explicitly by version rather than by equality with the mutable current alias. Scenario schema and checkpoint schema are decoupled: v1 emits checkpoint v1, while v2/v3 emit checkpoint v2.
- Agent-play schemas likewise retain immutable named v1, v2, and v3 identifiers and explicit routing for all three. Schema-less/v1 and literal v2 records reconstruct threshold `1`; new v3 captures record the post-reset environment value, normally `2`. Replay selects the historical threshold, calls `env.reset`, then applies the selected threshold to the replacement mediator before yielding the initial observation or stepping. Supplied factories and zero-argument factories follow that same order.
- Pixel protocol v1, the single-frame task descriptor/fingerprint, action and observation spaces, reward modes, manifest schemas, terminal-metrics-v1 keys, and the legacy meaning of `display_score` do not change. The runtime edit intentionally changes only the environment-content fingerprint; old models remain fail-closed unless the existing explicit content-drift opt-in is used.

## TDD sequence

1. Add focused red runtime tests for default `2`, bidirectional alias assignment, inclusive first/second overdue behavior, explicit legacy threshold `1`, metro-rider exclusion, and reset restoring the configured default. Update the existing terminal-over-horizon pixel test to set threshold `1` explicitly and add a default-two pixel termination case.
2. Extend checkpoint tests: fresh v2 emits `2/2`; canonical or legacy mutation remains equal; genuine v1 threshold `1` normalizes without mutation; v2 disagreement remains fail-closed.
3. Add red recursive-contract tests for strict v3 scenario/input keys and positive non-boolean threshold validation. Pin genuine v1 and literal pre-GM-01c v2 reconstruction at threshold `1`, new v3 at `2`, explicit v2/v3 reward routing, scenario-to-checkpoint mapping, zero-argument factories, inputs-mode replay, and fresh-process public verification. A custom reset that replaces the mediator must prove the threshold is applied after reset and before the initial checkpoint/operation. Preserve a literal v2 fixture when the default checked-in scenario advances to v3. Update both `test/playtest-verify.test.mjs` and the schema assertion in `test/playtest-recursive.test.mjs`.
4. Add red agent-play tests for schema-less/v1 and literal v2 threshold-one reconstruction, v3 default/explicit capture, application after a replacement-mediator reset for supplied and constructed environments, and malformed/missing v3 values failing closed.
5. Implement the smallest runtime and schema changes that satisfy those tests. The pre-existing `src/mediator.py` and `test/test_mediator.py` hard-ceiling violations remain a deliberate temporary exception owned by GM-03: GM-01c may add only minimal default/alias plumbing to the mediator, adds no tests to the oversized mediator test, and introduces no unrelated refactor. Do not add to the 498-line `src/recursive_checkpoint.py`; put new recursive v3 cases in a focused new test module if `test/test_recursive_playtest.py` would cross 500 lines, and keep every other touched source/test file below 500 lines.
6. Update `GAME_RULES.md`, `README.md`, architecture, progress, state, evidence, and recursive fixture docs. Rerun the exact paired 12-seed thresholds 1/2/3 baseline and a default-versus-explicit-two equivalence check, retaining its static-route limitations.

## Expected files

- Runtime: `src/config.py`, `src/mediator.py`.
- Persisted replay: `src/recursive_contract.py`, `src/recursive_playtest.py`, `src/agent_play.py`, `scripts/playtest-verify.mjs`, and the checked-in recursive fixtures.
- Tests: a new focused threshold module plus targeted mediator/env/player/checkpoint/recursive/agent-play and Node verifier tests.
- Docs/evidence: public rules/API wording and this iteration's diff, raw reviews, review synthesis, baseline evidence, and parent state ledger.

## Review and validation

- Before runtime edits, three independent live-code plan reviewers must try to refute runtime semantics, persisted compatibility, and scope/test completeness. Multi-CLI review follows the repository runbook; unavailable services are recorded and compensated without bypass.
- After implementation, three independent finder/refuter lanes review the live diff and all grounded findings are fixed and re-reviewed.
- Focused red/green tests precede full core and exact-RL `python -m unittest -v`, full Ruff/format, changed-file pre-commit, dummy-video app smoke, and fingerprint checks. Every new/affected Node test must pass locally. Full local `npm test` must be reverified with exactly the same 19 known civ-engine pin failures unless the external sibling state changes; record the observed pass/total count after adding tests rather than freezing the old total. Pinned CI must pass the complete updated Node suite plus build/RL smoke until GM-04 supplies the isolated local 2.2.0 pin.
- Commit A contains implementation/tests/docs/evidence and waits for green remote CI. Commit B records its exact SHA/run, waits for its own CI, and only then starts GM-02.

## Acceptance

- A fresh default game ends on the second overdue station passenger, never the first; explicit threshold one preserves old behavior.
- Both alias directions and every persisted format reconstruct one authoritative threshold without disagreement.
- Genuine pre-change recursive v1/v2 and agent-play v1/v2 evidence replays under threshold one; new v3 evidence records/replays threshold two.
- Protocol and task hashes are unchanged and the content hash changes intentionally. All applicable local gates and all pinned remote gates pass; the only allowed local exception is the reverified 19-test Node pin mismatch recorded above. The threshold baseline is reported as directional rather than final balance proof.

# Game maturity decision log

## D-001 - Repository-backed persistence

Decision: `PLAN.md` is the durable scope and acceptance contract; `STATE.md` is the sole resume cursor; `DECISIONS.md` prevents design drift; `EVIDENCE.md` records verification. All four are committed and updated incrementally.

Reason: chat context and active-process state are not sufficient evidence for a multi-session effort. The repository must say what is complete, what remains, and exactly where to resume.

## D-002 - Deliveries and currency are separate concepts

Decision: `Mediator.deliveries` is the canonical cumulative objective and `Mediator.line_credits` is the spendable balance. A delivery increments both; a purchase subtracts only line credits. `total_travels_handled` remains a compatibility property alias to deliveries and `score` remains a deprecated compatibility property alias to line credits, so callers that fund purchases by assigning `score` do not silently change meaning.

Reason: the current HUD and game-over overlay call remaining spendable currency `score`, while the user and RL objective define success as total passengers delivered. One value cannot truthfully represent both after a purchase.

Status: accepted implementation contract after adversarial plan review.

## D-003 - Longer history must be temporally meaningful

Decision: the fresh policy will receive more than eight frames, but the implementation will not blindly multiply contiguous RGB frames. It will preserve immediate interaction context and add older snapshots through a manifest-bound history layout selected after resource profiling.

Reason: eight consecutive 10 Hz frames cover only 0.8 seconds. Doubling contiguous frames covers 1.6 seconds while roughly doubling rollout observation memory, which is still too short for route and reroute planning. Recurrent state remains necessary for episode-long memory.

Candidate: `decision-history-v1` with twelve oldest-to-newest offsets `[128, 64, 32, 16, 7, 6, 5, 4, 3, 2, 1, 0]`, zero-filled missing history, and explicit channel ordering. This keeps the current eight recent 10 Hz frames and adds anchors through 12.8 seconds at 1x, while the LSTM carries episode-long memory. The candidate produces 36 input channels and a 729 MiB raw 8-environment x 128-step rollout payload; promotion remains contingent on a measured process-tree profile against 8-contiguous and 8-multiscale controls.

Status: accepted implementation candidate; final fresh-default promotion is pending GM-02 profiling and review.

## D-004 - Product features share one simulation

Decision: menus may wrap sessions, but route editing, resources, maps, upgrades, saves, manual controls, structured actions, recursive play, and pixel RL must all drive one canonical gameplay model.

Reason: parallel feature implementations would invalidate determinism, tests, and the claim that the pixel policy faces the same game as a player.

## D-005 - Compatibility before decomposition

Decision: complete the score/reward and history-contract migrations before splitting `Mediator`, then keep `Mediator` as a facade over composed collaborators.

Reason: doing the same contract migration across temporary and final module boundaries would increase risk and make artifact fingerprint changes harder to reason about.

## D-006 - Initial overload-pressure correction

Decision: rename the mechanic around an explicit overdue-passenger threshold, use two as the initial default, and retain `max_waiting_passengers` as a compatibility alias. One overdue passenger warns but does not end a default game; the second ends it. An explicitly configured threshold of one preserves the old behavior.

Reason: two is the smallest change that removes the current one-passenger failure cliff while retaining visible time pressure. The scripted paired-seed evidence was independently reproduced and remains directional only; GM-11 still owns final balance tuning from broader human and policy evidence.

## D-007 - Two-commit remote finalization

Decision: each independently green work unit uses implementation Commit A followed, after green CI, by metadata Commit B that records A's SHA/CI and advances the resume cursor. Commit messages carry exact `[<work-unit>:A]` and `[<work-unit>:B]` markers; B is located as the newest commit that changed the goal's `STATE.md` with the expected marker. Commit B is pushed and its CI must be green before new implementation starts; a later session queries B's CI and reopens the unit if it failed. Failing TDD tests are working-tree phases inside a work unit, not remotely finalized commits.

Reason: a local cursor advanced only after CI is not durable on `origin/main`, while endlessly committing the latest metadata CI result has no terminal transaction.

## D-008 - Explicit persisted-schema compatibility

Decision: GM-01 adds checkpoint schema v2 plus v1 normalization, recursive input schema v2 with explicit reward contract and legacy v1 score-delta replay, versioned agent-play records, writable compatibility aliases, and reconstructable pixel terminal-metrics versions. GM-02 adds manifest v2 with a separate validated history fingerprint while retaining the single-frame task fingerprint and arbitrary v1 contiguous stacks.

Reason: source/content drift flags cannot repair a protocol or persisted-document schema that the loader no longer understands.

## D-009 - Runtime selections belong to task identity

Decision: map ID and map-definition version will be included in RL task identity, manifests, train/resume/evaluate CLI reconstruction, saves, and high-score keys. Task descriptors and fingerprints become explicitly versioned; genuine legacy artifacts reconstruct and hash the exact pre-map descriptor rather than inserting fields and expecting the old hash to match.

Reason: hashing source code does not distinguish two maps selectable from the same revision.

## D-010 - Pause reasons precede modal product systems

Decision: GM-07a replaces internal boolean-only pause ownership with explicit pause reasons while retaining the `is_paused` compatibility facade. Menus/save, tutorial, and weekly choices build on that established contract.

Reason: introducing pause reasons only with weekly progression would force save and tutorial schema migrations and could let the Space key dismiss a non-manual modal pause.

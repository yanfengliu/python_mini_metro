# Game maturity and long-horizon RL plan

Status: active

Goal thread: `019f5286-dfca-75e1-9e79-58719dbe1efb`

## Objective

Evolve `python_mini_metro` from a stable playable alpha into a coherent, maintainable game and a validated long-horizon RL testbed. Work proceeds as independently shippable increments; each increment uses TDD, updates player and architecture documentation, passes the relevant local gates, receives adversarial review proportional to risk, commits directly to `main`, pushes, and verifies remote CI before the next increment begins.

## Durable resume contract

1. At the start of every continuation, read `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, `README.md`, `GAME_RULES.md`, this `PLAN.md`, `STATE.md`, `DECISIONS.md`, and `EVIDENCE.md`.
2. Treat `STATE.md` as the exact resume cursor. Continue the single item marked `in_progress`; do not restart completed increments or skip ahead to a dependent feature.
3. Confirm `git status --short --branch`, preserve unrelated changes and the untracked `.agents/` directory, and compare local `main` with `origin/main` before editing.
4. Begin behavior changes with a failing test. Preserve existing public APIs through aliases or explicit versioned migrations unless an acceptance criterion deliberately changes a contract.
5. Every independently shippable work unit uses a two-commit remote transaction. Design phases and failing TDD tests may exist in the working tree but are never finalized as deliberately red commits. Commit A contains the green implementation, tests, affected public docs, provisional evidence, and sets the cursor to `awaiting-implementation-ci`; its commit message includes `[<work-unit>:A]`. Push A and wait for its required CI. Commit B records A's exact SHA and CI URL/result, marks the work unit complete, advances the cursor, and has commit marker `[<work-unit>:B]`; push B and wait for B's CI before starting the next work unit. Locate B as the newest commit that changed the goal's `STATE.md` and carries that exact marker. A later session must query B's CI before trusting its completed cursor; if B failed, reopen the work unit instead of advancing. Commit B needs no third metadata commit.
6. Keep raw high-risk reviewer output under this iteration's `raw/` directory and synthesize findings in `REVIEW.md`. Verify every reviewer claim against live code before acting.
7. This thread remains under `docs/threads/current/` until every acceptance criterion is satisfied. When the whole goal is complete, move or merge it into `docs/threads/done/game-maturity/`.

## Global invariants

- The canonical performance objective is total passengers delivered before game over.
- Spendable progression currency is distinct from lifetime deliveries; UI, structured observations, pixel terminal metrics, scripted play, and evaluation must name both unambiguously.
- Manual play, `MiniMetroEnv`, `PlayerPixelEnv`, deterministic recursive play, save/resume, and replay use the same gameplay mechanics rather than parallel implementations.
- Pixel policies receive only player-visible pixels and player-equivalent controls. Privileged state remains restricted to tests, curriculum generation, and verification.
- Saved artifacts fail closed on incompatible game, observation, action, reward, runtime, or trainer changes.
- Every persisted or replayed document has an explicit schema/version and a tested legacy normalization or a deliberate fail-closed migration boundary; adding a field is not treated as backward compatible by accident.
- Every runtime-selected task dimension that changes gameplay, including map identity and definition version, is part of task identity, manifests, CLI reconstruction, resume/evaluation validation, saves, and high-score keys.
- A larger visual history must span strategically meaningful time without silently creating an unsafe rollout-memory default.
- Rendering remains observational and deterministic; headless operation remains display-independent.
- No handwritten source or test file may remain over the 1,000-line hard ceiling when the goal closes; new files target fewer than 500 lines.
- No feature is called complete from a code diff alone: behavior needs tests, executable evidence, and for recursive findings a rerun proving the bug class absent.

## Increment roadmap

### GM-00 - Persist and review the roadmap

Dependencies: none.

Acceptance:

- The active thread contains this plan, a resume cursor, a decision log, baseline evidence, review prompts, raw reviews, and a synthesized `REVIEW.md`.
- Codex and Claude are asked to verify the plan against live symbols and contracts; unavailable reviewers are recorded and available feedback converges with no unresolved high- or medium-severity plan defect.
- The persistence increment is committed and pushed before gameplay implementation begins.

### GM-01 - Make deliveries canonical and repair baseline rules

Dependencies: GM-00.

Scope:

- Introduce `Mediator.deliveries` as the canonical cumulative objective and `Mediator.line_credits` as the spendable balance. A delivery increments both; a purchase subtracts only credits.
- Retain `total_travels_handled` as a property alias to deliveries and `score` as a deprecated property alias to line credits, then migrate internal code, observations, checkpoints, recursive oracles, agent-play records, render text, and tests to the explicit names.
- Make `MiniMetroEnv` reward newly delivered passengers so structured and pixel learning surfaces optimize the same objective; retain any legacy score-delta experiment only as an explicitly named opt-in contract.
- Correct the passenger spawn cadence documentation to the live 900-step base randomized to 70-130 percent, or deliberately rebalance the constant and tests before documenting the new value.
- Rename the game-over count to an explicit overdue-passenger threshold and start from a default of two, retaining `max_waiting_passengers` as a compatibility alias. Verify the threshold against a reproducible paired-seed scripted baseline and do not claim that this first value is final human-balance evidence.
- Give all three legacy aliases writable setters because current tests and callers assign them directly.
- Introduce checkpoint schema v2 with explicit deliveries, line credits, and overdue threshold plus a v1 normalizer used by verification so historical transcripts do not become false nondeterminism failures.
- Introduce recursive scenario/input schema v2 with an explicit environment reward contract. Replaying v1 inputs reconstructs the legacy spendable-score-delta reward, while v2 defaults to deliveries; transcript comparison and reward oracles use the selected contract. Acceptance includes a genuine v1 successful-line-purchase transcript whose negative legacy reward still verifies.
- Introduce versioned agent-play records with explicit per-step/final deliveries and line credits while retaining the old return value and `score`/`final_score` fields during a deprecation window; add a separately named canonical delivery-returning entry point rather than silently changing legacy callers.
- Keep pixel terminal-metrics v1 reconstructable for old manifests. A terminal-metrics v2 may add explicit `line_credits`, but manifest reconstruction must select the saved metrics version so old artifacts remain evaluable with the existing content-drift opt-in after HUD changes.

Acceptance:

- Purchasing a line cannot reduce lifetime deliveries or the final delivered-passenger total.
- The HUD displays `Passengers Delivered` and `Line Credits`; the game-over primary result is deliveries and remaining credits are secondary.
- Both environment rewards telescope to total deliveries under the default reward mode.
- Checkpoint/replay determinism and old observation consumers remain covered by compatibility tests.
- Direct assignment through all legacy aliases, v1 checkpoint normalization, v1/v2 agent-play replay, old pixel terminal-metric reconstruction, and purchase-only zero default reward are acceptance-pinned.
- `GAME_RULES.md`, `README.md`, and RL objective metadata agree with code.

Work units: GM-01a uses TDD to introduce canonical deliveries/credits plus writable aliases, structured reward modes, checkpoint/recursive-input/agent-play/terminal-metric schema compatibility, and genuine v1 regressions in one green transaction; GM-01b updates HUD, game-over presentation, public docs, and the verified spawn cadence; GM-01c introduces and scenario-tests the explicit baseline overload-pressure rule.

### GM-02 - Increase strategically useful visual history

Dependencies: GM-01.

Scope:

- Increase the fresh-run observation history beyond eight frames.
- Prefer a tested multi-timescale or dilated history that preserves recent pointer/motion frames while adding route-state snapshots across seconds or tens of seconds; do not assume a larger contiguous stack alone provides long-term planning.
- Start from the concrete `decision-history-v1` candidate with twelve oldest-to-newest RGB offsets `[128, 64, 32, 16, 7, 6, 5, 4, 3, 2, 1, 0]`. At the default 10 Hz decision rate this preserves the current eight recent samples and adds 1.6, 3.2, 6.4, and 12.8-second anchors; at 4x game speed the oldest visible anchor spans 51.2 simulated seconds. The LSTM remains responsible for episode-long memory.
- Record history layout, sample ages, channel order, and reset/terminal semantics in the task and training manifests so resume/evaluation cannot silently reinterpret channels.
- Give the canonical history descriptor its own `historyFingerprint` in manifest v2 and validate it separately from the unchanged single-frame task fingerprint. Add the temporal wrapper module to the closed training-source hash allowlist.
- Preserve LSTM state across decisions and reset it at episode boundaries.
- Benchmark at least two candidate history layouts on identical 8-environment x 128-step CPU rollouts; choose a fresh default only after reporting wall time, FPS, process-tree RSS, raw observation payload, and trainable parameter count.

Acceptance:

- The default supplies more than eight frames and spans at least one meaningful rerouting horizon while retaining immediate click/drag context.
- Reset, episode boundary, terminal observation, timeout bootstrap, resume mismatch, and legacy arbitrary contiguous-stack artifact tests pass for at least N=1, 4, 8, and another valid N.
- Staggered resets across multiple vector slots prove rings cannot leak across environments or episodes, and genuine pre-history artifact bytes remain covered rather than being regenerated only through the new wrapper.
- The selected default stays within a documented local memory ceiling or reduces another rollout dimension transparently to remain safe.
- README, architecture, model-selection research, manifests, CLI help, and CI smoke tests describe and exercise the new history contract.

Substeps: GM-02a adds the immutable history descriptor, manifest-v2 migration, and v1 normalization; GM-02b implements the vectorized temporal ring with synthetic chronology/reset/terminal tests; GM-02c integrates CLI, training, evaluation, recurrent timeout bootstrap, and legacy artifact compatibility; GM-02d profiles 12-multiscale against 8-contiguous and 8-multiscale controls before promoting the safe fresh default.

### GM-03 - Split the mediator and its tests

Dependencies: GM-01 and GM-02, so early contract changes are not duplicated across temporary boundaries.

Scope:

- First split `test/test_mediator.py` by behavior with shared fixture helpers.
- Keep `Mediator` as the compatibility facade while extracting composed path/progression, passenger-flow, route-planning, and input coordination boundaries that match actual responsibility clusters.
- Avoid inheritance and avoid moving state into duplicate representations.

Substeps: GM-03a splits mediator tests behind shared fixtures; GM-03b extracts progression and purchase ownership; GM-03c extracts pure route planning; GM-03d extracts topology and path lifecycle; GM-03e extracts passenger spawning and flow; GM-03f extracts input/layout coordination and leaves `Mediator` as a compatibility facade. Move one ownership cluster at a time and run focused plus full gates after every move.

Size trajectory: GM-03b's explicit compatibility properties may temporarily grow `src/mediator.py` from its 1,112-line baseline to 1,193 lines while establishing single ownership. GM-03c must reverse that trajectory and finish below the 1,112-line baseline; GM-03d must cross below 1,000 lines. GM-03e and GM-03f continue toward the practical under-500 target without hiding behavior in magic delegation.

Acceptance:

- By GM-03d, `src/mediator.py` is under 1,000 lines; by GM-03 completion, it and every resulting handwritten file are under 500 lines where practical and always under 1,000.
- Existing public `Mediator` methods retain behavior unless a separately accepted contract change says otherwise.
- Full gameplay, deterministic replay, rendering, structured environment, and pixel environment tests pass unchanged or with semantics-driven updates already approved in GM-01/GM-02.

### GM-04 - Make local recursive tooling reproducible

Dependencies: GM-00.

Scope:

- Provide an isolated, documented way to obtain and use the pinned civ-engine runtime without mutating an unrelated sibling checkout.
- Ensure local commands and CI resolve the same engine version, commit, and runtime digest, while preserving fail-closed provenance checks.

Acceptance:

- A clean documented setup from the current machine state runs all 41 Node contract tests against the pin.
- A mismatched live sibling still fails with an attributable message rather than producing misleading downstream failures.
- No generated dependency worktree or credentials are committed.

Substeps: GM-04a defines the isolated pin location and provenance contract; GM-04b adds the setup/verification command without mutating `../civ-engine`; GM-04c proves the complete current Node suite passes at the pin and mismatch diagnostics remain attributable.

### GM-05 - Add route editing

Dependencies: GM-03.

Scope:

- Support extending, shortening, and rerouting an established line without deleting the whole line.
- Define deterministic behavior for loops, duplicate stations, metros on removed segments, onboard transfer plans, and passenger replanning.
- Add equivalent manual and structured API actions; low-level pixel policies continue to use player events.

Substeps: GM-05a adds an atomic programmatic `replace_path` transaction with rollback; GM-05b adds selected-line redraw through real mouse gestures while preserving line identity, color, fleet, and progress on retained station pairs; GM-05c adds ergonomic endpoint extension/shortening and interior insertion handles. Reject unsafe edits rather than teleporting a metro; replan waiting passengers immediately and onboard passengers at their next alight.

Acceptance:

- A player can edit line endpoints and interior route order with clear visual feedback.
- Metros and passengers transition without invalid references, teleportation, lost riders, or stale plans.
- Replay/checkpoint equality and route-edit regressions cover linear and loop lines.

### GM-06 - Add fleet and carriage resource management

Dependencies: GM-03 and GM-05.

Scope:

- Replace automatic one-metro-only assignment with an explicit inventory and assignment model.
- Add movable locomotives and capacity-expanding carriages, with deterministic assignment and removal rules.
- Expose player controls and structured actions without privileged pixel-policy shortcuts.

Substeps: GM-06a adds a conserved locomotive inventory; GM-06b adds assign, queued-unassign, and redistribution controls/actions; GM-06c adds carriage entities, capacity, attachment, and rendering; GM-06d hardens occupied-train, detachment, and line-removal edge cases so resources and riders cannot disappear.

Acceptance:

- Players can assign, remove, and redistribute available fleet resources among lines.
- Capacity, stop timing, rendering, observations, and checkpoints reflect carriage composition; GM-07 owns the first save schema and must include the completed fleet state.
- Resource conservation invariants and line-removal edge cases are tested.

### GM-07 - Add application shell and persistence

Dependencies: GM-03 and stable state schemas from GM-05/GM-06.

Scope:

- Add title, pause, settings, and game-over navigation states.
- Add versioned atomic save/resume for complete deterministic game state and a durable local high-score table keyed by map/rules version.
- Keep automated/headless entry points able to bypass menus explicitly.

Work units: GM-07a extracts an `AppController`, explicit screen states, and an internal pause-reason model from `main.py`/the boolean-only pause path while retaining the `is_paused` facade; GM-07b adds strict versioned JSON snapshot roundtrips at clock-reset-safe boundaries, including pause reasons; GM-07c adds atomic autosave, Continue, and menu integration; GM-07d adds high scores keyed by map and rules version and ranked by lifetime deliveries rather than credits. `recursive_checkpoint.py` may inform coverage but remains a one-way verifier rather than becoming an unsafe loader. GM-08 tutorials and GM-10 progression consume the established pause-reason contract so Space cannot bypass modal state.

Acceptance:

- Save then load produces the same canonical checkpoint and subsequent seeded trajectory.
- Save/load preserves every public entity ID used by structured actions, including path IDs, and a pre-save ID remains valid for the corresponding post-load action. UUID-free canonical checkpoint equality supplements rather than replaces this assertion.
- Interrupted writes retain the previous valid save.
- Menus, pause, restart, exit, and headless modes have deterministic tests.

### GM-08 - Add tutorial, settings, and audio

Dependencies: GM-07.

Scope:

- Add an interruptible tutorial covering routes, reroutes, line purchases, fleet resources, overload pressure, pause, and speeds.
- Add persisted settings for window/display, audio levels, and accessibility-relevant presentation options.
- Add lightweight licensed or original audio with a headless-safe no-device path.

Substeps: GM-08a adds a typed settings store with malformed-file fallback; GM-08b adds gameplay domain events plus mixer and `NullAudio` consumers; GM-08c adds a deterministic tutorial state machine driven entirely by real controls and events.

Acceptance:

- A first-time player can complete the tutorial entirely through real controls.
- Settings survive restart and malformed settings fail safely to defaults.
- Audio initialization failure cannot prevent gameplay or tests.

### GM-09 - Add maps and geographic constraints

Dependencies: GM-03, GM-05, and GM-07.

Scope:

- Introduce versioned map definitions with station regions, rivers or other obstacles, and crossing resources such as tunnels/bridges.
- Keep procedural station spawning deterministic within map constraints.
- Add `map_id` and `map_definition_version` to the structured session contract, RL `TaskSpec`, task fingerprint, training manifest, CLI train/resume/evaluate reconstruction, save schema, and high-score key. Introduce an explicit task-descriptor/fingerprint version: genuine pre-map manifests reconstruct and hash the exact legacy descriptor bytes, while new manifests use the map-bound descriptor. Resume and evaluation tests use genuine pre-map manifest bytes rather than recomputing them through current code.

Work units: GM-09a adds versioned task-descriptor identity and a `Classic` map definition that preserves current behavior; GM-09b adds terrain/station regions and the first river map; GM-09c adds deterministic crossing intersection, tunnel consumption, refunds, and route-edit integration; GM-09d adds the second map; GM-09e adds the third map; GM-09f performs menu/save/high-score/RL-task integration and reconciliation.

Acceptance:

- At least three meaningfully different maps are selectable and save/high-score compatible.
- Route creation and editing enforce geographic constraints and consume/refund crossing resources deterministically.
- Pixel rendering, structured observations, checkpoints, and tests represent map identity and crossings.

### GM-10 - Add weekly progression and upgrade choices

Dependencies: GM-06 and GM-09.

Scope:

- Add deterministic calendar progression and periodic choices among lines, locomotives, carriages, crossings, or capacity-related upgrades.
- Separate lifetime delivery score from all spendable or inventory resources.

Work units: GM-10a adds a simulation calendar using GM-07's pause-reason model; GM-10b generates deterministic eligible two-choice offers from a dedicated RNG stream; GM-10c adds modal and structured choice controls; GM-10d adds line upgrades; GM-10e adds locomotive upgrades; GM-10f adds carriage upgrades; GM-10g adds tunnel upgrades; GM-10h reconciles persistence/replay and progression documentation across all upgrade families. Space cannot dismiss a progression modal.

Acceptance:

- Time boundaries pause for an explicit player choice and resume without simulation backlog.
- Offered choices, inventory changes, saves, checkpoints, and replays are deterministic from the session seed.
- Upgrade choices are accessible through manual and structured controls.

### GM-11 - Balance and playtest the complete loop

Dependencies: GM-05 through GM-10.

Scope:

- Add deterministic scenario fixtures for early, mid, and late game; collect human and scripted evidence for spawning, overload pressure, costs, progression, resource supply, and map difficulty.
- Use recursive passes to discover and fix verified defects; promote every fixed bug class to a regression.

Acceptance:

- No verified high- or medium-severity gameplay finding remains open.
- Balance constants are justified by recorded scenario distributions rather than one anecdotal run.
- At least one sustained manual play session reaches each progression tier without crashes, deadlocks, or impossible required choices.

Substeps: GM-11a checks in deterministic early/mid/late scenarios and metrics; GM-11b runs paired scripted baselines; GM-11c records sustained manual play evidence; GM-11d runs recursive discovery/fix/prove passes and promotes regressions; GM-11e changes one balance family at a time and reruns the paired evidence before accepting it.

### GM-12 - Train and validate competent long-horizon policies

Dependencies: GM-02 and the stable post-balance task contract from GM-11.

Scope:

- Run matched feed-forward, recurrent, history-layout, semantic structured-only, direct semantic-hybrid, player-equivalent privileged-transfer, and task-specific action-head experiments using at least five independent training seeds per configuration. Direct semantic observations remain an explicitly assisted task; only a deployed actor that receives pixels alone remains player-equivalent.
- Evaluate fixed checkpoints on paired held-out seeds with at least 20 episodes per seed, censoring-aware delivery totals, confidence intervals, equal environment-step budgets, wall-clock curves, and peak resource use.
- Promote a policy only if it demonstrates meaningful route construction and rerouting and beats declared scripted/random baselines on total deliveries.

Work units: GM-12a freezes the post-balance dynamics/action/reward/evaluation benchmark, inventories every final renderer/control/action field, and drafts semantic/oracle/player-pixel observability and conformance rules; GM-12b implements and adversarially tests candidate schemas plus structured-only, direct-hybrid, and pixel-only privileged-transfer candidates, runs leakage/lifecycle/resource smokes, and only then freezes immutable observation versions and an experiment matrix with one durable row per configuration and training seed; each GM-12c training row and each GM-12d checkpoint/held-out-seed evaluation row is its own two-commit remotely finalized transaction with an exact transaction marker, status, artifact locator, model/manifest/index digests, and next-row cursor pushed before another expensive row starts; GM-12e computes run-clustered statistics and resource curves; GM-12f promotes or rejects a candidate from the declared criteria. `STATE.md` must point to the exact matrix row in progress, and a row is never inferred complete from a directory name alone. Until an external artifact store is explicitly authorized, locators are workspace-relative under ignored `output/` and every continuation rehashes/presence-checks them; a missing artifact reopens that row rather than trusting the ledger.

Acceptance:

- The repository contains reproducible commands and authenticated manifests for the selected runs, while large generated models remain outside Git.
- Results distinguish game-over totals from horizon-censored lower bounds and report run-level uncertainty.
- The promoted policy's exact artifact digest, task contract, benchmark summary, limitations, and reproduction instructions are documented.

### GM-13 - Final reconciliation and release-readiness review

Dependencies: all previous increments.

Acceptance:

- Full Python, RL, Node, lint, formatting, pre-commit, dependency audit, headless render, save/replay, and remote CI gates pass.
- Three independent full-codebase reviewers cover gameplay correctness, product/persistence, and RL/reproducibility; all real findings are fixed and re-reviewed.
- Public docs match the live product, no active thread or blocker is mislabeled complete, and this thread moves to `done/`.

## Completion rule

The goal is complete only when GM-00 through GM-13 are all marked complete in `STATE.md`, their evidence is recorded, every required commit is on `origin/main`, and final CI is green. GM-13 archival Commit A may move the thread to `done/`; its Commit B is found there by goal ID and transaction marker. If archival B fails CI, the next continuation searches both `current/` and `done/`, moves the thread back to `current/`, and reopens GM-13c. Context limits, elapsed time, or a completed intermediate commit are never completion criteria.

# Gate proofs

Every gate that retired a lesson, with the product-code edit that was applied to make it go red.


## If a gate here is wrong

A gate and the claim in its header can be wrong together, and when they are they look exactly like a gate that is right: retiring 356 lessons across this fleet found 43 that named a defect their own named test did not catch. Auditing one means reaching what was actually believed, measured, and abandoned — never the sentence the gate carries about itself, which is the same self-agreement these gates exist to catch.

That evidence was deleted in the retirement commits, not lost. This repo's evidence file as it stood immediately before, all 23 entries with their anchors:

    git show 26c31bd:docs/learning/lessons-evidence.md

`git log -- docs/learning/lessons-evidence.md` lists every earlier revision, and `git log -S'<phrase from the gate header>' -- docs/learning/` finds the entry a particular gate came from.


A gate nobody has made fail is a claim, not a gate. This file is the standing answer to "did the gates actually do their job", so it records the exact mutation, the failure line it produced, and that the gate returned green when the mutation was reverted. Where an existing gate turned out NOT to catch the defect it was named for, that is recorded too — those are the most useful entries here.

All runs are `python -m unittest` in the `py313` conda environment (`environment.yml`). Baseline before this work: 1,709 tests, OK, 251s; `npm test` 249 pass / 0 fail.

Six gates in this file were rewritten after an independent critic attacked them; what it found is recorded in each entry and summarised under **What the critic changed** at the end.

---

## Resample a simulator's randomness when planning inside it; a reproducible simulator is not a deterministic game, and one rollout per candidate selects the luckiest future rather than the best action

- **Gate:** `test/test_search_policy.py` :: `SampledFutureTest::test_it_averages_rather_than_taking_one_sample`, and `test/test_search_planning_contract.py` :: `TheSearchPlayerPlansAgainstSampledFutures` (5 tests) — run by `python -m unittest -v`
- **Mutation 1 (the helper):** in `scripts/search_policy.py`, `expected_value` reduced to `return _rollout(env, document, decision, action, cap)`, ignoring `futures` entirely.
- **Red:** `AssertionError: 94.0 != 95.66666666666667 within 5 places : expected_value returned 94.0 where the mean of [95.0, 96.0, 96.0] is 95.66666666666667; it is not averaging over the futures it was given`
- **What had to be fixed first:** at the gate's original rollout cap of 600 that same mutation left **all 15 tests in `test_search_policy.py` green**. Futures on this game do not separate until about 3,000 decisions, so the mean of three identical samples equalled the one sample it was meant to replace, and the assertion was comparing a number to itself. The cap is now 3,500.
- **And the control had to be fixed again, after a critic:** the first replacement control asserted that the rollouts were not all identical. That is neither necessary nor sufficient. Deliveries are integers, so three genuinely different futures can still average to the one-sample value — `[94, 95, 96]` against a real future of 95 passes a "the futures differ" check and leaves the assertion underneath comparing 95 to 95. The control is now the exact condition: `assertNotAlmostEqual(plain, mean(singles))`.
- **Mutation 2 (the call site):** in `play`, `keys` forced to `[]` at every search point.
- **Red:** `19 of 19 candidates were scored against no sampled future` — while the whole of `test_search_policy.py` stayed **green, 15/15**. Nothing had ever tested `play`.
- **Mutation 3:** fresh future keys drawn per candidate instead of once per decision point (common random numbers removed). **Red:** `candidates at 6 decision point(s) were scored against different futures ([0, 1, 2])`.
- **Mutation 4:** `def play(..., futures: int = 0)` — the historical defect, where the function defaulted to the oracle while the CLI advertised 4. **Red:** `` `play` defaults futures to 0 ``. The same assertion now covers `cap`, which had the identical exposure and no pin.
- **Mutation 5:** `--futures` default set to 0. **Red:** `--futures defaults to 0; below two there is nothing to average`.
- **The bar is two futures, not one.** The first version of the call-site gate asserted only that the future set was non-empty, so `--futures 1` passed it while reproducing the lesson verbatim: reseeding to a single future removes the clairvoyance but leaves the winner's curse, and here the noise is the size of the signal.
- **Green after revert:** yes (`scripts/search_policy.py` restored byte-for-byte; 15/15 and 8/8).
- **Also fixed:** the module docstring of `scripts/search_policy.py` still asserted the retracted claim — "One rollout per candidate gives the exact future under the default policy and no averaging is needed" — and `main` passes `description=__doc__`, so `--help` printed it. Deleting the prose that corrects a reader while leaving the prose that misleads one is how this knowledge would actually have been lost.

## A deterministic simulation is not a faithful one: prove a snapshot reproduces the live run's continuation, since a rewound seed is perfectly repeatable and perfectly wrong

- **Gate:** `test/test_search_policy.py` :: `SnapshotFidelityTest::test_a_rollout_predicts_the_future_the_live_game_produces` — run by `python -m unittest -v`
- **Mutation:** in `scripts/search_policy.py`, `_restore` rebuilt the game from a rewound RNG — `env._mediator = deserialize_game(reseeded(document, 0))`. This is exactly the failure the test's own docstring describes: perfectly deterministic, and simulating a future that never happens.
- **What had to be fixed first:** the gate ran an 800-decision window and was **green** with that mutation live. Measured against it:

      400 decisions   live   8.0   snapshot   8.0   same
      800 decisions   live  19.0   snapshot  19.0   same   <- the old window
     1500 decisions   live  37.0   snapshot  37.0   same
     3000 decisions   live  80.0   snapshot  82.0   DIFFERS
     4000 decisions   live 118.0   snapshot 117.0   DIFFERS

  A changed spawn sequence takes thousands of decisions to reach the delivery count, so the two runs stay numerically equal long after they have stopped being the same game. The window is now 4,000 and the measurement is in the gate's header.
- **Red:** `AssertionError: 117.0 != 118.0 : the snapshot rollout predicted 117.0 deliveries where the live game produced 118.0; search would be choosing actions for a future that will not happen`
- **The widened window needed a control, and a critic pointed out it had none.** Both loops break on game over, so an episode ending early would silently shrink the window back below the divergence point and return the gate to its false green. It now asserts the live run actually played at least 3,000 decisions before comparing.
- **Green after revert:** yes (4/4).

## Drive a gate with a policy that can actually play; one driven by random play only tests what bad play happens to touch

- **Gate:** `test/test_env_agency.py` — run by `python -m unittest -v`
- **Mutation A:** in `src/rl/semantic_env.py`, the fleet masked out — `mask[crew[...]] = False` and `mask[carriage[...]] = False`.
- **Red:** 4 failures, including `competent play never ran more than 0 train(s); the fleet actions are in the table but unreachable, so line capacity is fixed and no policy can respond to demand`. The same run also turned the line-length assertion red at 3 stations, which is the third of the three historical mutations.
- **Mutation B:** `DEFAULT_MAX_DECISIONS = 450`.
- **Red:** 4 failures, including `an episode stopped on the step limit rather than on game over ... seed 0 ran 450 decisions, seed 1 ran 450 decisions, seed 2 ran 450 decisions`.
- **Green after revert:** yes (9/9). Both mutations are ones the file's own history records as having survived the random-play version of these gates untouched.

## Validate the capability the agent gained, not the mechanism you built: measure what it can now reach, express, decide and exploit

- **Gate:** `test/test_env_agency.py` — run by `python -m unittest -v`
- **Mutation:** the same fleet mask-out as above. The mechanism is untouched: the mask is computed, every action in the table still exists, nothing raises.
- **Red:** `the longest line competent play could build was 3 stations; below five the action space cannot express a network worth routing, however well a policy plays`, plus `the baseline scored 0.0 deliveries, so it is not real play and cannot bound a degenerate policy`.
- All four sub-claims have their own assertion: reach (`test_every_offered_action_takes_effect`, `test_the_fleet_can_actually_be_grown`), express (`test_the_action_space_can_express_a_real_route`), decide (`test_the_agent_has_real_choices`), not exploit (`test_a_degenerate_policy_cannot_outscore_real_play`).
- **Green after revert:** yes (9/9).

## Validate an equivalence on the per-item sequence — what was done and when — never on the summary statistic

- **Gate:** `test/test_event_gate.py` :: `ASpawnInsideTheWaitStepMustNotBeSleptThrough::test_the_delayed_action_arrives_on_time` — run by `python -m unittest -v`
- **Mutation:** in `src/rl/event_gate.py`, `step` calls `self.fast_forward()` instead of `self.fast_forward(seen)`, so the baseline mask is read AFTER the WAIT step has advanced six ticks.
- **What had to be fixed first:** the gate pinned the seed (90048) and the window (700) and left the third input — `wait_backstop` — at its shipped default of 400. With the defect live, **all 25 tests in the file passed**. Re-measured on seed 90048:

      backstop 100   identical
      backstop 200   411 -> 611   REPRODUCES
      backstop 300   identical
      backstop 400   identical                   <- what the gate used
      backstop 600   identical

  A spawn causes a delay only when it lands in the one step that opens a fast-forward, so which backstop reproduces is as arbitrary as which seed does. The gate now asserts the equivalence across a sweep of (100, 200, 300, 400).
- **Red:** `AssertionError: Lists differ: [... (7, 195), (611, 203)] != [... (7, 195), (411, 203)]` at `wait_backstop=200` — the correct action arriving exactly one backstop late, which no delivery total would ever show.
- **Reach, stated honestly:** four values, not a range. A defect reproducing only at, say, backstop 250 would still escape. The sibling `test_reading_the_baseline_after_the_step_reproduces_the_delay` re-implements the defect at 200 and requires it to diverge, so if 200 ever stops reproducing this class goes red rather than becoming vacuous.
- **Green after revert:** yes.

## Match a representation's finest addressable unit to the smallest target it must resolve

- **Gate:** `test/test_rl_model_spatial_acuity.py` — run by `python -m unittest -v`
- **Mutation:** in `src/rl/model.py`, `nn.AdaptiveAvgPool2d((3, 5))` reinserted before `nn.Flatten()` — the encoder head that was removed on 2026-08-13.
- **Red:** `AssertionError: 960 not greater than 960 : fidelity and fast both flatten to 960 values, so the extra pixels are discarded before the policy ever sees them`, and `moving a station three station-widths changed the encoding by only 4.0%`. The 960 is the historical number exactly.
- **Green after revert:** yes (2/2).

## A training-time signal must be reachable by the policy that needs it, and then bounded against being farmed

- **Gate (bounded):** `test/test_shaped_reward.py` :: `ShapedRewardTest::test_total_shaping_is_bounded_so_it_cannot_be_farmed`
- **Mutation:** `PROXIMITY_BUDGET = float('inf')` in `src/rl/shaping.py`.
- **Red:** `clicking one station repeatedly earned 7.999999999999917; the shaping budget must keep a degenerate policy far below the ~19-20 real play earns`.
- **Gate (reachable, new):** `test/test_shaped_reward.py` :: `TheSignalMustBeReachableByThePolicyThatNeedsIt` (2 tests)
- **Mutation:** the gesture ladder removed, leaving only the milestone credit — `bonus = self._connection_credit(mediator)`. This is the exact first version of the wrapper, which paid out zero times across 24 random episodes and 8,721 decisions.
- **What had to be written:** with that mutation live, **all 7 existing tests passed**. Every reachability test in the file drove the *expert's* opening drag, and the expert reaches the milestone on its first gesture — so the gate asked whether shaping pays a policy that can already do the thing, which is not the policy shaping exists for.
- **Red:** `shaping paid out nothing across 600 random decisions on seed(s) [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] of 12`, and `on seed(s) [0..11] every payout arrived only after a line already existed, so the ladder has no rung below the milestone`.
- **Green after revert:** yes (9/9).

## Keep training-time concerns out of fingerprinted contracts; a wrapper costs nothing, an enum member invalidates every saved artifact

- **Gate:** `test/test_gm09a2_task_identity.py`, with `test/test_shaped_reward.py::test_shaping_leaves_the_task_identity_untouched` pinning the wrapper side — run by `python -m unittest -v`
- **Mutation:** `SHAPED = "shaped"` added to `RewardMode` in `src/rl/protocol.py` — shaping expressed as a task-contract concern rather than a wrapper.
- **Red:** `AssertionError: '88dd17f11d8098d3dddb20102e7e7cd1250af97aad5d9e12373b7c89754270ad' != 'c2ef342f9cedfc3b7292ec2517ec7ccca7b2dcf9b49811c6dec529c25e73933e'`, plus an outright ERROR in `test_real_legacy_manifest_reconstructs_to_its_exact_hash` — one enum member, and every previously saved manifest stops reconstructing.
- **Green after revert:** yes (11/11).

## Key a cache on what the DOMAIN can change, not on what the current caller happens to do

- **Gate:** `test/test_semantic_env_mask_equivalence.py` — run by `python -m unittest -v`
- The fingerprint carries three terms whose omission the evidence documents, and each is now gated on its own.
- **Mutation A (route membership):** `_mask_fingerprint` keyed on route LENGTH — `tuple(len(path.stations) for path in paths)`.
- **Red:** `after rerouting a line to a route of the same length the mask disagrees on 4 actions [(201, 'EXTEND_LINE', (0, 1)), (202, 'EXTEND_LINE', (0, 2)), (281, 'PREPEND_LINE', (0, 1)), (282, 'PREPEND_LINE', (0, 2))]` — one legal action withheld and one illegal action offered per line end.
- **Mutation B (`is_game_over`):** the term replaced with `False`.
- **Red:** `seed 11: the mask on the TERMINAL state disagrees on 2 actions [191, 195]` — a finished game still advertising ASSIGN_LOCOMOTIVE and ATTACH_CARRIAGE.
- **Mutation C (`is_unassignment_queued`):** the per-metro flag replaced with `False`. This is the term the rule is actually about: no action in this environment's table can queue an unassignment, and "unreachable from the current caller" is precisely the argument that let the other two be omitted. A critic found it ungated; nothing in `test/` mentioned it.
- **Red:** `after queuing an unassignment through the mediator's public API the mask disagrees on 1 actions [(195, 'ATTACH_CARRIAGE', (0, 0))]; the cache is keyed on what this environment's action table can do rather than on what the game can do`
- **A pinned input for mutation C, found by running the control.** The first version of that test assigned the line's full four metros and then queued one — and passed with the term deleted, because three metros were still attachable and the true mask did not move at all. The flag only reaches the mask when the queued metro is the only candidate, so exactly one locomotive is assigned, and the test asserts the true mask moved before comparing the cached one against it.
- **What had to be fixed first:** `test_it_matches_after_a_different_game_is_restored_behind_it` imports `search_policy`, which lives in `scripts/`, but the file only added `../src` to `sys.path`. Run on its own the test raised `ModuleNotFoundError` and reported an ERROR instead of guarding the cache; it passed in the full suite only because another test module happened to append that path first. A gate whose reach depends on unittest discovery order is not a gate.
- **Green after revert:** yes (6/6, and now green when the file is run alone).

## Set a lookahead from the measured interval between consequences; one shorter than that gap sees cost without benefit and reliably recommends inaction

- **Gate (new):** `test/test_search_planning_contract.py` :: `TheRolloutHorizonOutlastsTheDelayBeforeAPayoff` (3 tests) — run by `python -m unittest -v`
- **Mutation:** `--cap` default set to 150 in `scripts/search_policy.py` — the first implementation's horizon, which scored 144 against the heuristic's 262.
- **Red:** `the default rollout cap is 150 decisions against a measured 2237-decision gap between the scripted policy's own actions on seed 9000; a rollout that cannot reach the next decision point cannot see a payoff, so WAIT wins by construction`, and `the default rollout cap is 150 decisions while an episode on seed 9000 runs 8244`.
- The gate measures the interval rather than quoting it: it plays the scripted policy on the pinned seed, records where it acts, and compares the default cap against the largest gap and the episode length it measures (2,237 and 8,244 today). A control fails loudly if that seed ever stops exhibiting the delayed-payoff structure.
- **Green after revert:** yes (8/8).

## Save the best result while it exists; a training run is not monotonic and the final weights are not the peak

- **Gate (new):** `test/test_training_readout_contract.py` :: `TheBestPolicyMustSurviveTheRunThatProducedIt` (5 tests) and `TheBestKeeperMustActuallyBeWiredIntoTheRun` (3 tests) — run by `python -m unittest -v`
- The first class drives `train_semantic.KeepBest` through the measured collapse (10.0, 40.0, 97.5, 60.0, 35.5) and records which artifact was written at each step.
- **Mutation A:** `if mean > keeper.best:` replaced with `if True:` — the `-best` artifact overwritten at every readout.
- **Red:** `the last "-best" save happened at step 5000 but the run peaked at 97.5 deliveries at step 3000; the artifact keeps its name while holding weights worth 35.5`, and `the keeper reports its best as 35.5 against a measured peak of 97.5`.
- **Mutation B:** the `-best` save removed entirely — the original defect, where the trainer saved only at the end.
- **Red:** `no "-best" artifact was ever written across a run that reached 97.5 deliveries`.
- **The call site was uncovered, and a critic found it.** `KeepBest` is driven directly by two test classes, so its arithmetic was covered twice and its wiring nowhere. **Mutation C:** `callback=keeper.build()` deleted from `scripts/train_semantic.main`. Every direct-drive test stayed green — including `test_train_semantic_eval_trigger.py` — while no run would ever have written a best checkpoint again. `TheBestKeeperMustActuallyBeWiredIntoTheRun` runs `main` with the trainer and vector env replaced by recorders and requires the object handed to `learn` to be the one the keeper built. **Red:** `train_semantic.main() called learn with [None] while the keeper built []`.
- **Green after revert:** yes (12/12 with `test_train_semantic_eval_trigger`).
- **Known limit of its reach:** `scripts/train_residual.py` contains a second, independent best-keeper (`Readout`, defined inside `main`) that is not covered. Gating it needs the same recorder harness pointed at a class the script defines rather than imports, which was not attempted here.

## An initialisation is a claim: save the starting policy and evaluate it as readout zero

- **Gate (new):** `test/test_training_readout_contract.py` :: `AnInitialisationIsAClaimSoItIsMeasured` (4 tests) — run by `python -m unittest -v`
- The gate RUNS `scripts/train_residual.main` with the trainer, the vector env, the heuristic reference and the readout replaced by recorders, and asserts on the order of the events it actually produced.
- **The first version of this gate was a source check, and a critic broke it in one probe.** It parsed the AST for a save and a readout appearing before the first `.learn(...)`, and its helper walked into compound-statement bodies. Measured on mutated copies:

      as shipped                                     PASS
      readout wrapped in a condition never taken     PASS   <- false green
      same behaviour moved to a module-level helper  FAIL   <- false red
      save and readout deleted                       FAIL

  The false green is the defect itself: the script takes its first gradient step having measured nothing, and all three assertions passed. Ordering is a property of execution, so it is now asserted by executing.
- **Mutation A (re-run against the behavioural gate):** the save and readout wrapped in `if args.total_timesteps < 0:`.
- **Red:** three failures — `train_residual.main() never measured its own initialisation (recorded ['learn', 'save'])`, plus the save and artifact-identity checks.
- **Mutation B:** `paired_readout(f"{args.output}-latest", ...)` — reading out something other than the untrained policy. **Red:** the artifact-identity check.
- **Refactor probe (must NOT go red):** the same save and readout moved into a module-level helper called from `main`. **Green**, as it should be.
- **Green after revert:** yes (12/12).
- **Known limit of its reach:** `scripts/train_semantic.py` makes an initialisation claim on `--resume` ("start from a policy that already plays") and does not read out step zero. Extending the gate to it would require changing that script's behaviour, which was out of scope.

## Do not report an effect size from a handful of trials when the outcome is bimodal; the mean is mostly a count of lucky seeds

- **Gate (new):** `test/test_evaluation_protocol.py` :: `EveryReportedScoreMeetsThePreRegisteredSampleSize` (4 tests) — run by `python -m unittest -v`
- The gate reads the pre-registered minimum out of `docs/rl-model-selection.md` rather than restating it, then checks the default episode count of every entry point that reports a comparable score.
- **Mutation:** none was needed. **The defect was live at baseline, twice over.** `scripts/evaluate_rl.py` and `scripts/evaluate_policy.py` both defaulted to 10 episodes against a document pre-registering at least 20.
- **Then the gate's own reach was proved, and it failed that proof.** The entry points were a hand-written list — an exemption list wearing a different hat. Replacing it with a sweep of `scripts/` immediately found four more, none of which had been in the list:

      dagger_semantic.py --episodes        10
      hybrid_player.py   --episodes        16
      search_policy.py   --episodes         8   <- the n=8 that published "+128.50 +/-117.96, winning 8/8"
      train_rl.py        --eval-episodes    5   <- the five-sample lottery, still live

  The last is the exact defect the evidence describes: against a score distribution spanning 110 to 800 and an MDE near +/-190, every "new best, saved" was a five-sample lottery, and the checkpoints picked that way are what later comparisons ran against.
- **Reach, proved rather than asserted:** `test_a_new_script_is_inside_the_gate_the_day_it_is_written` writes a script the discovery has never seen, declaring `--episodes` with a default of 5, and requires both that discovery finds it and that the bar reports it as short. A class claim that is not exercised on a new member of the class is a sentence, not a gate.
- **Fix:** all six defaults raised to 20, each with the reason at the call site. Explicit smaller runs are unaffected — CI's smoke jobs pass `--episodes 1` and `--eval-episodes 1` deliberately.
- **Also hardened after the critic:** the bound was read entirely out of a prose file, with the only check on it being "at least 2" — so editing one word of `docs/rl-model-selection.md` to "at least 2" would have made the whole gate green with every 10-episode default restored. The measured floor of 20 now lives in the test; the document may raise the bar and may not lower it. And a non-integer default is now reported as unreadable rather than compared, which would have raised a TypeError instead of failing an assertion.
- **Green after fix:** yes (4/4).
- **What bounds this gate:** it binds the DEFAULT of each entry point, not every run. It removes the case the defect came from — a run launched without thinking about n, whose number is then quoted — and does not stop someone passing `--episodes 6` on purpose.
- **Consequence recorded deliberately:** `scripts/evaluate_rl.py` and `scripts/train_rl.py` are both in `TRAINING_SOURCE_PATHS`, so this rotated the training-source fingerprint and `EXPECTED_LF_TRAINING` was repinned. That pin is a provenance contract rather than a checksum of a file that should never change, and repinning on a deliberate change is how it has always been used. The task and content fingerprints are untouched, so no saved artifact's task identity moves; every saved artifact under `output/` already carried a fingerprint older than this change.

---

## Clause ledger

A compound lesson needs a destination for every clause, not for its headline. Where each one went:

| lesson | clause | destination |
| --- | --- | --- |
| Resample the simulator's randomness | resample and average | `test_search_planning_contract.py`, `test_search_policy.py` |
| | reproducible is not deterministic | `scripts/search_policy.py` module docstring (it had asserted the opposite) |
| | common random numbers across candidates | `test_every_candidate_at_a_decision_shares_the_same_futures` |
| A training signal must be reachable, then bounded | reachable by exploring play | `TheSignalMustBeReachableByThePolicyThatNeedsIt` |
| | bounded against farming | `test_total_shaping_is_bounded_so_it_cannot_be_farmed` |
| Key a cache on what the domain can change | route membership | `test_it_matches_after_a_line_is_rerouted_to_the_same_length` |
| | `is_game_over` | `test_it_matches_under_random_play_which_builds_odd_lines`, pinned seeds |
| | `is_unassignment_queued` | `test_it_matches_after_an_unassignment_is_queued_through_the_public_api` |
| Save the best result while it exists | keep the peak, not the last | `test_the_best_checkpoint_is_the_peak_and_not_the_last_weights` |
| | print the history as the run goes | `test_the_evaluation_history_is_kept_as_the_run_goes` |
| | the collapse's step-size signature | `scripts/train_semantic.py` `KeepBest` docstring and the file's LR comment |
| | the keeper reaches the trainer | `TheBestKeeperMustActuallyBeWiredIntoTheRun` |
| An initialisation is a claim | save the starting policy | `test_the_starting_policy_is_written_to_disk` |
| | evaluate it as readout zero | `test_the_starting_policy_is_evaluated_before_a_single_gradient_step` |
| | read out the policy you saved | `test_readout_zero_measures_the_policy_that_was_just_saved` |
| Validate the capability, not the mechanism | reach / express / decide / exploit | one assertion each in `test_env_agency.py` |
| Set a lookahead from the interval | measure the interval | `TheRolloutHorizonOutlastsTheDelayBeforeAPayoff` |
| | a short horizon biases toward inaction | that class's docstring and failure message |
| Count the decision points | how many / how many forced / how much live | one C candidate, all three numbers in its anchor |
| Count the OPTIONS | one option means forced | C candidate; the environment-side half is `test_the_agent_has_real_choices` |
| A gate is mutation-proved | mutation-prove it | already in the constitution (`AGENTS.md`) |
| | pin every input that reproduces | staged in `canon-candidates.md` as an amendment — NOT already canon |
| | two fixes covering one scenario need two tests | `test_semantic_env_mask_equivalence.py`, in the reroute test's docstring |
| Match the finest addressable unit | resolution must reach the features | `test_rl_model_spatial_acuity.py` |
| | before tuning anything else | sequencing — the "read the outcome curve" C candidate |

## What the critic changed

An independent lane was given the diff and the claims and asked to find why the measurements did not support them. It found four blockers and several weaker gates, all recorded above. In summary:

- One gate could not fail for the defect its own name described (`--futures 1` passed a check written for `--futures 0`).
- One gate was a source-shape check that a never-taken branch satisfied, and that a behaviour-preserving refactor broke.
- One "control" asserted a condition that was neither necessary nor sufficient, and the comment justifying a change beside it was measurably wrong.
- One deleted lesson's claim survived only in a module docstring that still asserted its opposite, printed to the user by `--help`.
- Two fingerprint terms and one call site were gated; the third term and one other call site were not.
- A hand-written entry-point list hid four live violations of the very rule it was written to enforce.

Every one of those was a gate that looked correct from the outside. That is the whole argument for the mutation proof, and for a critic on top of it.

# Local rules

Steering specific to this repo that outlives the task that produced it. Fleet-wide direction lives in `../fleet/FLEET.md`; this file holds only what is true here and nowhere else.

A rule earns a place here when it would change how the next unrelated task is approached. Anything already enforced by a test, lint rule or fixed command belongs to the machine instead — do not restate a gate here.

## RL work

- **An environment change is not done until `test_env_agency.py` passes.** Any
  edit to an action space, mask, observation or reward gets measured by what
  the agent can now reach, express, decide and exploit -- not by whether it
  runs. Six defects here shared exactly that shape, each looked like a weak
  policy rather than a broken environment, and each was found by playing the
  environment rather than by reading the code. If a new property is learned,
  add it to that gate rather than to a note.

- **Every experiment gets a ledger entry, including the ones that fail.** `docs/rl-experiments.md` records the hypothesis, what was measured, and a blunt verdict — CONFIRMED, REFUTED, INVALID, SUPERSEDED. Negative results and reversed conclusions are the point of the file, not an embarrassment to be tidied out of it; a wrong first answer that is written down is cheaper than the same wrong answer reached twice.

- **Report against the protocol in `docs/rl-model-selection.md`, or say plainly that you did not.** It pre-registers five seeds per configuration, at least 20 held-out evaluation episodes, run-level rather than pooled-episode statistics, and best-seed scores as a diagnostic only. Most exploratory runs here will not meet that bar. Stating the shortfall alongside the number is acceptable; quoting the number as though it met the bar is not.

- **Shaping, curricula and other training aids stay outside the task contract.** They belong in wrappers applied to training environments. The task is "deliver passengers before the system is overwhelmed"; anything that changes `RewardMode`, the action space, the observation, or the render profile changes what the agent is being measured on and invalidates every artifact fingerprinted against it.

- **Run the critic BEFORE launching a multi-hour job, not while it runs.** Two lanes reviewing a residual design found, an hour into a four-hour pair of runs, that the initialisation was not what the design claimed -- so both runs were un-learning their own starting noise while printing a closing gap. The review cost twenty minutes and the runs cost four hours. A long job's premise is exactly the thing an independent lane is cheapest at attacking, and the cheapest moment to attack it is before the GPU-hours are committed.

- **One silently-ignored knob means the class is unaudited.** `--eval-episodes` was found by accident; auditing the rest of the surface the same way found thirteen more, one of them invalidating the recorded learning rate of every warm start in the project's history. The audit is cheap and mechanical: for each flag, constructor keyword and module constant, trace the value from its parse site into its consumer **with the callee's signature open**, then have an independent lane try to refute each suspect. Positional-argument mismatches and post-`load()` attribute assignments are invisible to any reading that stops at the caller.

- **Measure the shape of the decision problem before tuning the learner.** How many decisions per episode, how many of them are forced, how much of the observation is live. Each is one probe, and each bounds what any amount of learning could have achieved -- this lane spent five sessions on architectures while 99.8% of every rollout was a forced WAIT and 560 of 654 observation floats were permanently zero.

- **Semantic-lane RL runs through `EventGatedSemanticEnv`.** It is proved free for the scripted policy on 200 seeds (identical deliveries, decision counts, and full action sequence) and cuts the horizon a learner sees by 135x. A run that queries the policy every six ticks is spending 99.8% of its gradient on WAIT; if there is a reason to do that, state it.

- **Evaluation is never assisted.** No shaping wrapper, no privileged channel, no teacher actions. A held-out evaluation that quietly includes exploration credit corrupts not just its own number but every comparison built on it.

- **Do not restart the throughput work until a policy earns reward.** It was measured and abandoned: the environment pipeline delivers ~1300 env-FPS against training's 133-235, and `SubprocVecEnv` is 3.8x *faster* than in-process, so the IPC hypothesis was wrong. All of it was moot at a reward of exactly 0.00 at every logged step, because a fix on a path carrying no signal cannot be validated by the thing you care about. Numbers in `docs/devlog/detailed/2026-08-13_2026-08-14.md`.

## Game changes in service of the agent

- **The observation is a design surface, not a given.** Render scale, entity sizes and contrast are as legitimate to change as the network, and are sometimes the cheaper fix — a passenger 0.5 px wide is destroyed before any architecture sees it. Weigh the two together rather than treating the game as fixed.

- **But changing the game is the more expensive lever, so price it.** Render or mechanic changes rotate task fingerprints, invalidate trained policies and saved runs, and are locally high-risk under `AGENTS.md`. Re-derive how much game change is still needed *after* the model-side fix, rather than inheriting a number sized against the old model.

## Shell mechanics on this machine

- **Write commit messages through a file or a quoted heredoc, never `-m "..."`.**
  A double-quoted `-m` is still interpreted by the shell, so backticks become
  command substitution: a message describing a `candidates` argument was
  committed with the word silently deleted and `candidates: command not found`
  printed to stderr, which is easy to miss among Git's own line-ending warnings.
  `main` here forbids force-pushing, so an amend cannot fix a message that has
  already been pushed — the defect is permanent. Use `git commit -F <file>` or
  `git commit -F - <<'EOF'`.

- **Prefer a scratchpad Python file over an inline heredoc for multi-line
  edits.** Heredoc terminators are repeatedly swallowed here — the shell reports
  `unexpected EOF while looking for matching quote` and the whole edit is lost —
  because the files are CRLF. Writing the patch script to the scratchpad with
  the Write tool and running it costs one extra call and does not fail.

## Long-running jobs

- **Emit the decisive metric while the job runs, not after it.** A run that only
  reports at the end forces a choice between waiting hours and knowing nothing,
  and most runs here are decidable long before they finish. The pointer-head RL
  run was stopped at 6.8M of 20M steps because a proper n=40 evaluation of its
  checkpoint showed it below the blind control; the eight remaining hours would
  have bought a confirmed negative. Structure the output so the run can be
  killed: print the number that predicts the outcome, on a fixed interval, with
  `flush=True`.

- **Print the number that predicts the outcome, not the one that is convenient.**
  Behaviour cloning here reported training agreement on a mixture that is 99.8%
  forced WAIT, so it read 98.1% while held-out agreement on real decisions was
  72.8% and the policy played like a network fed constant input. Overall
  agreement never once predicted score. `scripts/bc_semantic.py --readout N` now
  reports held-out real-decision agreement every N epochs for exactly this
  reason.

- **State the kill criterion before starting.** "Stop if held-out agreement is
  flat across two readouts" is a decision that can be made in advance and
  executed cheaply; "see how it looks at the end" is how a 30M-step run consumed
  a night to reproduce a result already visible at 6M.

- **Check in on a schedule rather than on completion.** Several jobs here ran
  for hours past the point where their answer was already legible -- two training
  runs kept going after both had settled, and a search run held twenty cores
  while its own partial output already showed the effect collapsing.

## Adding an observation feature

**Do not add a feature until you can state the measurement that would prove it
useless, and then run it.** Features here have been added on plausible reasoning
and have never once moved the score. The observation reached 654 floats of which
**590 are constant across an entire episode and only 45 are non-zero at any
instant** -- roughly 7% carrying signal -- because every addition was justified
by an argument rather than a result.

The record:

| feature | argument for it | what it bought |
| --- | --- | --- |
| per-end distances (`REACH`) | the teacher's rule needs them | agreement 44% -> 81.5%, score unchanged |
| rank of nearest unserved (`RANK`) | the network cannot do the argmin, so hand it over | agreement 73.8% -> 83.3%, score +2 |

Both were verified to fire correctly -- the rank block marks the teacher's own
graft target 5 times out of 5 -- and neither moved the outcome. Correct and
load-bearing is not the same as useful.

**The bar, before the feature is written:**

1. **Name the falsifier.** What measurement, at what sample size, would show this
   feature is worthless? If the answer is "agreement goes up", that is not a
   falsifier: agreement has never predicted score in this project across the
   0-83% range (E40, E41).
2. **Measure the outcome, paired, at adequate n.** Deliveries is a ~5-rung ladder
   with one rung of per-episode noise, so anything under ~45 deliveries needs n
   in the hundreds. State the minimum detectable effect beside the result.
3. **Have an independent subagent review it as a harsh critic BEFORE it is
   committed.** Not a summary of the change -- give it the diff, the claimed
   benefit and the measurement, and ask it to find the reason the measurement
   does not support the claim. Every multi-lane review run in this repo has found
   a defect the author missed, including three in a cache the author had already
   gated and mutation-tested.
4. **If it does not move the outcome, remove it.** A feature that is merely
   harmless still costs: it dilutes the input, and it is one more thing a future
   session must reason about. Dead weight in an observation is not free.

The same bar applies to removing a feature: prove the removal is neutral before
claiming it is a simplification.

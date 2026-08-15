# Lessons evidence

The war story and the anchor behind every rule in [lessons.md](lessons.md). Not session-start reading — open an entry when its rule is in doubt, or when the work is in that area.

An entry with no anchor is folklore. Entries are corrected in place as understanding improves, with the correction dated; deletion is reserved for a lesson that became a gate.

---

## Read the outcome curve before optimising the machinery that produces it

**Anchor:** 2026-08-14, commit `80efd95`; `docs/rl-experiments.md` E1, E2, E4.

Two real defects were found and fixed in the RL stack before anyone looked at a reward curve. The installed torch was a CPU build on a machine with an RTX 4090, worth **146x** on a forward+backward pass (398.88 ms to 2.73 ms). The pixel encoder pooled every render profile down to an identical 960 values, so raising resolution provably changed nothing — a 16 px shift of the whole frame moved the features less than a 2 px shift did.

Both were genuine. Neither could have moved the score. Two 3M-step training runs then held `rollout/ep_rew_mean` at **exactly 0.00 at every logged step**, because across 12 random episodes and 4,170 decisions the policy never once built a usable line: with no reward anywhere in a batch the advantage is identically zero and the policy gradient is the zero vector.

Reading one curve first would have reordered the whole day. The generalisation is not "profile before optimising" — it is that a fix on a path carrying no signal cannot be validated by the thing you care about, so it should be sequenced after something that can be.

What was tried and abandoned: throughput work. The environment pipeline delivers ~1300 env-FPS against training's 133-235, and `SubprocVecEnv` is 3.8x *faster* than in-process, so the IPC hypothesis was wrong too. All of it was moot at zero reward. Do not restart that work until a policy earns reward.

---

## When two metrics disagree in direction, the measurement is wrong

**Anchor:** 2026-08-14, commit `9b2fb66`; `docs/rl-experiments.md` E7 and E8.

An ablation compared a flat coordinate head against a spatial heatmap and reported the flat head at **8371x uniform** probability — an apparently crushing win for the status quo, and the opposite of the truth.

The tell was internal: the same run gave the flat head 40% probability *and* a **worse** argmax error than the arm it beat. Those cannot both be true of a better model. The cause was that the expert's pointer actions mix two populations — drags targeting stations, whose coordinates move with the layout, and clicks on fleet controls, which sit at **fixed UI pixels in every game**. A flat head memorises a constant trivially, so the experiment measured recall of a constant rather than visual grounding.

Restricted to station targets, the result reversed: flat **1.9x** uniform against spatial **9.5x**.

The habit worth keeping is to look for the internal contradiction before believing a surprising result, and to ask what population the data actually contains.

---

## Do not report an effect size from a handful of bimodal trials

**Anchor:** 2026-08-14, commit `d6e0148` correcting `9bc1321`.

A configuration was published as **6.17 mean deliveries, max 19** on six evaluation episodes. Twelve held-out episodes gave **1.50, max 9**. The number had already been committed and written into a published summary.

Outcomes here are near-bimodal: either the opening drag lands and the run continues, or it does not and the run dies at exactly the 400-decision deadline. A mean over a handful of episodes is therefore mostly a count of lucky seeds, and its variance is enormous. The qualitative finding survived the correction; the effect size did not.

`docs/rl-model-selection.md` pre-registers five seeds per configuration and at least 20 evaluation episodes with run-level statistics. That standard exists precisely for this, and was not met by the run that produced the wrong number.

---

## Match the finest addressable unit to the smallest target

**Anchor:** 2026-08-14, commits `9bc1321` and `526fea1`; `docs/rl-experiments.md` E9 and E12.

The policy must point at a station roughly ten pixels wide. Reading its heatmap from a 7x12 feature grid, resampled ~15x up to the action grid, delivered **0** passengers however well trained — the representation's finest addressable unit was coarser than the thing it had to hit. Reading from a 27x48 grid (4x resample) produced the first non-zero deliveries. Preserving resolution to the full action grid through a U-Net raised probability on the expert's exact pixel by **11.8x** (pointer loss 3.127 to 0.656) with **3.4x fewer parameters**, and deliveries from 3.08 to 3.75.

Two generalisations. First, resolution was being destroyed in two independent places — at render, where a passenger is **0.5 px** and therefore gone before the network sees it, and in the encoder, which strides it away — and fixing either alone leaves the ceiling in place. Raising the render profile *after* the encoder was fixed took deliveries from 3.75 to **17.33**.

Second, the reason partial fixes read as exactly zero: a drag needs about four correct pointer actions in sequence, so per-action accuracy compounds and there is no partial credit until a threshold is crossed.

Inherited defaults are worth checking against the task. The encoder here was Nature DQN's, designed for Atari, where translation *invariance* is correct because the output is one of eighteen joystick actions. Choosing where to click is keypoint localisation and needs equivariance — the opposite property. This repo's variant also strided 2 on the third convolution where the original used stride 1, discarding another 2x.

---

## A training signal must be reachable, then bounded

**Anchor:** 2026-08-14; `docs/rl-experiments.md` E14 and E15, `src/rl/shaping.py`.

Reward shaping was added to let the game be learned without a teacher. The first version paid credit for joining stations onto a usable route. Across **24 random episodes and 8,721 decisions it paid out zero times**, because that is precisely the event an exploring policy never reaches — it reproduced the exact zero gradient it was built to remove.

Replacing it with a dense signal — credit on every pointer-down, rising as the click nears a station — fires in **24 of 24** episodes. That immediately created the opposite failure: at 0.02 per pointer-down over a 4000-decision episode a policy can bank ~80 against the ~19-20 real play earns, making "stand beside a station and click forever" optimal. A per-episode budget of 1.0 closes it, verified by driving exactly that degenerate policy and measuring 1.00 total.

Both checks are cheap and belong before any training run: confirm the signal fires under random play, then drive a deliberately degenerate policy against it.

---

## Keep training-time concerns out of fingerprinted contracts

**Anchor:** 2026-08-14; `test/test_gm09a2_task_identity.py`, protocol fingerprint `69c604ac` to `233b0d6b`.

Reward shaping was first implemented as a new `RewardMode.SHAPED` enum member. Adding it rotated the protocol fingerprint, which broke `task_spec_from_manifest` for every previously saved model: six task-identity tests failed and a legacy-manifest byte-compatibility test errored outright.

The suite was right, and the wrapper it forced is the better design regardless. The task is "deliver passengers"; shaping is scaffolding used while learning it, so it belongs in a `gym.Wrapper` applied to training environments only. Evaluation wraps nothing, and a test now pins that both fingerprints are unmoved by wrapping.

The general form: anything that changes a declared contract invalidates saved artifacts built against it, so ask whether the concern is really part of the task before extending the contract to hold it.

---

## Anchor text edits to the file's real bytes

**Anchor:** 2026-08-14; the GIF save block in `scripts/bc_spatial.py`, which collected frames for a full run and silently wrote nothing.

Programmatic edits failed repeatedly in one session for two reasons, both silent. These files are **CRLF**, so an anchor string built with `\n` never matches and the patch reports "anchor not found" at best — or, when several edits are batched before a single write, discards the edits that *did* apply. And `ruff format` may already have rewritten the exact line being matched, so an anchor copied from memory of the pre-format source no longer exists.

The GIF case is the one that cost real work: the save block's anchor had been reformatted, the edit silently never applied, and a full training run finished having captured frames it never wrote.

What works: read the file, detect its line ending from its own bytes, assert each anchor immediately before its own write rather than batching, and re-read after any formatter run.

---

## Validate the capability, not the mechanism

**Anchor:** 2026-08-14; `test/test_env_agency.py`, and experiments E14-E20 in `docs/rl-experiments.md`.

Six environment defects in one project shared a single shape. Each time the
mechanism was verified -- it imported, it ran, the loss descended -- and the
capability the agent actually gained was not. Each looked like a weak policy
rather than a broken environment, and every one was found by *playing* the
environment, never by reading the code.

    shaping paid for a milestone exploration never reaches   0 payouts / 24 episodes
    a denser signal was farmable                             ~80 vs ~20 for real play
    the mask advertised line slots the game had not unlocked 283 of 284 actions no-ops
    lines could only ever hold two stations                  no network expressible
    the shape encoding moved between episodes                shape-matching unlearnable
    the mask left one legal action per step                  the score measured the sim

The last is the sharpest. After fixing everything else the environment scored
171.5 with a random policy and looked solved; the median number of legal
actions per step was **one**. The agent was watching the simulation. Restoring
route editing took the median to 4 and random play to 0 -- a worse number and
a far better environment, because there were finally decisions to get wrong.

What was tried and abandoned: reasoning about these from the code. Every
defect above is invisible in a diff and obvious in a rollout. The five
questions that catch them are cheap and now run as tests -- can the agent
reach the signal, express the strategies the game rewards, decide between
real options, and not exploit any of it, and does an episode end because the
game ended?

Deleted from `lessons.md` when `test_env_agency.py` covers a case fully; the
rule stays only while judgement is still doing work the gate cannot.

---

## Save the best result while it exists

**Anchor:** 2026-08-14, commit `b2c5cc4`; `docs/rl-experiments.md` E22.

A 1.2M-step run peaked at **97.5** deliveries near 500k and fell to **35.5** by 856k. The trainer saved only at the end, so the best policy it ever produced was never written to disk and is now only a number in a log file.

The collapse itself was recoverable; the loss was not. Two habits follow. Evaluate periodically on held-out data and keep the best-scoring weights, not the last ones — "the run finished" and "the run's best result is available" are different claims. And print the evaluation history inline, so a collapse is visible while it happens rather than reconstructed afterwards from a log by someone who already suspects it.

The collapse had a diagnosable cause worth recognising again: `entropy_loss`, `approx_kl` and `clip_fraction` all rose together while the score halved. Updates getting larger as performance degrades means the step size no longer suits the policy, not that the policy needs more steps.

---

## A stated intention is not a completed action

**Anchor:** 2026-08-14; a turn that ended with "I'm going to stop this run and re-launch with checkpointing" while the run kept training and degraded from 40.0 to 35.5.

The plan was correct, specific, and entirely unexecuted. The turn read as though the work had happened because the reasoning that led to it had happened, and the run was only stopped after the user asked whether it had been.

What makes this hard to self-catch is that describing the fix produces the same sense of resolution as applying it. The check that works is mechanical rather than introspective: before ending a turn, any sentence written in the future tense about work in this session is either done first or is explicitly flagged as not done. "I will X" and "X is done" must never be indistinguishable in the same report.

The same turn also corrected a separate instance of reading a trend from a still-rising last number, which is the tell — a turn spent noticing one bias is not immune to another.


## Measure the teacher's headroom before scaling the student

Four architecturally unrelated approaches converged on 170-195 deliveries:
behaviour cloning (194.7), cloning plus a KL-anchored PPO fine-tune (170.9), a
pointer-head architecture (158.0), and DAgger (175.3). Each failure was diagnosed
as a property of the *learner* -- too little data, the wrong architecture, the
wrong state distribution -- and each fix was real, and none of them moved the
score.

DAgger should have settled it earlier. It did exactly what it promises:
real-decision agreement with the teacher rose from 71.8% to 77.3% over 8 rounds
and 10,314 aggregated labels. The final policy scored 175.31 +/-37.23 against a
control that builds one line and then waits forever at 174.81 +/-38.22 --
statistically identical. Higher fidelity to the teacher bought nothing, which is
only possible if the teacher is not worth being faithful to.

Testing that took minutes once asked. On seed 9000 the heuristic's opening
`CONNECT(0,2)` is worth 275 deliveries while `CONNECT(0,1)` is worth 380; at
decision 1 its `PREPEND_LINE(0,1)` is worth 275 against `ASSIGN_LOCOMOTIVE(0,0)`
at 398. The teacher gives up ~105 deliveries at the game's *first* decision.
Choosing by rollout instead scored 407.88 against the heuristic's 279.38, a
paired +128.50 +/-117.96, winning 8/8.

**Rule.** Imitation cannot exceed its labels. When unrelated architectures
plateau at the same number, suspect the target before the learner, and measure
the teacher's own headroom before spending anything on the student.

Anchor: E28-E30 in `docs/rl-experiments.md`; `scripts/search_policy.py`.

## Set a lookahead from the interval between consequences

The first lookahead implementation used a fixed 150-decision horizon and scored
144 against the heuristic's 262 -- worse than the thing it was improving. The
counts it printed were the diagnosis: 56 searches and 10 overrides on the seed
that scored 100. It was overriding good actions with WAIT.

The heuristic's real decisions on seed 9000 fall at 0-7, 459, 1702, 3411, 3412,
5444 and 7681 out of 8244. Gaps run 450 to 2200 decisions, so a 150-step horizon
cannot reach the *next decision point*, never mind a payoff. Every structural
action costs resources immediately and repays slowly, so a horizon inside the gap
sees the cost and none of the benefit, and inaction wins by construction.

Rolling to episode end removed the bias and turned 144 into 407.88.

**Rule.** Measure the interval between an action and its consequence before
choosing a horizon. A lookahead shorter than that gap does not merely lose
accuracy -- it acquires a systematic bias toward doing nothing.

Anchor: `scripts/search_policy.py` module docstring; E30.

## Deterministic is not faithful

Search here depends on simulating a candidate action and trusting the result. The
obvious check is determinism: three rollouts from one snapshot returned 13.0
deliveries every time, so restore is exact and candidates are comparable.

That check is insufficient, and its insufficiency is invisible. A `deserialize`
that rewound the RNG to the episode's start seed would be *perfectly*
deterministic, pass the check, and simulate a future that never happens. Search
would be optimising a fiction. The only symptom would be a mediocre score --
indistinguishable from the method simply not working, which is exactly the
failure this repository has repeatedly mistaken for a weak policy.

The sufficient check compares against reality: play 800 decisions by continuing
the live game from decision 500, then play the same 800 from a snapshot taken
there, and require the same answer. Both gave 19.0. The simulating environment is
reset on a *different* seed first, so a rollout secretly keyed to its own episode
seed diverges rather than passing by coincidence.

**Rule.** Reproducibility proves a simulation agrees with itself. Only comparison
against the live system proves it agrees with reality.

Anchor: `test_a_rollout_predicts_the_future_the_live_game_produces` in
`test/test_search_policy.py`.

## Drive a gate with play that can play

`test_env_agency.py` exists to catch environment defects that look like weak
policies. Commit `80861c5` proved it stayed green under three
environment-breaking mutations -- horizon cut to 450, lines capped at three
stations, the whole fleet masked out -- and did not fix them.

One root cause. Every gate in the file was driven by *random* play. Random play
crashes this game within a few hundred decisions and never builds anything, so it
never reaches a horizon of 450, never grows a line to four stations, and never
accumulates the resources to buy a second train. The mutated environment and the
real one are indistinguishable to it.

The same root cause produced an assertion that could not fail at all:
`test_a_degenerate_policy_cannot_outscore_real_play` compared the degenerate
score against `max(max(real), 1.0)` where `real` was random play, which scores
about zero here. The floor did all the work and the assertion read `0.0 <= 1.0`
regardless of what the environment did.

Re-based on the scripted heuristic, which plays ~8,200 decisions and builds a
real network, all three mutations turn the suite red: 4, 3 and 4 failures.

**Rule.** A gate is only as strong as the play that drives it. Assert about
limits a competent player reaches, and drive it with one.

Anchor: `test/test_env_agency.py`; mutations re-proved 2026-08-15.

# Canon candidates

Knowledge this repo paid for that has no mechanical trigger here, staged for promotion into `../fleet/FLEET.md`.

Each entry is a lesson that could name no gate: not because nobody tried, but because what it asks of you is a habit of sequencing or attribution rather than a property of any artifact. The canon is where that kind of knowledge belongs — it is the document that is actually read every session. The parent promotes these and then deletes this file; until then it is the only copy, so the provenance is kept with each one.

Nine entries. The last one is an amendment to a rule the constitution already carries, and is marked as such — it is a clause the existing sentence does not cover, not a new rule.

One lesson that arrived here was sent back: the CRLF/anchor lesson CAN name a gate (repo-wide line-ending normalisation plus a test asserting one line ending per tracked `.py`), so by the canon's own rule it stays a queue entry in `lessons.md` naming that gate, rather than being promoted for having no mechanical trigger.

---

## Read the outcome the work is meant to move before optimising anything that produces it: a real defect on a path that carries no signal cannot be validated by the thing you care about, so it is sequenced after something that can be

**From:** python_mini_metro / "Read the outcome curve before optimising the machinery that produces it; a real defect on a path that carries no signal buys nothing."

**Why it has no gate:** it constrains the ORDER in which work is attempted, and no artifact records the order.

**Anchor:** 2026-08-14, commit `80efd95`; `docs/rl-experiments.md` E1, E2, E4. Two genuine defects were found and fixed in the RL stack before anyone looked at a reward curve — a CPU torch build on an RTX 4090 worth **146x** on a forward+backward pass, and a pixel encoder that pooled every render profile to an identical 960 values. Both were real. Neither could have moved the score: two 3M-step runs then held `rollout/ep_rew_mean` at **exactly 0.00 at every logged step**, because across 12 episodes and 4,170 decisions the policy never built a usable line, so the advantage was identically zero and the policy gradient was the zero vector.

## When two measurements from one experiment disagree in direction, the instrument is wrong — not the surprising one; look for the internal contradiction before believing a result, and ask what populations the data actually mixes

**From:** python_mini_metro / "When two metrics from one experiment disagree in direction, the measurement is wrong — not the surprising one."

**Why it has no gate:** it is a rule for reading a result, and the contradiction is between two numbers that are each individually valid.

**Anchor:** 2026-08-14, commit `9b2fb66`; E7 and E8. An ablation reported a flat coordinate head at **8371x uniform** against a spatial heatmap — an apparently crushing win, and the opposite of the truth. The tell was internal: the same run gave the flat head 40% probability *and* a worse argmax error than the arm it beat, which cannot both be true of a better model. The expert's actions mixed two populations — drags at stations, and clicks on fleet controls at **fixed UI pixels in every game** — so the experiment measured recall of a constant. Restricted to station targets the result reversed: flat **1.9x**, spatial **9.5x**.

## Measure the shape of a problem before tuning the thing that solves it: how many decisions there are, how many are forced, and how much of the input is live are one probe each, and together they bound what any amount of optimisation could have achieved

**From:** python_mini_metro / "Count the decision points before optimising the decision maker; how many decisions, how many are forced, how much of the input is live are one probe each and they bound what any learner could have achieved."

**Why it has no gate:** the probe has to be run before the work, and nothing in the artifact records whether anyone ran it.

**Anchor:** E42 in `docs/rl-experiments.md`; `src/rl/event_gate.py`, commit `00c65c6`. Five sessions of reinforcement learning — four architectures, nine ledgered experiments, a search programme and an imitation programme — ran against an environment nobody had counted. One probe that took a minute to write: **7,989 decisions per episode, 14.8 of them actions**, so over 99.8% of every rollout was a forced WAIT and the gradient for the choices that mattered was diluted about 500:1. The same probe found that 560 of 654 observation floats are permanently zero — fixed-slot padding, not lost signal — answering a question the previous session had recorded as its most suspicious open fact.

## A claim of headroom names the decision it lives in and how many candidates that decision offers; a rule with one legal option is forced, and no amount of learning can improve it

**From:** python_mini_metro / "Count the OPTIONS each decision offers before blaming the chooser; a rule with one legal option is forced, and a claim of headroom names the decision it lives in and how many candidates it has."

**Why it has no gate:** it governs how a failure is attributed, and an attribution is not a property of the code. (The environment-side half — that an environment must offer real choices at all — IS gated here, by `test_env_agency.py::test_the_agent_has_real_choices`.)

**Anchor:** E44 in `docs/rl-experiments.md`; `scripts/heuristic_variants.py`, commit `86b19ca`. Nine ledgered experiments concluded a learner could not make the right choice. Measured over 10 episodes of the policy all of them were trying to beat: the crewing rule had **exactly one legal option every single time** — three variants that change it produce byte-identical play — and the grafting rule had **exactly two**, head or tail of one line. The obvious remedy of spending the unused line slots is worth **-95.07 +/-24.17 at n=60**, because the binding constraint was the four-metro fleet all along.

## When every variation of an approach lands on the same answer, that is evidence about the family, not about the ceiling: before calling a system optimal, compute a bound that does not depend on the strategy it uses

**From:** python_mini_metro / "When every variation of a strategy lands on the same answer, that is evidence about the family, not about the ceiling -- compute a bound that does not depend on the strategy (the optimal tour, the offline best) before concluding a system is optimal."

**Why it has no gate:** the missing bound is a different measurement, not a failing assertion, and nothing can detect that it was never taken.

**Anchor:** E47 and its correction in E48, `docs/rl-experiments.md`; `make_rebuilder` in `scripts/heuristic_variants.py`. A session established that the scripted policy's decisions were forced or binary, that a second line cost 95 deliveries, and that a six-weight search over the one real decision found nothing at **+/-3 on 200 held-out seeds with 193 exact ties**. Every number was correct; the conclusion "at or near the ceiling of this action space" was not, and it survived a full write-up. The check that broke it took four minutes: the route the policy builds is **41.6% longer** than the optimal ordering of the same stations. Greedy is within **3.9%** of the best route any end-choosing policy could reach, while insertion-only growth is **34.2%** above the optimum — so the decision that had been searched to exhaustion was the wrong decision.

## End a turn on what was done, not on what will be done next: before finishing, any sentence written in the future tense about work in this session is either executed first or explicitly flagged as not done

**From:** python_mini_metro / "A stated intention is not a completed action -- end a turn on what was done, not on what will be done next."

**Why it has no gate:** it is a property of a report, not of a repository.

**Anchor:** 2026-08-14; a turn that ended with "I'm going to stop this run and re-launch with checkpointing" while the run kept training and degraded from 40.0 to 35.5. The plan was correct, specific, and entirely unexecuted; the run was stopped only after the user asked whether it had been. What makes it hard to self-catch is that describing the fix produces the same sense of resolution as applying it, so the check that works is mechanical rather than introspective: "I will X" and "X is done" must never be indistinguishable in the same report.

## Imitation cannot exceed its labels: when unrelated approaches plateau at the same number, suspect the target before the learner and measure the target's own headroom first

**From:** python_mini_metro / "Before scaling a student, measure the teacher's own headroom; imitation cannot exceed its labels, and a plateau across unrelated architectures indicts the target rather than the learner."

**Why it has no gate:** it is a diagnosis rule for a pattern that only appears across several completed experiments.

**Anchor:** E28-E30 in `docs/rl-experiments.md`; `scripts/search_policy.py`. Four architecturally unrelated approaches converged on 170-195 deliveries — behaviour cloning 194.7, cloning plus a KL-anchored fine-tune 170.9, a pointer head 158.0, DAgger 175.3 — and each failure was diagnosed as a property of the learner, and each fix was real, and none moved the score. DAgger did exactly what it promises: agreement rose 71.8% to 77.3% over 8 rounds and 10,314 labels, and the final policy scored **175.31 +/-37.23 against a control that builds one line and waits forever at 174.81 +/-38.22**. Testing the teacher took minutes once asked: on seed 9000 it gives up ~105 deliveries at the game's *first* decision, and choosing by rollout instead scored 407.88 against its 279.38.

## Hand reviewers an explicit ref — a commit or a throwaway worktree — and do not edit the reviewed files until they return; reviewing a moving target produces confident findings about a state nobody can reproduce

**From:** python_mini_metro / "Freeze the tree before review: run reviewers against a pinned commit or worktree, or they review a moving target."

**Why it has no gate:** the reviewer runs outside the repository's own tooling, and nothing the repo can assert covers what a review lane was looking at.

**Anchor:** external `claude -p` review of commit `47997a3`, 2026-08-15. About twenty minutes in, the reviewer noticed a probe script giving opposite answers on two runs, found six files dirty that had been clean at its start, re-ran its entire analysis in a detached worktree at a pinned commit, and said so in its report. That was the reviewer's save, not the author's.

**Reinforced 2026-09-02, in this repo, by a mechanism rather than a person:** `npm test` failed at baseline with `actual: 'source-changed', expected: 'drive'` because a mutation was live in the working tree while the recursive playtest contract ran. Re-run against a frozen tree: 249 pass, 0 fail. A test harness that reads the source is a reviewer too.

## Pin every input that reproduces a defect, not just the one you thought of — a gate with one input pinned and a second left at its default has exactly the hole the first was pinned to close

**From:** python_mini_metro / "A gate is only real once mutation-proved against the specific defect; pin the inputs that reproduce it, because a nearby seed can pass with the bug live."

**This is an AMENDMENT to a rule already in the constitution, not a new rule.** The canon carries the first clause — a gate counts only once it has been made to go red by reintroducing the defect. It does not carry the second, and the second is the clause that cost the most here. Recording the whole lesson as "already promoted" is how the uncovered half gets lost, so it is staged rather than dropped.

**Why it has no gate:** it is a rule about how gates are written, and the repository cannot assert that the inputs someone chose are the ones that reproduce.

**Anchor:** measured twice on 2026-09-02 in this repo. `test_semantic_env_mask_equivalence` pins seeds 8, 17 and 18 because a review sweep of 50 episodes found those are the ones that reproduce a stale terminal mask, and an earlier version on seed 11 passed with the defect live. And `test_event_gate`'s spawn regression pins seed 90048 and a 700-decision window — and left `wait_backstop` at its shipped default of 400, which does not reproduce. Only 200 does. With the defect reintroduced, all 25 tests in that file passed. A third instance the same day: the mask-cache gate for `is_unassignment_queued` was written with the line's full four metros assigned, and passed with the fingerprint term deleted, because three metros were still attachable and the true mask never moved. The flag only reaches the mask when the queued metro is the only candidate.

The lesson's third clause — when two fixes cover one scenario, add a test that isolates each — is preserved in `test/test_semantic_env_mask_equivalence.py`, whose reroute test exists precisely because the `_restore` cache-clear independently covered the same case.

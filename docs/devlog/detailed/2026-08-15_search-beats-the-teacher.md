# 2026-08-15 — the plateau was the teacher, not the learner

## What was believed, and what proved it false

Four architecturally different approaches had landed in the same 170–195 band: behaviour cloning (194.7), cloning plus a KL-anchored PPO fine-tune (170.9), a pointer-head architecture (158.0), and DAgger (175.3). The scripted heuristic scored ~262 from the identical action space and the identical observation.

The working explanation, recorded as E28, was that this game *multiplies* decisions where imitation metrics *average* them: roughly fourteen real decisions per episode, each worth enormous value, so getting three or four wrong costs ~70 deliveries however closely the policy matches the teacher elsewhere. That explanation was consistent with every measurement available at the time — including DAgger's clean null result, where real-decision agreement rose from 71.8% to 77.3% and the score did not move at all (175.31 ±37.23 against a one-line control's 174.81 ±38.22).

It was also wrong about the binding constraint, and the reason it survived so long is that it was never tested against the obvious alternative: **that the teacher itself was bad.**

## The measurement

The game serialises exactly, so a candidate action can be *tried* rather than predicted. Take a decision point, apply a candidate, roll it to the end of the episode under the heuristic, and read the delivery count.

Two properties had to hold first, and only one of them is what a naive check would look for.

- **Determinism.** Three rollouts from one snapshot returned 13.0 deliveries every time.
- **Fidelity.** Determinism alone is *not* sufficient, and this is the trap worth remembering. A restore that rewound the RNG to the episode start would be perfectly deterministic, pass the determinism check, and simulate a future that never happens — search would be optimising a fiction, and the only symptom would be a mediocre score, indistinguishable from the method not working. So the real check plays the same 800 decisions twice, once by continuing the live game from decision 500 and once from a snapshot taken there. Both produced 19.0. The simulating environment is reset on a *different* seed first, so a rollout that secretly depended on its own episode seed would diverge rather than pass by coincidence.

With that established, seed 9000's opening:

| decision | heuristic's choice | its value | best found | value |
| --- | --- | --- | --- | --- |
| 0 | `CONNECT(0,2)` | 275 | `CONNECT(0,1)` | **380** |
| 1 | `PREPEND_LINE(0,1)` | 275 | `ASSIGN_LOCOMOTIVE(0,0)` | **398** |

The heuristic gives up ~105 deliveries at the game's first decision and ~123 at the second. Every learned policy in this repository had been trained to reproduce that.

## The result

Paired evaluation — same seed played twice, so layout luck cancels:

```
seed 9000    803 vs 275   +528        seed 9004    393 vs 391     +2
seed 9001    318 vs 253    +65        seed 9005    468 vs 279   +189
seed 9002    265 vs 174    +91        seed 9006    474 vs 425    +49
seed 9003    276 vs 217    +59        seed 9007    266 vs 221    +45

search 407.88, heuristic 279.38, paired gap +128.50 ±117.96, won 8/8
```

First method here to beat the scripted heuristic, and it wins on every seed.

## What a first attempt got wrong

The first version used a fixed 150-decision lookahead and scored **144** against the heuristic's 262 — worse than doing nothing new. The diagnosis is in the counts it printed: 56 searches and only 10 overrides on the seed that scored 100.

The heuristic acts at decisions 0–7, 459, 1702, 3411, 3412, 5444 and 7681 out of 8244, so gaps between real decisions run 450 to 2200. A 150-step horizon cannot reach the *next decision point*, let alone see a payoff. It saw each action's immediate cost and none of its delayed benefit, so WAIT won by default and search systematically under-acted. Rolling to episode end removed the bias entirely.

The generalisable form: **a lookahead shorter than the interval between consequences measures cost without benefit, and will reliably recommend inaction.** Measure that interval before choosing a horizon.

## Detail worth keeping

Search overrides the heuristic on only 6–15 of 17–32 search points. So most of the heuristic's choices are already right, and a minority of decisions carry the entire 128-delivery gap — which is exactly why 77% imitation agreement could look healthy while the score did not move. E28's multiplication observation was real; it just described the *sensitivity*, not the cause.

Longest line rises from the heuristic's typical 7–8 stations to 8–11. Search finds that committing further to one line pays.

Variance is enormous: +528 on one seed, +2 on another. The honest claim is that search wins consistently by a wildly seed-dependent amount, not that it triples the score.

## A reviewer catch on the search itself

The shortlist took the heuristic's pick plus `structural[:5]`. The action table is ordered by `(kind, first, second)`, so that slice systematically offered station 0 and 1 and never looked at the far side of the board. Every search in the +128.5 result examined a biased corner of the map — for the same rollout cost as sampling. Now sampled, with the player and the label generator sharing one `shortlist_for` so they cannot drift apart.

## Gates that could not fail

Commit `80861c5` named three environment-breaking mutations that `test_env_agency.py` stayed green under — a horizon cut to 450, lines capped at three stations, and the whole fleet masked out — and did not fix them.

One root cause: every gate in that file was driven by **random play**, which crashes within a few hundred decisions without building anything, so it never reaches the limit being asserted about. A gate driven by a policy that cannot play only tests what bad play happens to touch.

Worse, `test_a_degenerate_policy_cannot_outscore_real_play` could not fail at all. It compared against `max(max(real), 1.0)` where `real` was random play, which scores about zero here — so the floor did the work and the assertion read `0.0 <= 1.0` regardless of the environment.

All now driven by the heuristic, with each mutation re-applied and proved to turn the suite red: horizon 450 → 4 failures, 3-station cap → 3, fleet masked → 4.


## The correction: search was picking lucky futures

Everything above is measured correctly and the headline conclusion drawn from it was still wrong.

Rollouts are deterministic given the serialised state, and that state **includes the RNG**. So every candidate was scored against exactly one future — the one that will actually happen — and search knew which passengers and stations were coming. The 574-float observation encodes none of it.

Holding the board fixed at decision 0 of seed 9000 and varying only the RNG:

| candidate | f0 | f1 | f2 | f3 | mean |
| --- | --- | --- | --- | --- | --- |
| `CONNECT(0,2)` *(heuristic's pick)* | **291** | **292** | 274 | 285 | 285.5 |
| `CONNECT(0,1)` | 266 | 287 | **328** | **302** | 295.8 |
| `CONNECT(1,2)` | 275 | 275 | 289 | 275 | 278.5 |

The best action changes with the future, two of four each way. And the number that launched this entire line of work does not survive: against the one real future `CONNECT(0,2)` scored 275 and `CONNECT(0,1)` scored 380, a gap of 105. **In expectation the gap is about 10.**

### Why this was invisible

The determinism and fidelity checks were both correct, and both irrelevant to the actual defect. They proved the rollout reproduces *one* future exactly — and said nothing about whether one future is enough. I built a careful gate against the failure I had thought of, and it could not see the one I had not.

The reasoning error is specific and worth naming: **the simulator being reproducible was mistaken for the game being deterministic.** Mini Metro's passenger and station spawns are random. A reproducible simulator lets you replay a future; it does not make that future the only one.

Formally this is the winner's curse. A single rollout is a one-sample estimate of a candidate's value; taking the max over noisy one-sample estimates selects the candidate with the luckiest sample rather than the best action, and the selected estimate is biased upward. The measurements show the noise is the size of the signal — candidates differ by 17–54 deliveries within a future, while one *fixed* candidate varies by up to 62 across futures.

### What it explains

Three results that had looked like three separate problems are one problem.

- Search's paired +58.32 over the heuristic is partly foreknowledge. It genuinely delivers those passengers in that game — the score is real — but no reactive policy can reproduce it, because the information it used is not in the observation.
- Distillation stalls at 52% held-out agreement because a fraction of the labels are unlearnable *by construction*: identical observations, different correct answers.
- The distilled policy scores 193.20, statistically indistinguishable from cloning the heuristic at 194.7, because once the luck is averaged out the learnable part of search's policy is close to the heuristic's.

### The fix

Average each candidate over K sampled futures, which estimates E[return | state, action] — a function of the observation, hence learnable in principle, and free of the selection bias. Common random numbers across candidates at a decision point (the same K future keys for everyone) cancel the shared between-future variation so the comparison isolates the action, at no extra cost.

One detail cost a confusing test failure. Reseeding produces *identical* rollout values at 600 and 1,500 decisions and only diverges from about 3,000, because a changed spawn sequence takes time to reach the delivery count. A short check reads as a broken RNG swap when the swap is fine.

### The generalisable lesson

An agent that plans inside a simulator can only be trusted if the simulator's randomness is resampled. Otherwise the planner optimises against a future it has been handed, scores well, and produces training targets that nothing without that same handout can reproduce. The symptom is exactly what was seen here: excellent planner scores, a stubborn imitation ceiling, and a critic that cannot generalise — three findings that invite three separate explanations and have one cause.

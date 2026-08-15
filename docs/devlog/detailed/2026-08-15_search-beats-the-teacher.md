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

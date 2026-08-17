# 2026-08-16 — the episode was 7,600 decisions and 21 of them mattered

## What was believed, and what turned out to be true

The session opened with the semantic lane characterised as a hard learning
problem: nothing learned beats the scripted heuristic, cloning lands at the
blind null, agreement does not predict score, and honest search does not beat
the heuristic either. Four independent architectures and nine experiments had
converged on "the gap is which station pair gets chosen" (E40) and then on "not
even that, because handing over the argmin bought two deliveries" (E41).

Nobody had counted the decisions. Measured this session: **7,989 decisions per
episode, 14.8 of them actions.** Over 99.8% of every rollout was a forced WAIT,
so the policy gradient for the real choices was diluted about 500:1 and credit
for a delivery had to cross thousands of no-ops. That is not a property of Mini
Metro; it is a property of asking for an action every six ticks.

The same probe answered the "most suspicious open fact" the previous session
flagged — 590 of 654 observation floats constant within an episode. **560 are
permanently zero.** The observation is fixed-slot for 20 stations and 4 lines
while a real episode reaches 7-10 stations and 1-3 lines. It is padding.

## What a reviewer would have caught that the author missed — and did

Two wrong gates were built before the right one, and the second is the
instructive one.

**Wrong gate 1**: fast-forward whenever the mask is stable. Scored 0 deliveries
against 525. The heuristic's follow-up moves are already legal when the first is
taken, so the mask does not move, and the gate idled through the 40-second
overcrowding deadline. Acting changes what to do next without changing what is
*possible* — so the gate has to be asymmetric, fast-forwarding only after WAIT.
This one announced itself immediately.

**Wrong gate 2** did not. It read its baseline mask *after* the WAIT step had
already advanced six ticks, so a station spawning inside those ticks became the
baseline and the gate slept a full backstop through the change it exists to wake
for. It passed an 8-seed equivalence check. At n=200 it cost **5 seeds a delayed
action — always the correct action, exactly `wait_backstop` decisions late** —
while moving the mean from 249.29 to 249.50.

A comparison of totals could not have found that, at any n. What found it was
comparing **(decision index, action) pairs per seed**. The first mutation test
written for the fix compared action *lists* and passed with the bug live,
because the defect changes when an action happens and not which one.

## What number moved, and from what

| | queries/episode | mean deliveries | per-seed mismatches vs plain |
| --- | --- | --- | --- |
| plain (as shipped) | 6,859.6 | 249.29 | — |
| gated | **50.9** | 249.50 | **0 of 200** |

Identical deliveries, identical decision counts, identical action sequences, on
200 independent seeds. A 135x reduction in the horizon a learner sees (365x with
the backstop disabled). Training becomes simulation-bound rather than
policy-bound, which is also the first time the previous session's 1.55x
simulation speedup converts into training throughput.

## The audit

`--eval-episodes` was found by accident at the end of the previous session, so
the class was audited rather than the instance: every argparse flag plus
constructor keywords and module constants, traced from parse site to consumer
with the callee's signature actually opened, each suspect handed to an
independent lane told to refute it. **18 suspected, 13 confirmed, 5 refuted.**

The one that reaches furthest back: **`--learning-rate` was dead on every
`--resume`.** SB3's `load()` builds `lr_schedule` from the checkpoint's saved
rate and `_update_learning_rate` reads the schedule, never the attribute the
script assigns afterwards. It is checkable after the fact because SB3 pickles
the live schedule — all eight resumed artifacts on disk carry
`Constant(0.0003)` beside an attribute of 5e-5 or 1e-4, and all twelve
from-scratch checkpoints are clean.

That leaves **E26 unfounded as measured**, not refuted. The KL anchor was
introduced because an unanchored warm start decayed 146.5 → 46.4;
`train_semantic.py`'s own comment blames a *constant* 3e-4 for exactly that
failure and installs a decaying schedule as the cure — into the from-scratch
branch only. The collapse the anchor was built to fix was measured under the
rate the code says causes collapses.

Second-furthest: **`PointerExtractor` never stepped its cursor over the rank
block**, reading `resources` 80 floats early and getting the all-zero tail of
the rank block. It was structurally blind to locomotives, carriages, credits and
the unlock distance, and trained without error. Blast radius checked rather than
assumed: every checkpoint on disk carries `policy_kwargs {}`, so E41 and the
rank-rl runs are the MLP arm and unaffected. E27's pointer comparison was not.

## What this changes about how to attack the goal

Cloning is the wrong objective and has been shown so four independent ways. With
the horizon collapsed, the alternative is affordable: `DEFER` is one extra
action meaning "play what the heuristic would play", so a policy that always
defers *is* the heuristic, action for action, and PPO starts at 257 rather than
at the clone's 189. Deviations are then paid for out of measured deliveries
rather than out of agreement with a teacher.

The honest caveat, stated before any result: such a policy **contains** the
heuristic, so "beats the heuristic" only means something alongside the deviation
rate and an account of what the deviations are. A run that reaches 257 with a 0%
deviation rate has learned nothing and must be reported as such.

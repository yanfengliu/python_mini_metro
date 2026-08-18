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
zero for the whole of that episode.** The observation is fixed-slot for 20
stations and 4 lines while an episode reaches 9 stations and exactly one line.
It is padding.

**Corrected later, and the correction matters:** that count is per-episode, and
the always-zero set differs between episodes, so it is not the number that could
be deleted. Across 48 episodes of two different policies, **512** are never
non-zero in any of them. They still should not be deleted — the domain reaches
20 stations and 4 lines even though today's policy does not, an always-zero
input receives zero gradient and so is inert rather than diluting, and the real
defect is that slot i holds a different station on every board. See E42.

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

**Corrected below.** "PPO starts at 257" was an unmeasured assertion and
it was wrong -- the initialisation was a random-deviation policy worth
211.85. See the second half of this document.

The honest caveat, stated before any result: such a policy **contains** the
heuristic, so "beats the heuristic" only means something alongside the deviation
rate and an account of what the deviations are. A run that reaches 257 with a 0%
deviation rate has learned nothing and must be reported as such.


## The second half of the session: what the gate was built to enable, and what it found

### The headroom was measured before it was optimised, and it is negative

With the horizon collapsed, the plan was a residual policy: DEFER means "play
what the heuristic would play", so training starts at the bar and deviations are
bought with deliveries. Before training, the arbitrary-looking rules were probed
directly -- and the probe is what mattered.

The heuristic crews `legal[kind][0][0]`, "whichever line sits lowest in the
action table". That reads as arbitrary. It is **forced**: across 10 episodes the
crewing rule never once had more than one legal option, and three variants that
change the rule produce byte-identical play. Grafting has exactly two options
every time -- head or tail of **one** line. On 12 seeds the heuristic ends with
`lines=1`, `longest_line == stations`, and unspent line slots.

Opening a spare slot costs **95.07 +/- 24.17 deliveries at n=60**, and every
second-line arm ends the episode *earlier*. The mechanism, measured: the game
grants four metros; both arms deploy all four and end with none spare; a second
line leaves one line carrying **no train for 29% of the episode** against the
heuristic's 4%. Line slots are not scarce. Trains are, and the heuristic already
commits all of them to the only line that can use them.

That single fact retro-explains three ledgered results at once. Honest search
does not beat the heuristic because there is almost nothing to search over.
Agreement never predicted score because the decisions agreement was measured on
have zero or two options. Handing the network the argmin did nothing because the
argmin ranges over two candidates on one line.

### What the critic lanes caught that the author did not

Two lanes, deliberately different: one attacked the gate's equivalence claim,
one attacked the residual design's validity.

The design lane found the defect that invalidated the running experiment. The
claim "always deferring IS the heuristic, so training starts at 257" was never
measured -- and `action_net.weight.mul_(0.01)` on top of SB3's own `ortho_init`
gain of 0.01 left the weights at std 5.2e-6, so the opening policy was "DEFER
with probability p, otherwise uniform over legal actions", worth **211.85, a
-36.92 gap**. Both live arms were un-learning their own initialisation noise
while printing a closing gap. The run now saves an `-init` checkpoint and
reports readout zero before a single gradient step.

The equivalence lane could not break the gate and said so, then proved it harder
than the author had: an independent probe asserting the *ungated* heuristic
would WAIT at every decision the gate skips -- the mechanism, not the end state
-- over ~310,000 skipped decisions on 60 seeds it chose itself, at full episode
length, plus a `wait_backstop` sweep over 1/2/5/50/200/5000/100000. Zero
divergences, so the backstop is also proved not to be a knob that quietly tunes
the baseline. That probe is now a test.

It also found two statements in the author's own comments that were simply
false. "The heuristic never reaches the backstop" -- it reaches it on **83.9%**
of WAIT decisions, so most of the shipped 135x is fixed frame-skip rather than
event structure. And "a restricted class cannot score above the unrestricted
one, so the gate is a valid instrument" does not license the converse: a gated
WAIT blinds the policy for 19.2 seconds against a 40-second overcrowding clock,
and passenger pressure is exactly what the mask does not encode, so a policy
that loses **under** the gate has not been shown to lose ungated. The heuristic
is immune only because it ignores passengers entirely.

Ten further defects landed in the measurement harness itself -- including an
`mde` byte-identical to the 95% CI (43% too permissive against this repo's own
MDE(80%) convention), a `random` null that played the scripted heuristic 92% of
the time because DEFER was in the mask it sampled from, a readout that printed
W/L while hiding that 36 of 50 seeds were exact ties, and `unittest.main()`
above the last test class so `python test/test_event_gate.py` ran 18 of 24 tests
and reported green.

### Where this leaves the goal

Not achieved, and the reason is now specific rather than mysterious. The task as
configured is a four-train fleet on one line, the heuristic saturates it, and
its decisions have one or two options each. A learned policy that beats it has
to find its advantage inside a choice set that small -- or the game's own
parameters have to change, which is a different project and a priced one.

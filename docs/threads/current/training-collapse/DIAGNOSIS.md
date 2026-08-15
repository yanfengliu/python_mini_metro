# Training collapse: done-condition and search

Three runs have collapsed to zero after learning to play. Two fixes were shipped
against causes that were never verified (checkpointing, then learning-rate
decay); the second made the collapse arrive *earlier*. This file fixes what
counts as an answer before any more approaches are tried, per
`../fleet/docs/skills/hard-problem.md`.

## The fixed reproduction

One command, one number, unchanged for the rest of the search:

```
python scripts/collapse_probe.py --steps 400000 --seed 42
```

It reports three values from a single training run:

- `peak` — highest `ep_rew_mean` reached
- `final` — `ep_rew_mean` over the last 10 logged rows
- `retention` — `final / peak`

**Collapse is `retention < 0.25`.** A candidate fix passes only if it reaches a
peak of at least 40 deliveries *and* retains at least 0.75 of it. Both halves
matter: a run that never learns cannot collapse, and would otherwise "pass".

## What the evidence already says

`value_loss` and `explained_variance` are **exonerated as causes**. In v5 the
value loss *fell* to 0.0024 and explained variance *rose* to 0.94 at the moment
of collapse. Those are consequences of a policy that stopped acting -- returns
became constant and trivially predictable. Any approach premised on value-scale
blowup is already contradicted by the logs.

The learning rate is **exonerated as the primary cause**. v5 ran a decaying rate
and collapsed at ~325k, *earlier* than v4's ~500k at a flat rate.

The one variable that separates outcomes:

| run | layouts per episode | peak | outcome |
| --- | --- | --- | --- |
| v3 | one repeated board | 222 | never collapsed |
| v4 | fresh every episode | 97.5 | collapsed ~500k |
| v5 | fresh every episode | ~52 | collapsed ~325k |

v3 is the only run that did not collapse and the only one without layout
diversity. The seeding fix that introduced diversity is therefore the leading
suspect, which is uncomfortable because that fix was correct on its own terms --
training on one board is not training.

## Disqualifier list

Written now, with no candidate to be attached to. A result that does any of the
following is **not** a fix:

1. **Passes by not learning.** Retention is high because the peak never rose
   above ~20. The done-condition requires peak >= 40 for this reason.
2. **Passes by shortening the run.** Collapse onset moved past the horizon rather
   than being removed. Any candidate that passes at 400k must also be shown at
   600k before it is believed.
3. **Passes only on seed 42.** Layout diversity is the suspected mechanism, so a
   fix validated on one training seed proves nothing. Two seeds minimum.
4. **Passes because evaluation got quieter.** The 5-episode eval has a measured
   repeat spread of 30.8-58.6 on a fixed policy and fixed seeds. Scoring must use
   `ep_rew_mean` over training episodes, never the small held-out eval.
5. **Reverts diversity.** Returning to a single fixed board would "pass" and is
   the one outcome known in advance to be worthless -- it reintroduces the defect
   the seeding fix removed.
6. **Relocates the problem.** A candidate that requires a working curriculum, a
   working reward normaliser, or "just needs tuning" has renamed the difficulty,
   not removed it.
7. **The collapse went quiet rather than away.** Score is retained but entropy
   still explodes, or the policy survives by degenerating into WAIT-only play
   that happens to score through simulation rather than through decisions.

## Approach families

Kept deliberately distinct by *mechanism*, not by wording. Registry, so a
crowded family can be spotted:

- **A. Return-scale / normalisation.** Episode returns span 0 to 383 across
  layouts. Normalise returns, clip rewards, or reduce gamma so targets stay
  bounded.
- **B. Entropy dynamics.** The measured signature is an entropy explosion.
  Entropy coefficient schedule, KL-targeted early stopping, or a hard trust
  region.
- **C. Layout-difficulty variance.** Diverse boards give wildly different
  achievable returns, so an advantage computed across them mixes "bad policy"
  with "hard board". Per-layout baselines, or curriculum ordering.
- **D. Episode-length / credit assignment.** Episodes run 400 to 5,000+
  decisions against `n_steps=256`; an episode spans ~20 rollouts and GAE
  bootstraps across all of them.
- **E. Prior art.** Known PPO collapse modes in long-horizon, high-variance,
  masked-action settings. Cheapest branch and explicitly in the portfolio.

## SUPERSEDED diagnosis (kept for the record; see the correction below)

**Mechanism, evidenced:** the collapse is an *absorbing state* that recreates the
zero-reward condition PPO cannot escape.

1. **Removing a line is free.** From identical restored states under the same
   policy, the next 800 decisions return **18.3 if the line is kept and 18.7 if
   it is removed** (6 states, paired). One removal costs nothing, because the
   policy simply rebuilds.
2. **So no gradient ever opposes it.** An action with zero advantage is not
   pushed away from, and the entropy bonus actively pushes toward whatever is
   unexplored. The policy drifts onto REMOVE.
3. **Drift becomes self-sustaining.** The collapsed policy chooses REMOVE as
   argmax in **73% of states while it is only 17% of the legal set** -- over 4x
   its availability, so this is learned preference, not exposure. In that regime
   no line survives long enough to deliver.
4. **The absorbing state has no gradient out.** With every episode returning 0,
   every advantage is 0 and the policy gradient is the zero vector -- the exact
   condition measured in E4, where 3M steps produced no learning. Arrived at from
   above rather than from below, but identical.

**What this rules out.** Not a value-scale problem: `value_loss` fell to 0.0024
and `explained_variance` rose to 0.94 at collapse. Not a step-size problem: the
decaying rate collapsed *earlier*. Not an action-space confound: v3 and v5 both
run `Discrete(364)`, so v3 had REMOVE available and still never collapsed --
diversity changes how often the drift is sampled, not whether the trap exists.

**Why prior art fits.** [No Representation, No
Trust](https://arxiv.org/html/2405.00662v3) reports that around collapse the
trust region breaks down along with the representation. That predicts the
`target-kl` branch fails: a trust region constrains *how far* the policy moves,
and this trap is entered by many individually-free steps, none of which any KL
bound would reject.

**The single sentence:** an individually costless action that is collectively
fatal will be drifted into, and the state it leads to has no gradient back out.

---

## Correction (move 4: the adversarial audit killed it)

**The diagnosis above is refuted.** An adversarial reviewer was asked to break it
and broke it on five points, three of which I re-verified independently.

**1. Removal is not free -- it COSTS.** Replicating the paired measurement at
n=48 instead of n=6, at the same 800-decision horizon: keep 21.04, remove 18.23,
paired difference **-2.81, 95% CI [-4.53, -1.10]**. The sign is reversed. Measured
paired sd is 6.06, so n=6 gives a half-width of +/-6.36 -- 2.3x the true effect,
with roughly **8% power**. Two numbers quoted to 0.1 from an instrument whose
resolution was +/-6.4, on a bimodal outcome, which is the third time this exact
error has been made here (E9, E18, now this).

**2. The availability denominator was wrong.** The 17% figure comes from *random
play's* state distribution. In the states a competent policy actually occupies I
measure a mean legal set of **3.26** with **81.5% offering only WAIT or REMOVE**
(the reviewer measured 2.03 and 98.9% on the v3 policy). Against the right
denominator, 73% argmax is ~1.5x availability, not 4x.

**3. The collapsed policy has no REMOVE preference in probability mass.** Masked
entropy **1.020 nats against the healthy policy's 0.019** -- it is near-uniform
over the legal set (86% of uniform vs 2%). PPO samples from mass, not argmax, and
E20 already recorded that argmax is misleading on this task.

**4. It is not an absorbing state.** Verified in this repo's own v4 log: peak
102.0, falls to **34.2 at 714k, then recovers to 47.1**. A state whose gradient is
identically zero cannot recover. Only v5 reached ~0, and it was stopped 58k steps
later -- the one run allowed to continue past a decline is the one that recovered.

**5. The reproduction never reproduced.** Confirmed independently: the baseline
passes at 0.934 retention and its peak is the *last logged rollout*, still rising.

### The corrected chain

Something destroys the policy's **sharpness** (entropy 0.019 -> 1.020). Because
81-99% of the states a competent policy occupies offer only WAIT or REMOVE, any
loss of sharpness converts directly into a destroyed network scoring what random
legal play scores. **REMOVE is the transmission, not the driver.** Penalising it
removes the transmission, leaves the driver, and hands the agent a free floor --
random legal play that merely never removes scores **181.67**, above every peak in
this entire search.

The unlagged clock (the held-out eval, not the 100-episode-lagged `ep_rew_mean`)
puts **entropy first**: it starts rising at ~274k, before the eval dies at 300k,
while `value_loss` only crashes at 311k -- after the policy is already worthless.
That promotes family B, which the superseded diagnosis argued against.

### What the search is now

Branches `ent0` (ent_coef 0.0) and `ent001` (0.001) against the collapsing
configuration at 900k steps -- past v4's ~500k decline, since the old 400k horizon
demonstrably stopped short. The question is whether the constant entropy pressure
toward uniform-over-legal is what erodes sharpness once the advantage signal
weakens.

**New disqualifier, learned from the audit:** any candidate must be scored against
**random-legal-never-removes (181.67)**, not against zero. Both previously proposed
fixes fail this -- `--remove-min-age 200` lets *random play* score 45.67 and clear
`MIN_PEAK=40` with retention ~1.0, passing having learned nothing.

## Status

Move 1 complete; the reproduction is `scripts/collapse_probe.py`. Three branches
(baseline, return normalisation, target-KL) are running against it. The diagnosis
above is measured but the *fix* is not yet scored -- candidate interventions must
make removal cost something, or make the absorbing state unreachable, and must
still clear the disqualifier list.

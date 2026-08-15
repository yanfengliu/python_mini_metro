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

## Status

Move 1 complete. No approach has been scored against the reproduction yet.

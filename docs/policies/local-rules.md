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

- **Evaluation is never assisted.** No shaping wrapper, no privileged channel, no teacher actions. A held-out evaluation that quietly includes exploration credit corrupts not just its own number but every comparison built on it.

## Game changes in service of the agent

- **The observation is a design surface, not a given.** Render scale, entity sizes and contrast are as legitimate to change as the network, and are sometimes the cheaper fix — a passenger 0.5 px wide is destroyed before any architecture sees it. Weigh the two together rather than treating the game as fixed.

- **But changing the game is the more expensive lever, so price it.** Render or mechanic changes rotate task fingerprints, invalidate trained policies and saved runs, and are locally high-risk under `AGENTS.md`. Re-derive how much game change is still needed *after* the model-side fix, rather than inheriting a number sized against the old model.

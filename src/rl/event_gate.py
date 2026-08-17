"""Query the policy at decision points, not every 6 ticks.

`SemanticMetroEnv` asks for an action every `TICKS_PER_DECISION`, so a full
episode is thousands of decisions -- and the scripted heuristic acts on about
15 of them. Measured over 200 seeds: 6,860 decisions per episode, 14 actions.
So over 99.8% of every rollout is spent emitting WAIT, the policy gradient for
the handful of real choices is diluted about 500:1, and a delivery's credit has
to travel back across thousands of no-ops. That is not a hard game; it is a hard
*presentation* of an easy-to-present game.

**What the gate does.** After the policy chooses WAIT, the simulation is
fast-forwarded -- still WAITing, still accruing deliveries -- until the action
mask changes, or a backstop expires. After any other action the policy is
re-queried on the very next decision.

**Why that is free.** The heuristic's choice is a pure function of station
positions, the served set, and the mask. None of the three can move while the
mask stands still: a new station index makes fresh CONNECT/EXTEND/PREPEND
entries legal, and only an agent action changes line membership. Measured on 8
200 independent seeds, deliveries, decision counts and the whole (decision,
action) sequence are identical with the gate and without it, at 50.9 policy
queries per episode against 6,860 -- a 135x reduction at the shipped
`wait_backstop`. With the backstop disabled the purely event-driven count is
about 19 queries, or 332x; those are the numbers for a different setting and
are not what this ships with.

**The asymmetry is load-bearing.** An earlier version fast-forwarded after every
action, not just after WAIT. It scored 0 deliveries against 525, because the
heuristic's follow-up moves (graft the second station, then crew the line) are
already legal when the first one is taken, so the mask does not move and the
gate sat idle for the whole backstop while the run died at the 40-second
overcrowding deadline. Acting changes what to do next without changing what is
*possible*; `test_event_gate.py` pins that.

**What it costs, stated carefully.** The gate cannot inflate a learned score:
the policy acts strictly less often, and the bar it is measured against
provably scores the same either way. The converse does NOT follow, and an
earlier version of this note claimed it did. A gated WAIT blacks the policy
out for up to `wait_backstop` decisions -- 19.2 game-seconds against a
40-second overcrowding clock -- and passenger pressure is exactly what the
mask does not encode, so a policy that loses to the heuristic UNDER the gate
has not been shown to lose to it ungated. The heuristic is immune only
because it ignores passengers entirely. (The subset argument is also weaker
than it looks: expressing gated-WAIT requires remembering the mask the policy
decided against, which a Markov policy cannot do, so the gated class is a
subset of the history-dependent ungated class rather than of the Markov one.)

**DEFER**, optional, is the second half. It is one extra action meaning "play
whatever the heuristic would play here". A policy that always defers *is* the
heuristic, so residual training starts at the bar (263) rather than 80
deliveries below it at the blind null (183), and every deviation it learns is
paid for out of measured return rather than out of agreement with a teacher.
Agreement has never once predicted score on this task across the 0-83% range,
which is the argument for optimising the outcome at the decision points instead.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from rl.semantic_env import (
    ACTION_TABLE,
    MAX_STATIONS,
    ActionKind,
    SemanticMetroEnv,
)

# 20 game-seconds. It exists so WAIT is never absorbing and a learned policy
# can still act on passenger pressure, which does not move the mask.
#
# It is NOT rarely reached: measured over 16 seeds, 457 of 545 WAIT decisions
# (83.9%) end at the backstop rather than at a mask change. So most of the
# query reduction at this default is fixed frame-skip, not event structure --
# the purely event-driven count is 19 queries per episode (332x) against 51
# here (135x). What IS established is that the value cannot move the anchor:
# sweeping it over 1, 2, 5, 50, 200, 5000 and 100000 across 16 seeds leaves
# the heuristic's deliveries, decision counts and action sequence identical in
# all 112 episodes, so it is not a knob that quietly tunes the baseline.
DEFAULT_WAIT_BACKSTOP = 200

# One-hot over ActionKind, plus the two table arguments normalised by
# MAX_STATIONS. Small on purpose: it says what DEFER would do, nothing more.
PROPOSAL_FEATURES = len(ActionKind) + 2

# The table's arguments are station and line indices, so MAX_STATIONS bounds
# both. Written out rather than as the constant 20 it happened to equal: the
# previous expression evaluated to 20.0 unconditionally while its comment
# claimed to normalise by MAX_STATIONS, so raising MAX_STATIONS would have
# silently pushed the proposal block outside its declared Box(-1, 1).
_NORMALISER = float(MAX_STATIONS)

# How much of the table a deviation may reach.
#
#   "all"  -- every legal action. The general question: is there a better move
#             anywhere, including acting where the heuristic idles?
#   "kind" -- only the other arguments of the kind the heuristic just chose,
#             plus WAIT. The sharp question, aimed at a known arbitrariness:
#             the heuristic crews `legal[kind][0][0]`, which is whichever line
#             happens to sit lowest in the table, and grafts onto whichever end
#             is nearest without regard to what that line is already carrying.
#             With the proposal itself reachable only through DEFER this leaves
#             a handful of options per decision instead of about thirty, so the
#             same number of episodes buys far more signal per option.
DEVIATION_SCOPES = ("all", "kind")


_TABLE_KIND = np.array([int(kind) for kind, _, _ in ACTION_TABLE], dtype=np.int64)


class EventGatedSemanticEnv(gym.Env):
    """`SemanticMetroEnv` queried at decision points, optionally with DEFER."""

    metadata = {"render_modes": []}
    PROPOSAL_FEATURES = PROPOSAL_FEATURES

    def __init__(
        self,
        *,
        wait_backstop: int = DEFAULT_WAIT_BACKSTOP,
        defer: bool = False,
        proposal_features: bool = False,
        deviation_scope: str = "all",
        **inner_kwargs,
    ):
        super().__init__()
        if proposal_features and not defer:
            raise ValueError(
                "proposal_features describes what DEFER would do, so it needs "
                "defer=True; pass defer=True or drop proposal_features"
            )
        if deviation_scope not in DEVIATION_SCOPES:
            raise ValueError(
                f"deviation_scope must be one of {sorted(DEVIATION_SCOPES)}, got "
                f"{deviation_scope!r}; 'all' offers every legal action, 'kind' "
                "offers only the arguments of the kind the heuristic chose"
            )
        if deviation_scope != "all" and not defer:
            raise ValueError(
                f"deviation_scope={deviation_scope!r} is defined relative to the "
                "heuristic's proposal, so it needs defer=True"
            )
        self.inner = SemanticMetroEnv(**inner_kwargs)
        self.wait_backstop = int(wait_backstop)
        if self.wait_backstop < 1:
            raise ValueError(
                f"wait_backstop must be at least 1 decision, got {wait_backstop}; "
                "it bounds how long a WAIT may fast-forward"
            )
        self._defer = bool(defer)
        self._proposal = bool(proposal_features)
        self._scope = deviation_scope
        self.decisions = 0

        size = len(ACTION_TABLE) + (1 if self._defer else 0)
        self.DEFER = len(ACTION_TABLE) if self._defer else None
        self.action_space = spaces.Discrete(size)
        width = self.inner.observation_space.shape[0] + (
            PROPOSAL_FEATURES if self._proposal else 0
        )
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(width,), dtype=np.float32
        )

    # -- observation -------------------------------------------------------

    def _proposal_block(self) -> np.ndarray:
        from rl.heuristic import choose

        block = np.zeros(PROPOSAL_FEATURES, dtype=np.float32)
        kind, first, second = ACTION_TABLE[choose(self.inner)]
        block[int(kind)] = 1.0
        block[len(ActionKind)] = first / _NORMALISER
        block[len(ActionKind) + 1] = second / _NORMALISER
        return block

    def observe(self) -> np.ndarray:
        """The current observation, rebuilt from the live game."""
        inner = self.inner._observe()
        if not self._proposal:
            return inner
        return np.concatenate([inner, self._proposal_block()]).astype(np.float32)

    def action_masks(self) -> np.ndarray:
        mask = self.inner.action_masks()
        if not self._defer:
            return mask
        if self._scope == "kind":
            from rl.heuristic import choose

            wanted = ACTION_TABLE[choose(self.inner)][0]
            keep = _TABLE_KIND == int(wanted)
            keep[0] = True  # WAIT is always a legitimate alternative.
            mask = mask & keep
        # DEFER is always legal: `choose` only ever returns a legal index, and
        # WAIT is legal in every state, so deferring can never be a no-op.
        return np.concatenate([mask, np.ones(1, dtype=bool)])

    # -- rollout -----------------------------------------------------------

    def reset(self, *, seed: int | None = None, options=None):
        super().reset(seed=seed)
        self.inner.reset(seed=seed, options=options)
        self.decisions = 0
        return self.observe(), {}

    def fast_forward(self, held: np.ndarray | None = None):
        """Advance on WAIT until the option set changes or the backstop expires.

        `held` is the mask the policy SAW when it chose to wait, and defaults to
        the current one only for callers with nothing better. `step` passes the
        pre-decision mask, and the difference is not cosmetic: a WAIT advances
        six ticks before this runs, so a station spawning inside those ticks
        moves the mask immediately. Reading the mask here adopted that new state
        as the baseline and then slept through it for a whole backstop.

        Measured on 200 seeds, that cost 5 of them a delayed action -- always
        the right action exactly `wait_backstop` decisions late (411 -> 611,
        3033 -> 3233) -- while the mean moved only 249.29 to 249.50, which is
        why it was invisible until the action sequences were compared per seed.

        Returns the same 5-tuple as `step`, with the reward summed over every
        decision skipped. Public because the equivalence test drives it directly
        to reproduce the defect the WAIT-only asymmetry exists to prevent.
        """
        if held is None:
            held = self.inner.action_masks()
        total = 0.0
        terminated = truncated = False
        for _ in range(self.wait_backstop):
            if not np.array_equal(self.inner.action_masks(), held):
                break
            _, reward, terminated, truncated, info = self.inner.step(0)
            total += float(reward)
            self.decisions += 1
            if terminated or truncated:
                return self.observe(), total, terminated, truncated, info
        return self.observe(), total, terminated, truncated, {"applied": True}

    def step(self, action):
        chosen = int(np.asarray(action).ravel()[0])
        # The mask the policy is deciding against, captured before the step
        # advances the game. See `fast_forward`.
        seen = self.inner.action_masks()
        proposal = 0
        deviated = False
        if self._defer:
            from rl.heuristic import choose

            # Always resolved, not only when DEFER is played, so `deviated`
            # counts what the policy actually did DIFFERENTLY. Naming the
            # proposal explicitly is a no-op that a naive counter reads as a
            # deviation, and under deviation_scope="kind" most decisions offer
            # exactly {WAIT, DEFER} with the heuristic already proposing WAIT --
            # so that counter would report constant activity from a policy that
            # has changed nothing.
            proposal = choose(self.inner)
            if chosen == self.DEFER:
                chosen = proposal
            deviated = chosen != proposal
        _, reward, terminated, truncated, info = self.inner.step(chosen)
        total = float(reward)
        self.decisions += 1
        if not (terminated or truncated) and chosen == 0:
            _, extra, terminated, truncated, tail = self.fast_forward(seen)
            total += float(extra)
            info = dict(tail)
        info = dict(info)
        info["proposal"] = proposal
        info["deviated"] = deviated
        info["decisions"] = self.decisions
        return self.observe(), total, terminated, truncated, info

    def close(self):
        self.inner.close()

"""Training-time reward shaping, applied as a wrapper so the task is unchanged.

Under the environment's own reward the first passenger is unreachable by
exploration. Drawing a line needs pointer-down on a roughly ten-pixel station,
motion, then pointer-up on a *different* station, and across 12 random episodes
and 4170 decisions none occurred. Every reward in a batch is then zero, the
advantage is zero, and the policy gradient is the zero vector -- there is nothing
to descend, at any quantity of steps.

Shaping pays partial credit for the sub-events of that conjunction so the pieces
become individually learnable.

This is deliberately a wrapper rather than a ``RewardMode``. Adding a member to
that enum rotates the protocol fingerprint, which breaks task reconstruction for
every previously saved model -- the suite caught exactly that. The distinction is
also honest: the task is "deliver passengers", and shaping is scaffolding used
while learning it. Evaluation wraps nothing and scores true deliveries.
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym

# One station joined onto a usable route is worth this much, so a whole opening
# route stays well under a single delivery and cannot outweigh the objective it
# exists to lead toward.
CONNECTION_CREDIT = 0.1


def count_connected_stations(mediator: Any) -> int:
    """Station slots sitting on a route of at least two stations."""
    return sum(len(path.stations) for path in mediator.paths if len(path.stations) >= 2)


class ConnectionShapedReward(gym.Wrapper):
    """Add credit for joining stations onto a route, on top of the real reward.

    The credit follows a high-water mark rather than the live count. A reward
    paid for the *state* of having a line can be farmed by erasing and redrawing
    it; a monotone best-ever total cannot.
    """

    def __init__(self, env: gym.Env, credit: float = CONNECTION_CREDIT):
        super().__init__(env)
        if credit <= 0:
            raise ValueError(f"credit must be positive, received {credit!r}")
        self.credit = float(credit)
        self._best_connected = 0

    def _mediator(self):
        node = self.env
        for _ in range(8):
            mediator = getattr(node, "_mediator", None)
            if callable(getattr(node, "_require_mediator", None)):
                return node._require_mediator()
            if mediator is not None:
                return mediator
            node = getattr(node, "env", None)
            if node is None:
                break
        raise RuntimeError(
            "ConnectionShapedReward could not reach the mediator through the "
            "wrapper chain; it must wrap a PlayerPixelEnv"
        )

    def reset(self, **kwargs):
        self._best_connected = 0
        return self.env.reset(**kwargs)

    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        connected = count_connected_stations(self._mediator())
        gained = connected - self._best_connected
        if gained > 0:
            self._best_connected = connected
            reward = float(reward) + self.credit * gained
            info = {**info, "shaping_credit": self.credit * gained}
        return observation, reward, terminated, truncated, info

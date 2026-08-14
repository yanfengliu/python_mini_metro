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

from rl.protocol import ActionKind, canonical_to_action_coordinate

# One station joined onto a usable route is worth this much, so a whole opening
# route stays well under a single delivery and cannot outweigh the objective it
# exists to lead toward.
CONNECTION_CREDIT = 0.1

# Paid on a pointer-down for landing near a station. This is the DENSE half
# and the one that actually unblocks exploration: connection credit alone
# was measured at 0 across 24 random episodes and 8721 decisions, because
# it rewards precisely the event random play never reaches.
PROXIMITY_CREDIT = 0.02

# Beyond this fraction of the screen diagonal a pointer-down earns nothing,
# so the gradient stays local instead of rewarding vaguely central clicks.
PROXIMITY_RANGE = 0.25

# Total proximity credit an episode may earn. Without a ceiling the dense
# signal is farmable: 0.02 on every pointer-down over a 4000-decision
# episode is 80, against roughly 20 for actually playing well, so the best
# policy would be to stand next to a station and click forever. The budget
# keeps it a bootstrap that cannot outrank the objective.
PROXIMITY_BUDGET = 1.0


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
        self._proximity_spent = 0.0

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

    def _proximity_credit(self, mediator, action) -> float:
        """Reward a pointer-down for landing near a station.

        Connection credit is a milestone an exploring policy never reaches, so
        on its own it leaves the gradient at zero. This is available on every
        pointer-down and rises smoothly as the click approaches a station,
        which is what turns 'hit a ten-pixel target' into something learnable.
        """

        if int(action[0]) != int(ActionKind.DOWN.value):
            return 0.0
        stations = getattr(mediator, "stations", ())
        if not stations:
            return 0.0
        profile = self.env.unwrapped.task_spec.render_profile
        pointer_x, pointer_y = int(action[1]), int(action[2])
        reach = PROXIMITY_RANGE * ((profile.width**2 + profile.height**2) ** 0.5)
        best = None
        for station in stations:
            position = station.position
            station_x, station_y = canonical_to_action_coordinate(
                int(position.left), int(position.top), profile
            )
            distance = (
                (station_x - pointer_x) ** 2 + (station_y - pointer_y) ** 2
            ) ** 0.5
            if best is None or distance < best:
                best = distance
        if best is None or best >= reach:
            return 0.0
        credit = PROXIMITY_CREDIT * (1.0 - best / reach)
        remaining = PROXIMITY_BUDGET - self._proximity_spent
        credit = min(credit, max(0.0, remaining))
        self._proximity_spent += credit
        return credit

    def reset(self, **kwargs):
        self._best_connected = 0
        self._proximity_spent = 0.0
        return self.env.reset(**kwargs)

    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        mediator = self._mediator()
        reward = float(reward) + self._proximity_credit(mediator, action)
        connected = count_connected_stations(mediator)
        gained = connected - self._best_connected
        if gained > 0:
            self._best_connected = connected
            reward = float(reward) + self.credit * gained
            info = {**info, "shaping_credit": self.credit * gained}
        return observation, reward, terminated, truncated, info

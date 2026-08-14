"""Training-time reward shaping, applied as a wrapper so the task is unchanged.

Under the environment's own reward the first passenger is unreachable. Drawing a
line needs pointer-down on a roughly ten-pixel station, motion, then pointer-up
on a *different* station, and across 12 random episodes and 4170 decisions none
occurred. Every reward in a batch is then zero, the advantage is zero, and the
policy gradient is the zero vector.

Two measured failures shaped what this is now.

Paying only for the finished milestone ("a usable line exists") fired **zero
times in 24 random episodes** -- it rewards precisely the event exploration
cannot reach, so it reproduces the zero it was built to remove.

Paying only for pointer-down proximity was reachable, and did active harm. After
300,000 steps the policy chose pointer-down 63.5% of the time against a 12.5%
uniform, while **motion fell to 4.6% and pointer-up to 2.9%, both below
uniform**. PPO correctly inferred those actions paid less, so the shaping taught
the agent to stop performing the two actions a drag requires. A reward covering
one step of a sequence does not merely fail to teach the sequence; it suppresses
the rest of it.

So the credit is a *ladder* over the whole gesture, each rung reachable from the
one below: approach a station, hold a drag open, then land it on a different
station. Every rung carries its own per-episode budget, because a dense signal
without a ceiling is farmable -- one uncapped rung was worth ~80 against the
~19-20 real play earns.

This is a wrapper rather than a ``RewardMode`` because adding an enum member
rotates the protocol fingerprint and breaks task reconstruction for every saved
model. It is also the more honest shape: the task is "deliver passengers", and
this is scaffolding used while learning it. Evaluation wraps nothing.
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym

from rl.protocol import ActionKind, canonical_to_action_coordinate

# Rung 1: a pointer-down lands near a station.
PROXIMITY_CREDIT = 0.02
PROXIMITY_RANGE = 0.25
PROXIMITY_BUDGET = 1.0

# Rung 2: motion while a drag is open. Small, but its real job is to stop motion
# being driven below uniform by the rung beneath it.
DRAG_MOTION_CREDIT = 0.01
DRAG_MOTION_BUDGET = 0.5

# Rung 3: a pointer-up landing on a different station, completing the gesture.
DRAG_COMPLETE_CREDIT = 0.25
DRAG_COMPLETE_BUDGET = 1.0

# Milestone: stations joined onto a usable route, on a high-water mark so it
# cannot be farmed by erasing and redrawing the same line.
CONNECTION_CREDIT = 0.1

# A pointer within this many action pixels of a station centre counts as on it.
STATION_HIT_RADIUS = 4.0


def count_connected_stations(mediator: Any) -> int:
    """Station slots sitting on a route of at least two stations."""
    return sum(len(path.stations) for path in mediator.paths if len(path.stations) >= 2)


class ConnectionShapedReward(gym.Wrapper):
    """Ladder of credit over the drag gesture, on top of the real reward."""

    def __init__(self, env: gym.Env, credit: float = CONNECTION_CREDIT):
        super().__init__(env)
        if credit <= 0:
            raise ValueError(f"credit must be positive, received {credit!r}")
        self.credit = float(credit)
        self._reset_shaping()

    def _reset_shaping(self) -> None:
        self._best_connected = 0
        self._proximity_spent = 0.0
        self._motion_spent = 0.0
        self._complete_spent = 0.0
        self._drag_origin: int | None = None

    def _mediator(self):
        node = self.env
        for _ in range(8):
            if callable(getattr(node, "_require_mediator", None)):
                return node._require_mediator()
            node = getattr(node, "env", None)
            if node is None:
                break
        raise RuntimeError(
            "ConnectionShapedReward could not reach the mediator through the "
            "wrapper chain; it must wrap a PlayerPixelEnv"
        )

    def _nearest_station(self, mediator, x: int, y: int):
        """Index of and distance to the closest station, in action coordinates."""
        profile = self.env.unwrapped.task_spec.render_profile
        best_index, best_distance = None, None
        for index, station in enumerate(getattr(mediator, "stations", ())):
            position = station.position
            station_x, station_y = canonical_to_action_coordinate(
                int(position.left), int(position.top), profile
            )
            distance = ((station_x - x) ** 2 + (station_y - y) ** 2) ** 0.5
            if best_distance is None or distance < best_distance:
                best_index, best_distance = index, distance
        return best_index, best_distance

    def _spend(self, name: str, amount: float, budget: float) -> float:
        spent = getattr(self, name)
        allowed = min(amount, max(0.0, budget - spent))
        setattr(self, name, spent + allowed)
        return allowed

    def _gesture_credit(self, mediator, action) -> float:
        kind = int(action[0])
        x, y = int(action[1]), int(action[2])
        profile = self.env.unwrapped.task_spec.render_profile

        if kind == int(ActionKind.DOWN.value):
            index, distance = self._nearest_station(mediator, x, y)
            if distance is None:
                return 0.0
            self._drag_origin = index if distance <= STATION_HIT_RADIUS else None
            reach = PROXIMITY_RANGE * ((profile.width**2 + profile.height**2) ** 0.5)
            if distance >= reach:
                return 0.0
            return self._spend(
                "_proximity_spent",
                PROXIMITY_CREDIT * (1.0 - distance / reach),
                PROXIMITY_BUDGET,
            )

        if kind == int(ActionKind.MOTION.value) and self._drag_origin is not None:
            return self._spend("_motion_spent", DRAG_MOTION_CREDIT, DRAG_MOTION_BUDGET)

        if kind == int(ActionKind.UP.value):
            origin, self._drag_origin = self._drag_origin, None
            if origin is None:
                return 0.0
            index, distance = self._nearest_station(mediator, x, y)
            if distance is None or distance > STATION_HIT_RADIUS or index == origin:
                return 0.0
            return self._spend(
                "_complete_spent", DRAG_COMPLETE_CREDIT, DRAG_COMPLETE_BUDGET
            )

        return 0.0

    def _connection_credit(self, mediator) -> float:
        connected = count_connected_stations(mediator)
        gained = connected - self._best_connected
        if gained <= 0:
            return 0.0
        self._best_connected = connected
        return self.credit * gained

    def reset(self, **kwargs):
        self._reset_shaping()
        return self.env.reset(**kwargs)

    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        mediator = self._mediator()
        bonus = self._gesture_credit(mediator, action)
        bonus += self._connection_credit(mediator)
        if bonus:
            reward = float(reward) + bonus
            info = {**info, "shaping_credit": bonus}
        return observation, reward, terminated, truncated, info

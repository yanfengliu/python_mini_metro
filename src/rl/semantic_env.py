"""A semantic environment: choose stations and lines, not pixels.

The pixel task's difficulty turned out to be almost entirely targeting precision.
A station covers about 0.034% of the coordinate grid, so a random click lands on
one roughly 0.1% of the time, and drawing a line needs two such hits in sequence
-- about one in a million. Measured consequences: random play built a usable line
in 0 of 48 episodes, three separately configured PPO runs delivered exactly zero
across 3M, 300k and 600k steps, and Go-Explore reached lines only by archiving
lucky states and then stalled on a smaller target still, the locomotive control.

None of that difficulty is Mini Metro. It is the cost of expressing "connect
these two stations" as a pair of pixel coordinates.

So this environment removes the pixels from both sides. The agent is handed the
things the game is actually about -- where the stations are, what shape each one
is, who is waiting and for what -- and acts by naming stations and lines. Every
action is meaningful; there is no way to click on nothing.

The pixel environment is unchanged and remains the player-equivalent task. This
is the separate structured lane that `docs/rl-model-selection.md` pre-registers,
and results from the two are not interchangeable: this one is strictly easier
and cannot be quoted as a pixel-task score.
"""

from __future__ import annotations

from enum import IntEnum

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from config import screen_height, screen_width
from mediator import Mediator

MAX_STATIONS = 20
MAX_PATHS = 4
SHAPE_SLOTS = 8

# One decision advances this many simulation ticks, matching the pixel task's
# pacing so episode lengths and delivery totals stay comparable.
TICKS_PER_DECISION = 6
DEFAULT_MAX_DECISIONS = 4000


class SemanticAction(IntEnum):
    """What the agent can do, expressed as intent rather than as a gesture."""

    WAIT = 0
    CONNECT = 1
    ASSIGN_LOCOMOTIVE = 2
    ATTACH_CARRIAGE = 3
    REMOVE_LINE = 4


class SemanticMetroEnv(gym.Env):
    """Mini Metro with a structured observation and a structured action space."""

    metadata = {"render_modes": []}

    def __init__(
        self, *, max_decisions: int = DEFAULT_MAX_DECISIONS, seed: int | None = None
    ):
        super().__init__()
        self.max_decisions = int(max_decisions)
        self._mediator: Mediator | None = None
        self._decision = 0
        self._last_deliveries = 0
        self._shape_index: dict[str, int] = {}

        self.action_space = spaces.MultiDiscrete(
            [len(SemanticAction), MAX_STATIONS, MAX_STATIONS]
        )
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self._observation_size(),), dtype=np.float32
        )

    @staticmethod
    def _observation_size() -> int:
        per_station = 3 + SHAPE_SLOTS + SHAPE_SLOTS
        per_path = 4
        globals_ = 5
        return MAX_STATIONS * per_station + MAX_PATHS * per_path + globals_

    def _shape_slot(self, shape) -> int:
        name = getattr(shape, "type", shape)
        name = getattr(name, "name", str(name))
        if name not in self._shape_index:
            self._shape_index[name] = len(self._shape_index) % SHAPE_SLOTS
        return self._shape_index[name]

    def _observe(self) -> np.ndarray:
        mediator = self._mediator
        assert mediator is not None
        values = np.zeros(self._observation_size(), dtype=np.float32)
        cursor = 0
        for slot in range(MAX_STATIONS):
            if slot < len(mediator.stations):
                station = mediator.stations[slot]
                values[cursor] = 1.0
                values[cursor + 1] = station.position.left / screen_width * 2 - 1
                values[cursor + 2] = station.position.top / screen_height * 2 - 1
                values[cursor + 3 + self._shape_slot(station.shape)] = 1.0
                for passenger in station.passengers:
                    slot_index = self._shape_slot(passenger.destination_shape)
                    values[cursor + 3 + SHAPE_SLOTS + slot_index] += 0.1
            cursor += 3 + SHAPE_SLOTS + SHAPE_SLOTS

        for slot in range(MAX_PATHS):
            if slot < len(mediator.paths):
                path = mediator.paths[slot]
                values[cursor] = 1.0
                values[cursor + 1] = len(path.stations) / MAX_STATIONS
                values[cursor + 2] = len(getattr(path, "metros", ())) / 4.0
                values[cursor + 3] = min(1.0, len(path.stations) / 8.0)
            cursor += 4

        values[cursor] = len(mediator.stations) / MAX_STATIONS
        values[cursor + 1] = len(mediator.paths) / MAX_PATHS
        values[cursor + 2] = min(1.0, mediator.line_credits / 8.0)
        values[cursor + 3] = min(1.0, self._decision / self.max_decisions)
        values[cursor + 4] = min(1.0, mediator.deliveries / 50.0)
        return np.clip(values, -1.0, 1.0)

    def reset(self, *, seed: int | None = None, options=None):
        super().reset(seed=seed)
        self._mediator = Mediator(seed=seed if seed is not None else 0)
        self._decision = 0
        self._last_deliveries = 0
        self._shape_index = {}
        return self._observe(), {}

    def action_mask_components(self) -> list[np.ndarray]:
        """Per-component legality, in the form sb3-contrib's MaskablePPO wants.

        Limiting the decision space is the whole point of this lane. Station
        slots run to twenty while a young game has three, so an unmasked
        sampler spends almost every CONNECT on an index that does not exist,
        and a fifth of its actions removing the lines it just built.
        """

        mediator = self._mediator
        assert mediator is not None
        stations = len(mediator.stations)
        paths = len(mediator.paths)

        kinds = np.zeros(len(SemanticAction), dtype=bool)
        kinds[SemanticAction.WAIT] = True
        kinds[SemanticAction.CONNECT] = stations >= 2 and paths < MAX_PATHS
        assignable = any(mediator.can_assign_locomotive(p) for p in mediator.paths)
        attachable = any(mediator.can_attach_carriage(p) for p in mediator.paths)
        kinds[SemanticAction.ASSIGN_LOCOMOTIVE] = assignable
        kinds[SemanticAction.ATTACH_CARRIAGE] = attachable
        # Removing a line is legal but never useful to an exploring policy, so
        # it is masked out rather than left to undo progress at random.
        kinds[SemanticAction.REMOVE_LINE] = False

        # Per-component masks cannot express conditional legality: this vector
        # is chosen without knowing which kind will be sampled alongside it, so
        # a combination can still be refused. Narrowing it to indices that are
        # useful under *some* enabled kind keeps that rare; making it exact
        # needs a flattened Discrete over enumerated actions.
        first = np.zeros(MAX_STATIONS, dtype=bool)
        usable_paths = [
            index
            for index, path in enumerate(mediator.paths)
            if mediator.can_assign_locomotive(path)
            or mediator.can_attach_carriage(path)
        ]
        if kinds[SemanticAction.CONNECT]:
            first[:stations] = True
        for index in usable_paths:
            first[index] = True
        if not first.any():
            first[0] = True
        second = np.zeros(MAX_STATIONS, dtype=bool)
        second[: max(1, stations)] = True
        return [kinds, first, second]

    def action_masks(self) -> np.ndarray:
        """Flat mask over concatenated MultiDiscrete components.

        sb3-contrib expects one boolean vector of length sum(nvec); a list
        of per-component arrays has inhomogeneous shape and fails to stack.
        """

        return np.concatenate(self.action_mask_components())

    def _apply(self, action: np.ndarray) -> bool:
        """Carry out one intent, reporting whether it was legal and took effect."""
        mediator = self._mediator
        assert mediator is not None
        kind = SemanticAction(int(action[0]) % len(SemanticAction))
        first, second = int(action[1]), int(action[2])

        if kind is SemanticAction.WAIT:
            return True
        if kind is SemanticAction.CONNECT:
            count = len(mediator.stations)
            if first >= count or second >= count or first == second:
                return False
            if len(mediator.paths) >= MAX_PATHS:
                return False
            return (
                mediator.create_path_from_station_indices([first, second]) is not None
            )
        if kind in (SemanticAction.ASSIGN_LOCOMOTIVE, SemanticAction.ATTACH_CARRIAGE):
            if first >= len(mediator.paths):
                return False
            path = mediator.paths[first]
            if kind is SemanticAction.ASSIGN_LOCOMOTIVE:
                return mediator.can_assign_locomotive(
                    path
                ) and mediator.assign_locomotive(path)
            return mediator.can_attach_carriage(path) and mediator.attach_carriage(path)
        if first >= len(mediator.paths):
            return False
        return mediator.remove_path_by_index(first)

    def step(self, action):
        mediator = self._mediator
        if mediator is None:
            raise RuntimeError("environment must be reset before use")
        applied = self._apply(np.asarray(action, dtype=np.int64))
        for _ in range(TICKS_PER_DECISION):
            mediator.increment_time(16)
        self._decision += 1

        deliveries = mediator.deliveries
        reward = float(deliveries - self._last_deliveries)
        self._last_deliveries = deliveries
        terminated = bool(mediator.is_game_over)
        truncated = self._decision >= self.max_decisions and not terminated
        return (
            self._observe(),
            reward,
            terminated,
            truncated,
            {"applied": applied, "deliveries": deliveries},
        )

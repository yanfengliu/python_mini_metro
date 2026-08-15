"""A semantic environment: choose stations and lines, not pixels.

The pixel task's difficulty was almost entirely targeting precision. A station
covers about 0.034% of the coordinate grid, so a random click lands on one
roughly 0.1% of the time and a line needs two such hits -- about one in a
million. Measured consequences: random play built a usable line in 0 of 48
episodes, three PPO configurations delivered exactly zero across 3M, 300k and
600k steps, and Go-Explore reached lines only by archiving lucky states before
stalling on a smaller control still.

None of that is Mini Metro. It is the cost of expressing "connect these two
stations" as a pair of pixel coordinates. So this environment removes pixels
from both sides: the agent is told what the game is about and acts by naming
stations and lines.

Two properties are load-bearing, and both were learned the hard way.

**The offered actions must match the live game exactly.** An earlier version
masked CONNECT against a constant ceiling of four line slots while a fresh game
unlocks *one*, so 283 of 284 CONNECT attempts were silent no-ops and nearly half
of every episode was thrown away. The action space is therefore a flat table
whose legality is recomputed from the mediator every step -- an approximate mask
is a slow leak that reads as a weak policy.

**Whatever gates the agent's options must be visible to it.** Line slots unlock
on delivery milestones, so a model that cannot see the unlock state or its
distance to the next threshold is guessing about the rules it plays under. The
resource block reports every counter the game tracks and carries the distance to
the next unlock, and is written to extend to future unlocks rather than to
enumerate today's.

The pixel environment is unchanged and remains the player-equivalent task. This
is the separate structured lane `docs/rl-model-selection.md` pre-registers; it is
strictly easier and its scores are not interchangeable with pixel-task scores.
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

# Fixed slot per shape type. Must not depend on what the episode happened
# to spawn first; the last slot absorbs anything unrecognised.
SHAPE_ORDER = {
    "RECT": 0,
    "CIRCLE": 1,
    "TRIANGLE": 2,
    "CROSS": 3,
    "DIAMOND": 4,
    "PENTAGON": 5,
    "STAR": 6,
}

TICKS_PER_DECISION = 6
# The game is endless survival: stations keep arriving and the run ends when
# the agent can no longer keep up. A horizon that cuts an episode short
# right-censors its delivery total and understates the policy -- measured, 5
# of 8 episodes were being truncated at 4000, and lifting the cap took random
# play from a censored 102.8 to an uncensored 180.8. This value is a backstop
# against a non-terminating run, not a design limit; episodes should end
# because the game ended.
DEFAULT_MAX_DECISIONS = 200_000

STATION_FEATURES = 3 + SHAPE_SLOTS + SHAPE_SLOTS
PATH_FEATURES = 5

# Distance from every station to every line's nearest endpoint. Absolute
# positions alone force a flat network to infer pairwise geometry from two
# arbitrary slots; extending a line is fundamentally a question of how much
# longer it becomes, so that quantity is given directly.
REACH_FEATURES = MAX_STATIONS * MAX_PATHS
# Counters the game tracks, normalised. A future unlock means adding a reader to
# _resources and bumping this; nothing else in the environment changes.
RESOURCE_FEATURES = 14

# Deliveries out from a milestone at which "an unlock is imminent" reads as ~0.
UNLOCK_HORIZON = 20.0


class ActionKind(IntEnum):
    WAIT = 0
    CONNECT = 1
    ASSIGN_LOCOMOTIVE = 2
    ATTACH_CARRIAGE = 3
    PURCHASE_LINE = 4
    EXTEND_LINE = 5
    PREPEND_LINE = 6
    REMOVE_LINE = 7


def _build_action_table() -> tuple[tuple[int, int, int], ...]:
    """Enumerate every action once, so the mask can be exact rather than per-axis.

    Independent per-component masks over a MultiDiscrete cannot express
    conditional legality: the kind and the index are drawn separately, so
    "assign a locomotive" could pair with a line that cannot take one, and
    nothing could forbid CONNECT pairing a station with itself. A flat table
    makes every entry individually checkable against the live game.
    """
    table: list[tuple[int, int, int]] = [(ActionKind.WAIT, 0, 0)]
    for first in range(MAX_STATIONS):
        for second in range(first + 1, MAX_STATIONS):
            table.append((ActionKind.CONNECT, first, second))
    for path in range(MAX_PATHS):
        table.append((ActionKind.ASSIGN_LOCOMOTIVE, path, 0))
    for path in range(MAX_PATHS):
        table.append((ActionKind.ATTACH_CARRIAGE, path, 0))
    table.append((ActionKind.PURCHASE_LINE, 0, 0))
    # A real metro line runs through many stations. Without this the agent
    # could only ever build two-station lines, which caps the network
    # structurally no matter how well it plays.
    for line in range(MAX_PATHS):
        for station in range(MAX_STATIONS):
            table.append((ActionKind.EXTEND_LINE, line, station))
    # Which END a station joins changes the route order, and route order is
    # what a metro's lap time is made of. Append-only left the agent unable
    # to act on the very geometry the observation reports.
    for line in range(MAX_PATHS):
        for station in range(MAX_STATIONS):
            table.append((ActionKind.PREPEND_LINE, line, station))
    # Redrawing is a real strategic move, not just undoing progress. Masking
    # it out left a median of ONE legal action per step, so the policy had
    # nothing to decide and the score measured the simulation, not the agent.
    for line in range(MAX_PATHS):
        table.append((ActionKind.REMOVE_LINE, line, 0))
    return tuple(table)


ACTION_TABLE = _build_action_table()


class SemanticMetroEnv(gym.Env):
    """Mini Metro with a structured observation and an exactly-masked action set."""

    metadata = {"render_modes": []}

    def __init__(
        self, *, max_decisions: int = DEFAULT_MAX_DECISIONS, seed: int | None = None
    ):
        super().__init__()
        self.max_decisions = int(max_decisions)
        self._mediator: Mediator | None = None
        self._decision = 0
        self._last_deliveries = 0

        self.action_space = spaces.Discrete(len(ACTION_TABLE))
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self._observation_size(),), dtype=np.float32
        )

    @staticmethod
    def _observation_size() -> int:
        return (
            MAX_STATIONS * STATION_FEATURES
            + MAX_PATHS * PATH_FEATURES
            + REACH_FEATURES
            + RESOURCE_FEATURES
        )

    def _shape_slot(self, shape) -> int:
        """Canonical slot for a shape type, identical in every episode.

        An earlier version assigned slots in order of first appearance, so
        CIRCLE was slot 1 on one seed and slot 0 on another. The whole game
        is matching a passenger's shape to a destination station's shape, so
        an encoding that moves between episodes makes that unlearnable.
        """

        name = getattr(shape, "type", shape)
        name = getattr(name, "name", str(name))
        return SHAPE_ORDER.get(name, SHAPE_SLOTS - 1)

    @staticmethod
    def _path_station_indices(mediator, path) -> list[int]:
        """Indices into mediator.stations for the stations on this line."""

        lookup = {id(station): index for index, station in enumerate(mediator.stations)}
        return [
            lookup[id(station)] for station in path.stations if id(station) in lookup
        ]

    @staticmethod
    def _route_length(path) -> float:
        """Total distance a metro travels along this line, in canonical pixels."""

        stations = list(path.stations)
        total = 0.0
        for first, second in zip(stations, stations[1:]):
            total += (
                (first.position.left - second.position.left) ** 2
                + (first.position.top - second.position.top) ** 2
            ) ** 0.5
        return total

    @staticmethod
    def _distance_to_path(station, path) -> float:
        """How far this station sits from the nearest end of this line.

        Extending a line is a question of how much longer it becomes, and that
        is a pairwise quantity a flat network would otherwise have to infer by
        comparing two arbitrary observation slots.
        """

        ends = [path.stations[0], path.stations[-1]] if path.stations else []
        best = None
        for end in ends:
            distance = (
                (end.position.left - station.position.left) ** 2
                + (end.position.top - station.position.top) ** 2
            ) ** 0.5
            if best is None or distance < best:
                best = distance
        return 0.0 if best is None else best

    @staticmethod
    def _scaled(value: float, typical: float) -> float:
        """Compress an unbounded counter without saturating it.

        Line credits reach 210 in a long game while a naive min(1, v/8)
        saturates at 8, so the model could not tell eight credits from two
        hundred -- it could see that it could afford something, never how much
        headroom it had. A log curve keeps small values well separated and
        still bounds the large ones.
        """

        import math

        return min(1.0, math.log1p(max(0.0, value)) / math.log1p(typical))

    @staticmethod
    def _count(mediator, name: str) -> float:
        """Read a counter that may be absent OR present-but-None.

        available_tunnels is None on maps without tunnels, and a getattr
        default only fires when the attribute is missing -- not when it holds
        None. Defaulting on the value rather than on presence is the
        difference between a zero and a TypeError mid-episode.
        """

        value = getattr(mediator, name, None)
        return 0.0 if value is None else float(value)

    def _unlock_proximity(self, milestones, deliveries: int) -> float:
        """1.0 when the next unlock is imminent, 0.0 when far off or exhausted."""
        upcoming = next((m for m in milestones if m > deliveries), None)
        if upcoming is None:
            return 0.0
        return max(0.0, 1.0 - (upcoming - deliveries) / UNLOCK_HORIZON)

    def _resources(self, mediator) -> list[float]:
        """Every counter that gates what the agent may do, plus unlock distance.

        Line slots unlock on delivery milestones, so reporting the distance to
        the next threshold lets a policy anticipate an unlock rather than
        discover it -- the difference between planning and reacting.
        """
        deliveries = mediator.deliveries
        purchasable = mediator.get_next_path_button_idx_to_purchase()
        can_buy = purchasable is not None and mediator.can_purchase_path_button_idx(
            purchasable
        )
        return [
            self._scaled(mediator.line_credits, 200.0),
            self._scaled(self._count(mediator, "available_locomotives"), 12.0),
            self._scaled(self._count(mediator, "available_carriages"), 12.0),
            self._scaled(self._count(mediator, "assigned_carriages"), 12.0),
            self._scaled(self._count(mediator, "available_tunnels"), 12.0),
            mediator.get_unlocked_num_paths() / MAX_PATHS,
            min(1.0, mediator.get_unlocked_num_stations() / MAX_STATIONS),
            min(1.0, self._count(mediator, "purchased_num_paths") / MAX_PATHS),
            len(mediator.paths) / MAX_PATHS,
            min(1.0, len(mediator.stations) / MAX_STATIONS),
            1.0 if can_buy else 0.0,
            self._unlock_proximity(
                getattr(mediator, "path_unlock_milestones", ()) or (), deliveries
            ),
            self._unlock_proximity(
                getattr(mediator, "station_unlock_milestones", ()) or (), deliveries
            ),
            self._scaled(self._decision, 5000.0),
        ]

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
            cursor += STATION_FEATURES

        for slot in range(MAX_PATHS):
            if slot < len(mediator.paths):
                path = mediator.paths[slot]
                values[cursor] = 1.0
                values[cursor + 1] = len(path.stations) / MAX_STATIONS
                values[cursor + 2] = len(getattr(path, "metros", ())) / 4.0
                values[cursor + 3] = min(1.0, len(path.stations) / 8.0)
                # Route length is the travel time a metro pays each lap, so it
                # is what makes a long detour cost deliveries rather than gain
                # them. Without it the agent optimises coverage blind to speed.
                values[cursor + 4] = self._scaled(self._route_length(path), 4000.0)
            cursor += PATH_FEATURES

        for slot in range(MAX_STATIONS):
            for line in range(MAX_PATHS):
                if slot < len(mediator.stations) and line < len(mediator.paths):
                    values[cursor] = 1.0 - self._scaled(
                        self._distance_to_path(
                            mediator.stations[slot], mediator.paths[line]
                        ),
                        2000.0,
                    )
                cursor += 1

        resources = self._resources(mediator)
        values[cursor : cursor + len(resources)] = resources
        return np.clip(values, -1.0, 1.0)

    def action_masks(self) -> np.ndarray:
        """Exact legality for every enumerated action, recomputed from the game."""
        mediator = self._mediator
        assert mediator is not None
        stations = len(mediator.stations)
        paths = len(mediator.paths)
        purchasable = mediator.get_next_path_button_idx_to_purchase()
        can_buy = purchasable is not None and mediator.can_purchase_path_button_idx(
            purchasable
        )
        can_connect = stations >= 2 and paths < mediator.get_unlocked_num_paths()

        mask = np.zeros(len(ACTION_TABLE), dtype=bool)
        for index, (kind, first, second) in enumerate(ACTION_TABLE):
            if kind == ActionKind.WAIT:
                mask[index] = True
            elif kind == ActionKind.CONNECT:
                mask[index] = can_connect and second < stations
            elif kind == ActionKind.ASSIGN_LOCOMOTIVE:
                mask[index] = first < paths and mediator.can_assign_locomotive(
                    mediator.paths[first]
                )
            elif kind == ActionKind.ATTACH_CARRIAGE:
                mask[index] = first < paths and mediator.can_attach_carriage(
                    mediator.paths[first]
                )
            elif kind == ActionKind.PURCHASE_LINE:
                mask[index] = can_buy
            elif kind == ActionKind.REMOVE_LINE:
                mask[index] = first < paths
            else:
                if first >= paths or second >= stations:
                    mask[index] = False
                else:
                    on_line = self._path_station_indices(
                        mediator, mediator.paths[first]
                    )
                    mask[index] = second not in on_line
        return mask

    def reset(self, *, seed: int | None = None, options=None):
        super().reset(seed=seed)
        self._mediator = Mediator(seed=seed if seed is not None else 0)
        self._decision = 0
        self._last_deliveries = 0
        return self._observe(), {}

    def _apply(self, index: int) -> bool:
        mediator = self._mediator
        assert mediator is not None
        kind, first, second = ACTION_TABLE[int(index)]
        if kind == ActionKind.WAIT:
            return True
        if kind == ActionKind.CONNECT:
            return (
                mediator.create_path_from_station_indices([first, second]) is not None
            )
        if kind == ActionKind.ASSIGN_LOCOMOTIVE:
            return mediator.assign_locomotive(mediator.paths[first])
        if kind == ActionKind.ATTACH_CARRIAGE:
            return mediator.attach_carriage(mediator.paths[first])
        if kind == ActionKind.PURCHASE_LINE:
            return mediator.try_purchase_path_button_by_index()
        if kind == ActionKind.REMOVE_LINE:
            return mediator.remove_path_by_index(first)
        route = self._path_station_indices(mediator, mediator.paths[first])
        if kind == ActionKind.PREPEND_LINE:
            return mediator.replace_path_by_index(first, [second] + route)
        return mediator.replace_path_by_index(first, route + [second])

    def step(self, action):
        mediator = self._mediator
        if mediator is None:
            raise RuntimeError("environment must be reset before use")
        applied = self._apply(int(np.asarray(action).ravel()[0]))
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

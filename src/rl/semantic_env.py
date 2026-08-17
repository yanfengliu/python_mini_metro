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
# Two numbers per (station, line): distance to the route's head and to its
# tail. One number could not express which end is nearer, which is precisely
# the PREPEND-versus-EXTEND decision.
REACH_PER_PAIR = 2
REACH_FEATURES = MAX_STATIONS * MAX_PATHS * REACH_PER_PAIR

# The COMPARISON, not just its inputs. The distances above are everything the
# scripted heuristic's rule needs -- it grafts the nearest unserved station onto
# a line's nearer end -- and a network given only those distances never learns
# the rule: held-out agreement sits at 74-81% whatever the architecture, and 9x
# the data does not move it (E39/E40). What the rule requires is an ARGMIN over
# ~80 station-line pairs, and selection is not what a flat head over a
# fixed-slot vector does well; slot i also holds a different station on every
# board, so nothing learned about one slot transfers.
#
# So the ranking is computed and supplied directly. Per (station, line): 1.0 if
# this station is the nearest UNSERVED one to that line's nearer end, falling
# off with rank. This does not tell the agent what to do -- it still has to
# decide whether to extend, which line, and whether to act at all -- it removes
# only the argmin it demonstrably cannot perform.
RANK_PER_PAIR = 1
RANK_FEATURES = MAX_STATIONS * MAX_PATHS * RANK_PER_PAIR
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


# The action table's shape, resolved once at import rather than re-walked on
# every mask. Profiling showed 96% of `action_masks` was the 364-iteration
# Python loop itself -- tuple unpacking, a chain of enum comparisons, and a
# numpy scalar store per entry, about 190ns each -- and almost nothing in the
# game methods it called. Grouping the table by kind turns that loop into a
# handful of whole-array operations.
_TABLE_FIRST = np.array([first for _, first, _ in ACTION_TABLE], dtype=np.int64)
_TABLE_SECOND = np.array([second for _, _, second in ACTION_TABLE], dtype=np.int64)
_TABLE_BY_KIND = {
    kind: np.array(
        [index for index, (k, _, _) in enumerate(ACTION_TABLE) if k == kind],
        dtype=np.int64,
    )
    for kind in ActionKind
}
# EXTEND_LINE and PREPEND_LINE share one rule: the line and station must exist
# and the station must not already be on that line.
_TABLE_ON_LINE = np.sort(
    np.concatenate(
        [
            _TABLE_BY_KIND[ActionKind.EXTEND_LINE],
            _TABLE_BY_KIND[ActionKind.PREPEND_LINE],
        ]
    )
)


class SemanticMetroEnv(gym.Env):
    """Mini Metro with a structured observation and an exactly-masked action set."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        max_decisions: int = DEFAULT_MAX_DECISIONS,
        seed: int | None = None,
        remove_min_age: int = 0,
        remove_penalty: float = 0.0,
    ):
        super().__init__()
        self.max_decisions = int(max_decisions)
        # Removing a line is individually free: from identical states the next
        # 800 decisions return 18.3 when a line is kept and 18.7 when it is
        # destroyed. An action with no cost is never pushed away from, so the
        # policy drifts onto it -- the collapsed run chose REMOVE as argmax in
        # 73% of states while it was 17% of the legal set -- and once no line
        # survives, every return is 0 and the gradient vanishes. These two
        # knobs are the candidate interventions against that trap.
        self.remove_min_age = int(remove_min_age)
        self.remove_penalty = float(remove_penalty)
        self._line_born: dict[int, int] = {}
        self._mask_cache: tuple[tuple, np.ndarray] | None = None
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
            + RANK_FEATURES
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

    def _line_age(self, mediator, index: int) -> int:
        """Decisions since this line was created."""
        if index >= len(mediator.paths):
            return 0
        born = self._line_born.get(mediator.paths[index].id)
        # An unrecorded line is NEWBORN, not maximally old. The previous default
        # failed open in the same direction as the id-recycling bug.
        return 0 if born is None else self._decision - born

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
        """Distance to the nearer end of this line."""

        head, tail = SemanticMetroEnv._distances_to_ends(station, path)
        return min(head, tail)

    @staticmethod
    def _distances_to_ends(station, path) -> tuple[float, float]:
        """Distance to the FIRST station of the route, and to the last.

        Reporting only the nearer end made the two ends indistinguishable, and
        grafting a station onto the near end rather than the far one is exactly
        the choice between PREPEND_LINE and EXTEND_LINE. The scripted heuristic
        picks the nearer end and scores 276.9; a policy cloned from it agreed on
        only 44% of its real decisions and inverted that pair (EXTEND 8 /
        PREPEND 12 against the teacher's 14 / 9), because the information needed
        to make the decision was not in the observation at all.
        """

        if not path.stations:
            return 0.0, 0.0
        out = []
        for end in (path.stations[0], path.stations[-1]):
            out.append(
                (
                    (end.position.left - station.position.left) ** 2
                    + (end.position.top - station.position.top) ** 2
                )
                ** 0.5
            )
        return out[0], out[1]

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
                    # Both ends, so PREPEND and EXTEND are distinguishable.
                    head, tail = self._distances_to_ends(
                        mediator.stations[slot], mediator.paths[line]
                    )
                    values[cursor] = 1.0 - self._scaled(head, 2000.0)
                    values[cursor + 1] = 1.0 - self._scaled(tail, 2000.0)
                cursor += REACH_PER_PAIR

        # Rank of each station among the UNSERVED ones by distance to this
        # line's nearer end. 1.0 is nearest; a station already on the line, or
        # a slot with no station or no line, stays 0.
        for line in range(MAX_PATHS):
            order: list[tuple[float, int]] = []
            if line < len(mediator.paths):
                path = mediator.paths[line]
                on_line = set(self._path_station_indices(mediator, path))
                for slot in range(min(MAX_STATIONS, len(mediator.stations))):
                    if slot in on_line:
                        continue
                    head, tail = self._distances_to_ends(mediator.stations[slot], path)
                    order.append((min(head, tail), slot))
                order.sort()
            ranked = {slot: position for position, (_, slot) in enumerate(order)}
            for slot in range(MAX_STATIONS):
                position = ranked.get(slot)
                if position is not None:
                    values[cursor + slot * MAX_PATHS + line] = 1.0 / (1.0 + position)
        cursor += RANK_FEATURES

        resources = self._resources(mediator)
        values[cursor : cursor + len(resources)] = resources
        return np.clip(values, -1.0, 1.0)

    def _mask_fingerprint(self, mediator) -> tuple:
        """Everything the mask reads, in a form that is cheap to compare.

        The mask is dominated by `can_assign_locomotive` and
        `can_attach_carriage`, which run a full carriage-canonical and
        path-geometry validation per line. Profiling a heuristic episode showed
        those two accounting for nearly all of the time -- and the heuristic
        acts about 17 times in 8,244 decisions, so on ~99.8% of steps they
        re-validate a structure that has not changed.

        This fingerprint deliberately errs toward recomputation: it is built
        only from counts and identities that are cheap to read, and any of them
        moving discards the cache. Its completeness is not argued, it is gated
        -- `test_semantic_env_mask_equivalence` recomputes a naive reference
        mask at every step of two full episodes, so a missing term shows up as a
        disagreement rather than as a silently stale mask.
        """
        paths = mediator.paths
        return (
            len(mediator.stations),
            len(paths),
            # WHICH stations are on each line, not merely how many. Route length
            # plus line id looked sufficient because `_apply` only ever grows a
            # route, so equal ids and equal lengths implied equal membership --
            # a property of the current caller, not of the game. A same-length
            # edit (line [0,1] becoming [0,2]) left the fingerprint identical
            # while inverting four EXTEND/PREPEND entries: one legal action
            # withheld and one illegal action offered.
            tuple(tuple(self._path_station_indices(mediator, path)) for path in paths),
            tuple(len(path.metros) for path in paths),
            # How many of those metros are queued for unassignment.
            # `carriage_management._attach_candidate` filters on this flag, and
            # the plain metro count does not move when one is queued. No action
            # in this env's table can queue one, so it is unreachable from here
            # -- but the mediator's public API and any restored save can embody
            # it, and "unreachable from the current caller" is how the two
            # defects above got in.
            tuple(
                sum(
                    1
                    for metro in path.metros
                    if getattr(metro, "is_unassignment_queued", False)
                )
                for path in paths
            ),
            tuple(path.id for path in paths),
            # Game over is read transitively by both crew predicates
            # (fleet_management.can_assign and carriage_management's host check)
            # and changes nothing else here, so without it the cache kept
            # advertising ASSIGN_LOCOMOTIVE and ATTACH_CARRIAGE on a finished
            # game.
            bool(getattr(mediator, "is_game_over", False)),
            mediator.available_locomotives,
            mediator.available_carriages,
            mediator.assigned_carriages,
            mediator.get_unlocked_num_paths(),
            mediator.get_next_path_button_idx_to_purchase(),
            mediator.line_credits,
            tuple(
                self._line_age(mediator, index) >= self.remove_min_age
                for index in range(len(paths))
            ),
        )

    def action_masks(self) -> np.ndarray:
        """Exact legality for every enumerated action, recomputed from the game."""
        mediator = self._mediator
        assert mediator is not None

        fingerprint = self._mask_fingerprint(mediator)
        if self._mask_cache is not None and self._mask_cache[0] == fingerprint:
            return self._mask_cache[1].copy()
        stations = len(mediator.stations)
        paths = len(mediator.paths)
        purchasable = mediator.get_next_path_button_idx_to_purchase()
        can_buy = purchasable is not None and mediator.can_purchase_path_button_idx(
            purchasable
        )
        can_connect = stations >= 2 and paths < mediator.get_unlocked_num_paths()

        # Per-LINE quantities, computed once per line rather than per entry.
        served = np.zeros((MAX_PATHS, MAX_STATIONS), dtype=bool)
        for position, path in enumerate(mediator.paths[:MAX_PATHS]):
            for station_index in self._path_station_indices(mediator, path):
                if station_index < MAX_STATIONS:
                    served[position, station_index] = True

        mask = np.zeros(len(ACTION_TABLE), dtype=bool)
        mask[_TABLE_BY_KIND[ActionKind.WAIT]] = True

        connect = _TABLE_BY_KIND[ActionKind.CONNECT]
        if can_connect:
            mask[connect] = _TABLE_SECOND[connect] < stations
        mask[_TABLE_BY_KIND[ActionKind.PURCHASE_LINE]] = can_buy

        crew = _TABLE_BY_KIND[ActionKind.ASSIGN_LOCOMOTIVE]
        carriage = _TABLE_BY_KIND[ActionKind.ATTACH_CARRIAGE]
        # A line may only be redrawn once it has existed a while. The collapsed
        # policy ran a remove-then-rebuild loop; an age gate breaks that
        # directly while leaving genuine redraw available.
        remove = _TABLE_BY_KIND[ActionKind.REMOVE_LINE]
        for position, path in enumerate(mediator.paths[:MAX_PATHS]):
            mask[crew[_TABLE_FIRST[crew] == position]] = mediator.can_assign_locomotive(
                path
            )
            mask[carriage[_TABLE_FIRST[carriage] == position]] = (
                mediator.can_attach_carriage(path)
            )
            mask[remove[_TABLE_FIRST[remove] == position]] = (
                self._line_age(mediator, position) >= self.remove_min_age
            )

        on_line = _TABLE_ON_LINE
        first_of = _TABLE_FIRST[on_line]
        second_of = _TABLE_SECOND[on_line]
        legal = (first_of < paths) & (second_of < stations)
        allowed = np.zeros(len(on_line), dtype=bool)
        chosen = np.flatnonzero(legal)
        allowed[chosen] = ~served[first_of[chosen], second_of[chosen]]
        mask[on_line] = allowed
        # The cached array is never handed out directly. Returning it shared
        # made every consumer's `th.as_tensor(mask)` warn that the array is not
        # writable (a hard failure under -W error), and left the cache one
        # `mask[i] = False` away from silent corruption. A 364-byte copy costs
        # far less than the recomputation it still saves.
        self._mask_cache = (fingerprint, mask)
        return mask.copy()

    def reset(self, *, seed: int | None = None, options=None):
        """Start a new game, drawing a fresh layout when no seed is given.

        A vector environment auto-resets *without* a seed, so defaulting to a
        constant meant every episode after the first replayed one identical
        layout -- measured: eight parallel environments trained 600,000 steps
        on a single board. An explicit seed still pins the game exactly, which
        is what evaluation and the tests rely on.
        """

        super().reset(seed=seed)
        if seed is None:
            seed = int(self.np_random.integers(0, 2**31 - 1))
        self._mediator = Mediator(seed=seed)
        self._seed = seed
        self._decision = 0
        self._last_deliveries = 0
        self._line_born = {}
        self._mask_cache = None
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
        chosen = int(np.asarray(action).ravel()[0])
        kind = ACTION_TABLE[chosen][0]
        applied = self._apply(chosen)
        for _ in range(TICKS_PER_DECISION):
            mediator.increment_time(16)
        self._decision += 1
        # Record when each line came into being, so the age gate has something
        # to measure. Keyed by object identity because indices shift on removal.
        # Keyed by path.id (a unique string), NOT id(path): CPython recycles
        # freed addresses, and setdefault then refuses to overwrite the dead
        # line's birth time, so a brand-new line inherits it and reports a large
        # age. Measured: 71% of fresh lines were immediately removable, and the
        # leak was worst on exactly the remove-then-rebuild loop the gate exists
        # to break. Pruned each step so it cannot grow without bound.
        live = {path.id for path in mediator.paths}
        self._line_born = {
            key: born for key, born in self._line_born.items() if key in live
        }
        for path in mediator.paths:
            self._line_born.setdefault(path.id, self._decision)

        deliveries = mediator.deliveries
        reward = float(deliveries - self._last_deliveries)
        if applied and kind == ActionKind.REMOVE_LINE:
            # Destroying a line is otherwise free -- measured at 18.7 against
            # 18.3 for keeping it -- so nothing opposes drifting onto it.
            reward -= self.remove_penalty
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

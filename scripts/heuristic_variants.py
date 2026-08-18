"""Is there any headroom in the heuristic's arbitrary choices?

Before spending hours teaching a network to deviate from the scripted policy, it
is worth knowing whether deviating is worth anything. Two of the heuristic's
rules are arbitrary in a way its own docstring does not defend:

* it crews `legal[kind][0][0]` -- whichever line happens to sit lowest in the
  action table -- so which line gets a locomotive or a carriage is decided by
  table order, not by anything about the line;
* it grafts a station onto the nearest line END, with no regard for how long
  that line already is or what it is carrying.

Each variant here changes exactly one of those and nothing else. They are
scored by `paired_eval.py` against the unmodified heuristic on identical seeds,
so the difference isolates the rule.

This is a headroom probe, not a proposal. A variant that wins says the choice
matters and a learner has something to find; a set of variants that all land
inside the interval says the heuristic is at a local optimum in these
directions, and that a learned policy will have to find its advantage
elsewhere. Either answer is worth an hour, and both are cheaper than a training
run that cannot say which it was.
"""

from __future__ import annotations

import numpy as np

from rl.heuristic import _distance, _served, _station_positions
from rl.semantic_env import ACTION_TABLE, ActionKind


def _legal_by_kind(env) -> dict:
    legal: dict = {}
    for index in np.flatnonzero(env.action_masks()):
        kind, first, second = ACTION_TABLE[index]
        legal.setdefault(kind, []).append((int(index), int(first), int(second)))
    return legal


def _waiting_on(mediator, path) -> int:
    """Passengers standing at the stations this line serves."""
    return sum(len(getattr(station, "passengers", ())) for station in path.stations)


def _crewed_by(mediator, entries, score) -> int:
    """Pick the line maximising `score`, falling back to table order on a tie."""
    best = None
    for index, line, _ in entries:
        if line >= len(mediator.paths):
            continue
        value = score(mediator.paths[line])
        if best is None or value > best[0]:
            best = (value, index)
    return best[1] if best is not None else entries[0][0]


def _graft(env, mediator, legal, positions, unserved, penalty, end_rule=None):
    """The heuristic's graft, plus `penalty(path)` added to each candidate gap."""
    best = None
    for kind in (ActionKind.EXTEND_LINE, ActionKind.PREPEND_LINE):
        for index, line, station in legal.get(kind, ()):
            if station not in unserved or line >= len(mediator.paths):
                continue
            route = mediator.paths[line].stations
            if not route:
                continue
            end = route[-1] if kind is ActionKind.EXTEND_LINE else route[0]
            gap = _distance(positions[station], (end.position.left, end.position.top))
            gap += penalty(mediator.paths[line])
            if end_rule == "far":
                gap = -gap
            elif end_rule == "arbitrary":
                # Deterministic in the state, so the arm is reproducible, but
                # uncorrelated with which end is nearer. Knuth's multiplicative
                # hash over the decision index and the table entry.
                gap = float(((env._decision * 2654435761) ^ (index * 40503)) % 1000)
            if best is None or gap < best[0]:
                best = (gap, index)
    return None if best is None else best[1]


def _connect(mediator, legal, positions, unserved):
    if ActionKind.CONNECT not in legal or len(unserved) < 2:
        return None
    pick = None
    for index, first, second in legal[ActionKind.CONNECT]:
        if first not in unserved or second not in unserved:
            continue
        gap = _distance(positions[first], positions[second])
        if pick is None or gap < pick[0]:
            pick = (gap, index)
    return None if pick is None else pick[1]


def _make(
    crew_score=None,
    graft_penalty=None,
    defer_purchase=0,
    spare_line=None,
    spare_min_stations=0,
    end_rule=None,
):
    """Build a `choose`-compatible policy differing in one rule.

    `crew_score`      -- pick the line maximising this instead of table order.
    `graft_penalty`   -- added to each graft candidate's distance.
    `defer_purchase`  -- do not buy a line slot while fewer than this many
                         stations are unserved.
    `spare_line`      -- what to do when a line slot is bought but unused.
    `spare_min_stations` -- only open a second line once the network has at
                         least this many stations, so an early split cannot
                         starve the first line of a locomotive.
    """

    def choose(env) -> int:
        mediator = env._mediator
        positions = _station_positions(mediator)
        served = _served(mediator)
        unserved = [i for i in range(len(positions)) if i not in served]
        legal = _legal_by_kind(env)

        if ActionKind.PURCHASE_LINE in legal and len(unserved) >= defer_purchase:
            return legal[ActionKind.PURCHASE_LINE][0][0]

        # A spare slot exists exactly when CONNECT is legal: the mask offers
        # it only while `paths < unlocked_num_paths`. The heuristic reaches its
        # CONNECT rule only AFTER the graft rule declines, and the graft rule
        # never declines while any station is unserved -- so the slot it just
        # bought is never spent, and every episode ends with one line carrying
        # every station. Measured on 12 seeds: lines=1, longest_line=stations,
        # on all twelve.
        if (
            spare_line is not None
            and ActionKind.CONNECT in legal
            and len(positions) >= spare_min_stations
        ):
            if spare_line == "closest-any-pair":
                # CONNECT is legal for ANY pair, served or not -- the mask says
                # `second < stations` and nothing about membership. Restricting
                # it to unserved pairs is the heuristic's own rule, and it is
                # what makes a second line unreachable.
                pick = None
                for index, first, second in legal[ActionKind.CONNECT]:
                    gap = _distance(positions[first], positions[second])
                    if pick is None or gap < pick[0]:
                        pick = (gap, index)
                if pick is not None:
                    return pick[1]
            elif spare_line == "farthest-any-pair":
                pick = None
                for index, first, second in legal[ActionKind.CONNECT]:
                    gap = _distance(positions[first], positions[second])
                    if pick is None or gap > pick[0]:
                        pick = (gap, index)
                if pick is not None:
                    return pick[1]
            elif spare_line == "hold-for-unserved":
                # Do not graft while a slot is spare; wait for a second
                # unserved station and start a line with the pair instead.
                if len(unserved) >= 2:
                    held = _connect(mediator, legal, positions, unserved)
                    if held is not None:
                        return held
                elif unserved:
                    return 0

        penalty = graft_penalty or (lambda path: 0.0)
        grafted = _graft(env, mediator, legal, positions, unserved, penalty, end_rule)
        if grafted is not None:
            return grafted

        connected = _connect(mediator, legal, positions, unserved)
        if connected is not None:
            return connected

        for kind in (ActionKind.ASSIGN_LOCOMOTIVE, ActionKind.ATTACH_CARRIAGE):
            if kind in legal:
                if crew_score is None:
                    return legal[kind][0][0]
                return _crewed_by(mediator, legal[kind], crew_score)
        return 0

    return choose


# Feature scales, in canonical pixels and station counts, chosen so every
# feature is order 1 and the weights are directly comparable.
_GAP_SCALE = 500.0
_LENGTH_SCALE = 2000.0
_COUNT_SCALE = 10.0


def _end_features(positions, station, route, at_head):
    """The six numbers the learned rule scores a candidate end by.

    Deliberately small and local: this decision is binary and fires about 59
    times an episode, so the search space has to be small enough that paired
    evaluation can resolve it. Everything here is already in the observation.
    """
    head, tail = route[0], route[-1]
    near, far = (head, tail) if at_head else (tail, head)
    gap = _distance(positions[station], (near.position.left, near.position.top))
    other = _distance(positions[station], (far.position.left, far.position.top))
    length = 0.0
    for first, second in zip(route, route[1:]):
        length += _distance(
            (first.position.left, first.position.top),
            (second.position.left, second.position.top),
        )
    return np.array(
        [
            gap / _GAP_SCALE,
            other / _GAP_SCALE,
            1.0 if at_head else 0.0,
            len(route) / _COUNT_SCALE,
            length / _LENGTH_SCALE,
            1.0,
        ]
    )


def make_end_scorer(weights):
    """The heuristic, with the graft end chosen by `weights . features`.

    `weights = [-1, 0, 0, 0, 0, 0]` scores each candidate by the negative
    distance to it, which IS the scripted rule -- so a search seeded there
    starts at the bar exactly rather than approximately. `learn_end_rule.py`
    asserts that byte-for-byte before it optimises anything.
    """

    weights = np.asarray(weights, dtype=float)

    def choose(env) -> int:
        mediator = env._mediator
        positions = _station_positions(mediator)
        served = _served(mediator)
        unserved = [i for i in range(len(positions)) if i not in served]
        legal = _legal_by_kind(env)

        if ActionKind.PURCHASE_LINE in legal:
            return legal[ActionKind.PURCHASE_LINE][0][0]

        best = None
        for kind in (ActionKind.EXTEND_LINE, ActionKind.PREPEND_LINE):
            for index, line, station in legal.get(kind, ()):
                if station not in unserved or line >= len(mediator.paths):
                    continue
                route = list(mediator.paths[line].stations)
                if not route:
                    continue
                at_head = kind is ActionKind.PREPEND_LINE
                score = float(
                    weights @ _end_features(positions, station, route, at_head)
                )
                if best is None or score > best[0]:
                    best = (score, index)
        if best is not None:
            return best[1]

        connected = _connect(mediator, legal, positions, unserved)
        if connected is not None:
            return connected

        for kind in (ActionKind.ASSIGN_LOCOMOTIVE, ActionKind.ATTACH_CARRIAGE):
            if kind in legal:
                return legal[kind][0][0]
        return 0

    return choose


def load_learned(path="output/endrule/best.json"):
    """The weights the search settled on, as a playable policy."""
    import json

    with open(path, encoding="utf-8") as handle:
        return make_end_scorer(json.load(handle)["mean_weights"])


def _two_opt(points, order):
    """Shorten a route by repeatedly reversing segments. O(n^2) per pass.

    Not brute force: the exact optimum over 9 stations is 181,440 orderings and
    this runs on every decision. 2-opt lands within a few percent of it and
    costs microseconds, which is the right trade for a probe whose question is
    whether the effect exists at all.
    """

    def length(seq):
        return sum(_distance(points[a], points[b]) for a, b in zip(seq, seq[1:]))

    best = list(order)
    best_length = length(best)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 2, len(best)):
                candidate = best[: i + 1] + best[i + 1 : j + 1][::-1] + best[j + 1 :]
                value = length(candidate)
                if value < best_length - 1e-9:
                    best, best_length = candidate, value
                    improved = True
    return best, best_length


def make_rebuilder(threshold=0.10, min_stations=5):
    """The heuristic, plus: re-lay the line when its order is badly wrong.

    Measured motivation. The route greedy head/tail insertion builds is only
    ~4% longer than the best route ANY end-choosing policy could reach given
    the arrival order -- which is why searching the end choice found nothing at
    +/-3 (E47). But the insertion-reachable route is **34% longer than the
    optimal ordering of the same stations**, and lap time is what a four-train
    fleet is rationed by. That headroom is locked behind the action space, not
    behind the decision rule.

    It is reachable, though: REMOVE_LINE, CONNECT the first two stations of the
    better order, then EXTEND the rest in sequence. Every step is a legal
    action, and each costs one decision -- six ticks, 0.1 game-seconds -- so
    re-laying a nine-station line costs about a second of downtime against a
    permanently shorter lap.

    Stateless by construction: the target order is recomputed from the live
    board every call, and the policy's job each step is just "am I a prefix of
    the target, and if not, what is the next legal step toward it". Nothing is
    remembered between decisions, so a restored save or an interrupted rebuild
    behaves identically to one that ran straight through.
    """

    def choose(env) -> int:
        mediator = env._mediator
        positions = _station_positions(mediator)
        served = _served(mediator)
        unserved = [i for i in range(len(positions)) if i not in served]
        legal = _legal_by_kind(env)

        if ActionKind.PURCHASE_LINE in legal:
            return legal[ActionKind.PURCHASE_LINE][0][0]

        # Only ever reasons about a single line, which is what this policy
        # family builds; with none yet, fall straight through to the scripted
        # rules that create one.
        if len(mediator.paths) == 1 and len(positions) >= min_stations:
            route = _path_indices(mediator, mediator.paths[0])
            if len(route) >= min_stations:
                current = _route_length(positions, route)
                target, improved = _two_opt(positions, route)
                if current > 0 and (current - improved) / current > threshold:
                    step = _rebuild_step(env, mediator, legal, route, target)
                    if step is not None:
                        return step

        penalty = lambda path: 0.0  # noqa: E731 - matches _make's default
        grafted = _graft(env, mediator, legal, positions, unserved, penalty)
        if grafted is not None:
            return grafted

        connected = _connect(mediator, legal, positions, unserved)
        if connected is not None:
            return connected

        for kind in (ActionKind.ASSIGN_LOCOMOTIVE, ActionKind.ATTACH_CARRIAGE):
            if kind in legal:
                return legal[kind][0][0]
        return 0

    return choose


def _path_indices(mediator, path):
    lookup = {id(station): index for index, station in enumerate(mediator.stations)}
    return [lookup[id(s)] for s in path.stations if id(s) in lookup]


def _route_length(positions, order) -> float:
    return sum(_distance(positions[a], positions[b]) for a, b in zip(order, order[1:]))


def _rebuild_step(env, mediator, legal, route, target):
    """One legal action toward laying the line out as `target`.

    The line is torn down only when it is NOT already a prefix of the target,
    so an interrupted rebuild resumes rather than restarting -- and a route
    that already matches is never touched, which is what stops the policy
    oscillating between two orderings of equal length.
    """
    forward = target
    backward = target[::-1]
    for want in (forward, backward):
        if route == want[: len(route)]:
            if len(route) == len(want):
                return None
            nxt = want[len(route)]
            for index, line, station in legal.get(ActionKind.EXTEND_LINE, ()):
                if line == 0 and station == nxt:
                    return index
            return None
    if len(route) <= 2:
        return None
    for index, line, _ in legal.get(ActionKind.REMOVE_LINE, ()):
        if line == 0:
            return index
    return None


# Feature scales for the learned rebuild trigger, chosen so each is order 1 and
# the weights are directly comparable. Station capacity is 12.
_CAPACITY = 12.0
_UNSERVED_SCALE = 4.0
_WAITING_SCALE = 30.0

# The weights that reproduce `make_rebuilder(threshold=0.20)` EXACTLY: score is
# `saving - 0.20`, so the trigger fires on exactly the same states. The search
# is anchored here, and `learn_trigger.py` refuses to start unless the anchor
# reproduces v16 byte for byte -- the lesson E45 paid for.
TRIGGER_FEATURES = (
    "saving",
    "unserved",
    "max_queue",
    "total_waiting",
    "route_stations",
    "bias",
)
TRIGGER_ANCHOR = (1.0, 0.0, 0.0, 0.0, 0.0, -0.20)


def _pressure(mediator):
    """Queue state, which is exactly what the action mask does not encode."""
    queues = [len(getattr(s, "passengers", ())) for s in mediator.stations]
    return (max(queues) if queues else 0), sum(queues)


def make_learned_rebuilder(weights):
    """`make_rebuilder`, with the fixed threshold replaced by a learned score.

    The fixed trigger is one constant on a very steep curve -- measured at n=200
    per arm, a 5% trigger is worth -19.95 against the scripted policy, 20% is
    worth +31.82, and 40% is worth +2.73. A constant sitting on a curve that
    sharp is leaving value behind, because whether a rebuild pays plainly
    depends on the state: tearing the line down while queues are already full is
    a different proposition from doing it while the board is quiet.

    So the trigger becomes `weights . features > 0` over the saving itself plus
    four things the constant cannot see -- how many stations are unserved, the
    worst queue, the total waiting, and how long the line is. `TRIGGER_ANCHOR`
    reproduces the fixed 20% rule exactly, so the search starts at the current
    bar rather than near it.
    """

    weights = np.asarray(weights, dtype=float)

    def choose(env) -> int:
        mediator = env._mediator
        positions = _station_positions(mediator)
        served = _served(mediator)
        unserved = [i for i in range(len(positions)) if i not in served]
        legal = _legal_by_kind(env)

        if ActionKind.PURCHASE_LINE in legal:
            return legal[ActionKind.PURCHASE_LINE][0][0]

        if len(mediator.paths) == 1 and len(positions) >= 5:
            route = _path_indices(mediator, mediator.paths[0])
            if len(route) >= 5:
                current = _route_length(positions, route)
                target, improved = _two_opt(positions, route)
                if current > 0:
                    worst, waiting = _pressure(mediator)
                    features = np.array(
                        [
                            (current - improved) / current,
                            len(unserved) / _UNSERVED_SCALE,
                            worst / _CAPACITY,
                            waiting / _WAITING_SCALE,
                            len(route) / 10.0,
                            1.0,
                        ]
                    )
                    if float(weights @ features) > 0.0:
                        step = _rebuild_step(env, mediator, legal, route, target)
                        if step is not None:
                            return step

        grafted = _graft(env, mediator, legal, positions, unserved, lambda path: 0.0)
        if grafted is not None:
            return grafted

        connected = _connect(mediator, legal, positions, unserved)
        if connected is not None:
            return connected

        for kind in (ActionKind.ASSIGN_LOCOMOTIVE, ActionKind.ATTACH_CARRIAGE):
            if kind in legal:
                return legal[kind][0][0]
        return 0

    return choose


def load_learned_trigger(path="output/trigger/best.json"):
    import json

    with open(path, encoding="utf-8") as handle:
        return make_learned_rebuilder(json.load(handle)["mean_weights"])


# Each entry changes exactly one rule. The scale on a graft penalty is in
# canonical pixels, so it is comparable with the distances it is added to: a
# station is 30 px and a typical inter-station gap is a few hundred.
VARIANTS = {
    # The control. Must reproduce `rl.heuristic.choose` exactly; `paired_eval`
    # runs it beside `heuristic` and a non-zero gap means this file is wrong,
    # not that the variant is good.
    "v0-rebuilt": _make(),
    # Crew the line that has the fewest metros rather than the lowest index.
    "v1-crew-fewest-metros": _make(crew_score=lambda path: -len(path.metros)),
    # Crew the longest line, which carries the most stations' demand.
    "v2-crew-most-stations": _make(crew_score=lambda path: len(path.stations)),
    # Crew whichever line's stations have the most passengers waiting.
    "v3-crew-most-waiting": _make(
        crew_score=lambda path: sum(
            len(getattr(station, "passengers", ())) for station in path.stations
        )
    ),
    # Prefer grafting onto a SHORT line: lap time is what limits throughput, so
    # spreading stations across lines should beat piling them onto one.
    "v4-graft-prefers-short": _make(
        graft_penalty=lambda path: 40.0 * len(path.stations)
    ),
    # The opposite, as a direction check. If both lose, the rule is not the
    # binding constraint; if only one loses, the sign is informative.
    "v5-graft-prefers-long": _make(
        graft_penalty=lambda path: -40.0 * len(path.stations)
    ),
    # Hold the line slot until there is work for it.
    "v6-defer-purchase": _make(defer_purchase=2),
    # Spend the spare slot immediately on the two closest stations, served or
    # not. One line for nine stations means a lap the length of the whole map
    # and one train to walk it.
    "v7-second-line-closest": _make(spare_line="closest-any-pair"),
    # The same, on the two farthest apart -- a cross-town line rather than a
    # short hop, in case the closest pair merely duplicates an existing leg.
    "v8-second-line-farthest": _make(spare_line="farthest-any-pair"),
    # Do not graft while a slot is spare: hold out for a second unserved
    # station and open the new line with that pair. Costs waiting passengers at
    # an unserved station, which is the 40-second overcrowding clock.
    "v9-hold-for-second-line": _make(spare_line="hold-for-unserved"),
    # v7 lost 80 deliveries and ENDED EARLIER (5,078 decisions against 6,766),
    # so the second line is not merely useless, it is actively harmful --
    # consistent with it taking the scarce locomotive the first line needs.
    # These delay it until the network is big enough to be worth splitting.
    "v10-second-line-late-closest": _make(
        spare_line="closest-any-pair", spare_min_stations=6
    ),
    "v11-second-line-late-farthest": _make(
        spare_line="farthest-any-pair", spare_min_stations=6
    ),
    "v12-second-line-mid-farthest": _make(
        spare_line="farthest-any-pair", spare_min_stations=4
    ),
    # The LAST lever. Grafting is the only decision with more than one option,
    # and it has exactly two: head or tail. The heuristic takes the nearer end,
    # which is also the one that adds least route length, so lap time -- the
    # thing four trains are actually rationed by -- is decided here and nowhere
    # else. If taking the FAR end, or an arbitrary end, costs little, then the
    # only real decision in the game barely matters and the heuristic is at the
    # ceiling of this action space.
    "v13-graft-far-end": _make(end_rule="far"),
    "v14-graft-arbitrary-end": _make(end_rule="arbitrary"),
    # The lever the action space hides. Greedy is within ~4% of the best
    # route insertion can REACH, but insertion itself is 34% above the
    # optimal ordering, and lap time is what four trains are rationed by.
    "v15-rebuild-10pct": make_rebuilder(threshold=0.10),
    "v16-rebuild-20pct": make_rebuilder(threshold=0.20),
    "v17-rebuild-05pct": make_rebuilder(threshold=0.05),
    "v18-rebuild-30pct": make_rebuilder(threshold=0.30),
    "v19-rebuild-40pct": make_rebuilder(threshold=0.40),
    "v20-rebuild-25pct": make_rebuilder(threshold=0.25),
    "v21-rebuild-15pct": make_rebuilder(threshold=0.15),
}

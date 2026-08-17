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


def _graft(env, mediator, legal, positions, unserved, penalty):
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
        grafted = _graft(env, mediator, legal, positions, unserved, penalty)
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
}

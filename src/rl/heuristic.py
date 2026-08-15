"""A scripted policy for the semantic lane: the real baseline, and a teacher.

An adversarial review measured this strategy at **277.15 deliveries** on the
held-out seed set, beating every trained policy on this project on 17 of 20
seeds while acting about fifteen times per episode. That makes it two things at
once: the bar any learned policy must clear to be worth anything, and a source of
demonstrations for a lane where learning from scratch has repeatedly collapsed.

It is deliberately simple, and its simplicity is the point. Buy a line slot when
one is affordable, connect the two nearest stations nothing serves yet, graft each
new station onto whichever line end is closest, crew every line that will take a
locomotive or carriage, and otherwise do nothing. It never removes a line --
which matters, because random play that merely never removes already scores
181.67, while random play with removal scores zero.

Nothing here is privileged relative to the semantic observation: station
positions, line membership and fleet availability are all things the observation
already exposes. It is a policy over the same action table, not an oracle.
"""

from __future__ import annotations

import numpy as np

from rl.semantic_env import ACTION_TABLE, ActionKind


def _station_positions(mediator):
    return [(s.position.left, s.position.top) for s in mediator.stations]


def _served(mediator) -> set[int]:
    """Indices of stations that already sit on some line."""
    index = {id(s): i for i, s in enumerate(mediator.stations)}
    return {
        index[id(station)]
        for path in mediator.paths
        for station in path.stations
        if id(station) in index
    }


def _distance(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def choose(env) -> int:
    """Pick one action index for the current state, or WAIT."""
    mediator = env._mediator
    mask = env.action_masks()
    positions = _station_positions(mediator)
    served = _served(mediator)
    unserved = [i for i in range(len(positions)) if i not in served]

    legal = {}
    for index in np.flatnonzero(mask):
        kind, first, second = ACTION_TABLE[index]
        legal.setdefault(kind, []).append((index, first, second))

    # 1. A new line slot is worth more than anything else it could be spent on.
    if ActionKind.PURCHASE_LINE in legal:
        return legal[ActionKind.PURCHASE_LINE][0][0]

    # 2. Graft an unserved station onto whichever line end is nearest to it.
    #    Preferring the nearest end keeps lap time down, which is what actually
    #    limits throughput once a line is running.
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
            if best is None or gap < best[0]:
                best = (gap, index)
    if best is not None:
        return best[1]

    # 3. No line yet, or a spare slot: connect the two closest unserved stations.
    if ActionKind.CONNECT in legal and len(unserved) >= 2:
        pick = None
        for index, first, second in legal[ActionKind.CONNECT]:
            if first not in unserved or second not in unserved:
                continue
            gap = _distance(positions[first], positions[second])
            if pick is None or gap < pick[0]:
                pick = (gap, index)
        if pick is not None:
            return pick[1]

    # 4. Crew whatever will take a locomotive, then a carriage. A line without a
    #    locomotive carries nobody, so this is never worth deferring.
    for kind in (ActionKind.ASSIGN_LOCOMOTIVE, ActionKind.ATTACH_CARRIAGE):
        if kind in legal:
            return legal[kind][0][0]

    # 5. Otherwise let the metro run. Most steps should be this one.
    return 0


def play(seed: int, max_decisions: int = 200_000) -> dict:
    """Run one full episode, returning its score and what it did."""
    from rl.semantic_env import SemanticMetroEnv

    env = SemanticMetroEnv()
    env.reset(seed=seed)
    delivered = 0.0
    decisions = 0
    acted = 0
    try:
        while decisions < max_decisions:
            action = choose(env)
            if action != 0:
                acted += 1
            _, reward, terminated, truncated, _ = env.step(action)
            delivered += float(reward)
            decisions += 1
            if terminated or truncated:
                break
        mediator = env._mediator
        return {
            "seed": seed,
            "deliveries": int(delivered),
            "decisions": decisions,
            "actions_taken": acted,
            "lines": len(mediator.paths),
            "longest_line": max((len(p.stations) for p in mediator.paths), default=0),
            "stations": len(mediator.stations),
        }
    finally:
        env.close()

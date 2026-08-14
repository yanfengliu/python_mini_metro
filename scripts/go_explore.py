"""Go-Explore for this game: archive promising states, return to them, explore on.

Teacher-free learning has failed here twice for the same underlying reason. The
first passenger is unreachable by exploration — across 12 random episodes and
4170 decisions, none built a usable line — so PPO's gradient is the zero vector.
Reward shaping gave a gradient but the agent banked the budget and delivered
nothing, and paying only for the first step of the gesture drove motion and
pointer-up *below* uniform.

Go-Explore (Ecoffet et al., "First return, then explore", Nature 2021) attacks
the cause rather than the symptom. Its insight is that exploration algorithms
forget: an agent that stumbles into a promising state wanders away and cannot
find its way back. So it keeps an archive of states, **returns** to a chosen one
without exploring, and only then explores onward. Progress accumulates instead of
being rediscovered.

Two properties make it unusually well suited here, both measured rather than
assumed. The game serialises and deserialises exactly — restoring a state
reproduces the observation byte for byte — so returning costs one deserialize
rather than a replayed trajectory. And random play already lands a completed drag
in roughly 4% of episodes, so the rung that PPO cannot reach *is* reachable by
luck; what was missing is a way to keep the luck.

Note what this is not. Go-Explore's own third phase robustifies by imitation
learning, so "teacher-free" does not mean "no demonstrations" — it means the
demonstrations are the agent's own discovered trajectories rather than
privileged scripted code. The archive is a training-time device, like the
shaping wrapper; the policy it eventually trains still sees only pixels.

Random Network Distillation was considered and rejected on its documented
failure mode: it detects only large state changes, and here a drawn line moves a
few hundred of 20,736 pixels while the clock and moving metros change constantly
and mean nothing.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game_session import GameSession  # noqa: E402
from rl.player_env import INITIAL_CURSOR_POSITION, PlayerPixelEnv  # noqa: E402
from rl.privileged_oracle import capture_privileged_snapshot  # noqa: E402
from save_game import serialize_game  # noqa: E402
from save_load import deserialize_game  # noqa: E402

# Simulation-time granularity for a cell. Coarse enough that the archive
# stays small, fine enough that progress registers as a new cell.
TIME_BUCKET_MS = 5_000

# Canonical-pixel radius for 'the held pointer is on this station'.
CURSOR_HIT_CANONICAL = 40.0


@dataclass
class Cell:
    """One archived state: a saveable ancestor plus actions to replay from it.

    The game refuses to serialise mid-gesture -- "cannot save while a
    path-creation gesture is active" -- and a half-made drag is precisely the
    intermediate worth returning to. So a cell stores the last quiescent state it
    can save, and the action suffix that reaches the real one. Replay is exact
    because the game is deterministic given a state and a sequence of actions,
    which is the same determinism Go-Explore's first phase relies on.
    """

    document: dict
    actions: tuple
    deliveries: int
    decisions: int
    visits: int = 0


def capture(env: PlayerPixelEnv) -> dict:
    return serialize_game(env._require_mediator())


def restore(env: PlayerPixelEnv, document: dict) -> None:
    """Put a saved game back into a live environment.

    The session wraps the mediator, so it is rebuilt around the restored one and
    the layout re-prepared; the environment's own per-episode bookkeeping is
    reset to match, or reward deltas would be measured against a stale baseline.
    """
    mediator = deserialize_game(document)
    env._mediator = mediator
    env._session = GameSession(mediator, step_observer=env._renderer)
    env._session.prepare_layout(env._canonical_surface)
    env._last_deliveries = mediator.deliveries
    env._last_line_credits = mediator.line_credits
    env._episode_ended = False
    # A deserialised game is always quiescent, so the env's pointer state must
    # match it. Leaving a stale _pointer_down here desyncs the environment from
    # the mediator and any replayed gesture behaves differently than it did.
    env._pointer_down = False
    env._cursor = INITIAL_CURSOR_POSITION
    # Decisions accumulate across returns otherwise, and every step eventually
    # reports truncation, which silently ends exploration for good.
    env._decision = 0


def cell_key(env: PlayerPixelEnv) -> tuple:
    """A coarse signature of progress, not of pixels.

    Go-Explore's Atari work downsamples the frame; privileged game state is a
    better cell here because it names the things that actually constitute
    progress. This is training-time only and never reaches the policy.
    """
    snapshot = capture_privileged_snapshot(env)
    usable = tuple(
        sorted(
            len([s for s in path if s is not None])
            for path in snapshot.path_station_indices
            if len([s for s in path if s is not None]) >= 2
        )
    )
    # A time bucket is part of the key on purpose. Without it, sixty steps from
    # the opening changes no station count, no line and no delivery, so every
    # explored state maps back onto the start cell and the archive never grows
    # -- measured: 1 cell after 300 iterations. The bucket gives the frontier an
    # axis to advance along while staying far coarser than raw state.
    # The pointer state belongs in the key. A drag half-made -- pointer down on a
    # station, waiting for a release somewhere else -- is exactly the promising
    # intermediate the archive exists to hold: returning to it turns "complete a
    # four-action gesture by luck" into "complete the last action by luck".
    # Without it the archive only advances the clock (measured: 8 cells and zero
    # lines over 400 iterations).
    held = None
    if getattr(env, "_pointer_down", False):
        cursor = getattr(env, "_cursor", None)
        if cursor is not None:
            held = _nearest_station_index(snapshot, cursor)
    return (
        len(snapshot.station_positions),
        usable,
        snapshot.deliveries,
        snapshot.simulation_time_ms // TIME_BUCKET_MS,
        held,
    )


def _nearest_station_index(snapshot, cursor) -> int | None:
    """Which station the held pointer is on, if any."""
    x, y = (cursor.left, cursor.top) if hasattr(cursor, "left") else tuple(cursor)[:2]
    best, best_distance = None, None
    for index, (station_x, station_y) in enumerate(snapshot.station_positions):
        distance = ((station_x - x) ** 2 + (station_y - y) ** 2) ** 0.5
        if best_distance is None or distance < best_distance:
            best, best_distance = index, distance
    if best_distance is None or best_distance > CURSOR_HIT_CANONICAL:
        return None
    return best


def explore(env: PlayerPixelEnv, steps: int) -> tuple[bool, list]:
    """Take random actions, returning whether the run ended and what was taken."""
    taken = []
    for _ in range(steps):
        action = env.action_space.sample()
        taken.append(action)
        _, _, terminated, truncated, _ = env.step(action)
        if terminated or truncated:
            return True, taken
    return False, taken


def enter(env: PlayerPixelEnv, cell: Cell) -> None:
    """Return to a cell: restore its ancestor, then replay to the exact state."""
    restore(env, cell.document)
    for action in cell.actions:
        env.step(action)


def run(args: argparse.Namespace) -> dict[str, Any]:
    env = PlayerPixelEnv()
    env.action_space.seed(args.seed)
    env.reset(seed=args.seed)
    rng = np.random.default_rng(args.seed)

    archive: dict[tuple, Cell] = {}
    start = cell_key(env)
    archive[start] = Cell(capture(env), (), 0, 0)
    best = 0
    iterations = 0

    while iterations < args.iterations:
        iterations += 1
        # Prefer rarely-visited cells: Go-Explore's selection pressure is toward
        # the frontier, not toward whatever scored best so far.
        keys = list(archive)
        weights = np.array([1.0 / (1.0 + archive[k].visits) for k in keys])
        chosen = keys[int(rng.choice(len(keys), p=weights / weights.sum()))]
        source = archive[chosen]
        source.visits += 1

        enter(env, source)
        ended, taken = explore(env, args.explore_steps)
        decisions = source.decisions + len(taken)

        if ended:
            continue
        key = cell_key(env)
        snapshot = capture_privileged_snapshot(env)
        known = archive.get(key)
        if known is None or decisions < known.decisions:
            try:
                # Prefer a fresh save: it keeps replay suffixes from growing
                # without bound as the frontier advances.
                archive[key] = Cell(capture(env), (), snapshot.deliveries, decisions)
            except ValueError:
                # Mid-gesture, so anchor to this cell's ancestor plus the suffix.
                archive[key] = Cell(
                    source.document,
                    tuple(source.actions) + tuple(taken),
                    snapshot.deliveries,
                    decisions,
                )
        if snapshot.deliveries > best:
            best = snapshot.deliveries
            print(
                f"  iteration {iterations}: new best {best} deliveries "
                f"after {decisions} decisions ({len(archive)} cells)"
            )

    env.close()
    delivering = [c for c in archive.values() if c.deliveries > 0]
    return {
        "iterations": iterations,
        "cells": len(archive),
        "best_deliveries": best,
        "cells_with_a_delivery": len(delivering),
        "cells_with_a_line": len([k for k in archive if k[1]]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=400)
    parser.add_argument("--explore-steps", type=int, default=60)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print(
        f"go-explore: {args.iterations} iterations x {args.explore_steps} random "
        f"steps, seed {args.seed}"
    )
    summary = run(args)
    print()
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("reference: random play delivers 0; the scripted expert ~19-20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

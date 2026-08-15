"""Generate training labels by search rather than by asking the heuristic.

Every learned policy so far has imitated the scripted heuristic, and a probe on
seed 9000 showed why that was always going to cap out:

    decision 0: heuristic CONNECT(0,2) -> 275 deliveries
                          CONNECT(0,1) -> 380 deliveries
    decision 1: heuristic PREPEND_LINE(0,1) -> 275
                          ASSIGN_LOCOMOTIVE(0,0) -> 398

The teacher is roughly 40% below what its own action space allows, at the very
first decision of the game. So cloning it faithfully -- which DAgger did, raising
real-decision agreement from 71.8% to 77.3% -- could only ever reproduce a
mediocre player. That is the whole explanation for the 170-195 plateau.

Search does not have that ceiling, because it measures each candidate by rolling
it to the end of the episode instead of guessing. This script runs search across
many seeds in parallel and records what it chose, producing a dataset whose
labels are better than any policy that exists here.

Labels are kept the same way behaviour cloning keeps them: every real decision,
and a small random slice of the WAITs, because roughly 99.8% of decisions are
WAIT and cloning that mix directly produces a policy that waits forever.
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from search_policy import STRUCTURAL, _restore, _rollout, _signature  # noqa: E402

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402
from save_game import serialize_game  # noqa: E402


def collect(seed: int, candidates: int, cap: int, wait_keep: float, gamma: float):
    """Play one episode by search, recording every decision it makes."""
    rng = np.random.default_rng(seed)
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=seed)
    observations, actions, masks = [], [], []
    kept_at, rewards = [], []
    searches = overrides = 0
    last_signature: frozenset | None = None

    while True:
        mask = env.action_masks()
        structural = [
            i for i in np.flatnonzero(mask) if ACTION_TABLE[i][0] in STRUCTURAL
        ]
        preferred = choose(env)
        signature = _signature(mask)

        if structural and (preferred != 0 or signature != last_signature):
            last_signature = signature
            shortlist = [preferred] if preferred != 0 else []
            shortlist += [i for i in structural if i != preferred][: candidates - 1]
            if 0 not in shortlist:
                shortlist.append(0)
            document = serialize_game(env._mediator)
            at = env._decision
            scored = [
                (_rollout(env, document, at, candidate, cap), candidate)
                for candidate in shortlist
            ]
            _restore(env, document, at)
            searches += 1
            action = max(scored)[1]
            overrides += int(action != preferred)
        else:
            action = preferred

        if action != 0 or rng.random() < wait_keep:
            observations.append(observation.copy())
            actions.append(action)
            masks.append(mask.copy())
            kept_at.append(len(rewards))

        observation, reward, terminated, truncated, _ = env.step(action)
        rewards.append(float(reward))
        if terminated or truncated:
            break

    delivered = float(sum(rewards))
    env.close()

    # Discounted return-to-go for each kept state, so the critic can be fitted
    # to what SEARCH earns from there rather than what the heuristic earns.
    togo = np.zeros(len(rewards) + 1, dtype=np.float64)
    for step in range(len(rewards) - 1, -1, -1):
        togo[step] = rewards[step] + gamma * togo[step + 1]

    return {
        "observations": np.stack(observations),
        "actions": np.array(actions, dtype=np.int64),
        "masks": np.stack(masks),
        "returns": np.array([togo[at] for at in kept_at], dtype=np.float32),
        "deliveries": delivered,
        "searches": searches,
        "overrides": overrides,
        "seed": seed,
    }


def _one(job):
    return collect(*job)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20_000)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--cap", type=int, default=20_000)
    parser.add_argument("--wait-keep", type=float, default=0.02)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument(
        "--output", type=Path, default=Path("output/semantic/search-data.npz")
    )
    args = parser.parse_args(argv)

    jobs = [
        (args.seed + i, args.candidates, args.cap, args.wait_keep, args.gamma)
        for i in range(args.episodes)
    ]
    print(
        f"searching {args.episodes} episodes on {args.workers} workers; "
        f"the heuristic scores ~262 and search should exceed it"
    )
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(_one, jobs):
            results.append(result)
            print(
                f"  seed {result['seed']}: {result['deliveries']:6.0f} deliveries, "
                f"{result['searches']:3d} searches, "
                f"{result['overrides']:3d} overrode the heuristic, "
                f"{len(result['actions']):4d} labels",
                flush=True,
            )

    scores = np.array([r["deliveries"] for r in results])
    stacked = {
        key: np.concatenate([r[key] for r in results])
        for key in ("observations", "actions", "masks", "returns")
    }
    kinds: dict[str, int] = {}
    for action in stacked["actions"]:
        name = ActionKind(ACTION_TABLE[action][0]).name
        kinds[name] = kinds.get(name, 0) + 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        observations=stacked["observations"],
        actions=stacked["actions"],
        masks=stacked["masks"],
        returns=stacked["returns"],
    )
    stderr = scores.std(ddof=1) / np.sqrt(len(scores)) if len(scores) > 1 else 0.0
    print(
        f"\nsearch scored mean {scores.mean():.2f} +/-{1.96 * stderr:.2f} "
        f"(median {np.median(scores):.0f}, max {scores.max():.0f}) "
        f"against the heuristic's ~262"
    )
    print(f"dataset: {len(stacked['actions'])} labels, mix {kinds}")
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

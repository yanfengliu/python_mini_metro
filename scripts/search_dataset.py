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
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from search_policy import (  # noqa: E402
    STRUCTURAL,
    _restore,
    _rollout,
    _signature,
    shortlist_for,
)

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402
from save_game import serialize_game  # noqa: E402


def collect(seed: int, candidates: int, cap: int, wait_keep: float, gamma: float):
    """Play one episode by search, recording every decision it makes."""
    rng = np.random.default_rng(seed)
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=seed)
    observations, actions, masks = [], [], []
    # Every rollout search performs, not just the one it acted on. A search
    # point costs `candidates` full-episode simulations and the argmax throws
    # away all but one of them -- five sixths of the most expensive computation
    # here. Keeping the losing evaluations turns each search point into a full
    # preference ordering over its shortlist, which is the AlphaZero policy
    # target rather than a single hard label.
    evaluated, kept_at, rewards = [], [], []
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
            shortlist = shortlist_for(rng, structural, preferred, candidates)
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
            evaluated.append(
                {
                    "at": len(rewards),
                    "actions": np.array([a for _, a in scored], dtype=np.int64),
                    "values": np.array([v for v, _ in scored], dtype=np.float32),
                }
            )
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

    # The evaluations are stored flat with an index per row, since each search
    # point has a different shortlist length and ragged arrays do not survive
    # npz cleanly.
    flat_row, flat_action, flat_value = [], [], []
    at_to_row = {at: row for row, at in enumerate(kept_at)}
    for record in evaluated:
        row = at_to_row.get(record["at"])
        if row is None:
            # The search point was a WAIT that subsampling dropped; its
            # observation was never kept, so its evaluations have nothing to
            # attach to.
            continue
        for action_index, value in zip(record["actions"], record["values"]):
            flat_row.append(row)
            flat_action.append(int(action_index))
            flat_value.append(float(value))

    return {
        "observations": np.stack(observations),
        "actions": np.array(actions, dtype=np.int64),
        "masks": np.stack(masks),
        "returns": np.array([togo[at] for at in kept_at], dtype=np.float32),
        "eval_row": np.array(flat_row, dtype=np.int64),
        "eval_action": np.array(flat_action, dtype=np.int64),
        "eval_value": np.array(flat_value, dtype=np.float32),
        "deliveries": delivered,
        "searches": searches,
        "overrides": overrides,
        "seed": seed,
    }


def _one(job):
    return collect(*job)


def save(path, results) -> dict[str, int]:
    """Write everything collected so far, and report the label mix."""
    stacked = {
        key: np.concatenate([r[key] for r in results])
        for key in ("observations", "actions", "masks", "returns")
    }
    # `eval_row` indexes into each episode's own observations, so concatenating
    # episodes has to shift every index by the rows already written. Getting
    # this wrong would silently attach one episode's rollout values to another
    # episode's board.
    rows, offset = [], 0
    for result in results:
        rows.append(result["eval_row"] + offset)
        offset += len(result["actions"])
    eval_row = np.concatenate(rows) if rows else np.zeros(0, dtype=np.int64)

    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        observations=stacked["observations"],
        actions=stacked["actions"],
        masks=stacked["masks"],
        returns=stacked["returns"],
        eval_row=eval_row,
        eval_action=np.concatenate([r["eval_action"] for r in results]),
        eval_value=np.concatenate([r["eval_value"] for r in results]),
    )
    kinds: dict[str, int] = {}
    for action in stacked["actions"]:
        name = ActionKind(ACTION_TABLE[action][0]).name
        kinds[name] = kinds.get(name, 0) + 1
    return kinds


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
        f"the heuristic scores ~262 and search should exceed it",
        flush=True,
    )
    results = []
    # Results are written after every episode rather than once at the end.
    # A search episode costs tens of minutes -- the better search plays, the
    # longer the game runs and the more decision points it accrues -- so a run
    # that saved only on completion would throw away hours if one slow seed
    # hung or the process died. `as_completed` also means a single long episode
    # no longer hides the results of every episode that finished before it,
    # which is how a healthy run came to look wedged.
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_one, job): job[0] for job in jobs}
        for done in as_completed(futures):
            result = done.result()
            results.append(result)
            print(
                f"  seed {result['seed']}: {result['deliveries']:6.0f} deliveries, "
                f"{result['searches']:3d} searches, "
                f"{result['overrides']:3d} overrode the heuristic, "
                f"{len(result['actions']):4d} labels "
                f"[{len(results)}/{len(jobs)} done]",
                flush=True,
            )
            save(args.output, results)

    scores = np.array([r["deliveries"] for r in results])
    kinds = save(args.output, results)
    labels = sum(kinds.values())
    stderr = scores.std(ddof=1) / np.sqrt(len(scores)) if len(scores) > 1 else 0.0
    print(
        f"\nsearch scored mean {scores.mean():.2f} +/-{1.96 * stderr:.2f} "
        f"(median {np.median(scores):.0f}, max {scores.max():.0f}) "
        f"against the heuristic's ~262"
    )
    print(f"dataset: {labels} labels, mix {kinds}")
    print(
        f"  plus {len(np.load(args.output)['eval_value'])} scored rollouts kept as "
        "preference targets"
    )
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

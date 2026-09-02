"""Script the forced decisions, learn only the ones that matter -- and ablate it.

Most steps in this game are not decisions. The scripted heuristic acts about 17
times in 8,000 steps, and the rest are WAIT. Training a network on that mixture
spends nearly all of its capacity learning to do nothing, and measured agreement
is dominated by the decisions that carry no value.

The hybrid runs the heuristic everywhere and hands control to the policy only at
decision points. The gate is deliberately the same one search uses, and it is
computable from the observation alone -- a structural action is legal, and either
the heuristic wants to act or the set of available capabilities has changed. A
gate that needed the future would be privileged information the policy will not
have at test time, which would make the whole arrangement circular.

Three players are compared, on identical seeds, because the interesting question
is not whether the hybrid scores well but whether the *network* is contributing:

  heuristic   the script alone, ~267 deliveries
  hybrid      script everywhere, policy at decision points
  ablated     script everywhere, RANDOM legal choice at the same points

`ablated` is the control that matters. If the hybrid does not clearly beat it,
the network is decoration and the script is playing the game.
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

from search_policy import STRUCTURAL, _signature  # noqa: E402

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, SemanticMetroEnv  # noqa: E402

PLAYERS = ("heuristic", "hybrid", "ablated", "policy")


def play(player: str, seed: int, model=None) -> dict:
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=seed)
    rng = np.random.default_rng(seed)
    delivered = 0.0
    handovers = 0
    last_signature: frozenset | None = None

    while True:
        mask = env.action_masks()
        preferred = choose(env)

        if player == "heuristic":
            action = preferred
        elif player == "policy":
            predicted, _ = model.predict(
                observation, action_masks=mask, deterministic=False
            )
            action = int(np.asarray(predicted).ravel()[0])
        else:
            structural = [
                i for i in np.flatnonzero(mask) if ACTION_TABLE[i][0] in STRUCTURAL
            ]
            signature = _signature(mask)
            pivotal = structural and (preferred != 0 or signature != last_signature)
            if not pivotal:
                action = preferred
            else:
                last_signature = signature
                handovers += 1
                if player == "ablated":
                    action = int(rng.choice(np.flatnonzero(mask)))
                else:
                    predicted, _ = model.predict(
                        observation, action_masks=mask, deterministic=False
                    )
                    action = int(np.asarray(predicted).ravel()[0])

        observation, reward, terminated, truncated, _ = env.step(action)
        delivered += float(reward)
        if terminated or truncated:
            break

    mediator = env._mediator
    result = {
        "seed": seed,
        "deliveries": int(delivered),
        "handovers": handovers,
        "lines": len(mediator.paths),
        "longest_line": max((len(p.stations) for p in mediator.paths), default=0),
    }
    env.close()
    return result


def _one(job):
    player, seed, path = job
    model = None
    if player in ("hybrid", "policy"):
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(path), device="cpu")
    return player, play(player, seed, model)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("output/semantic/distilled"))
    # 20, the pre-registered minimum in docs/rl-model-selection.md.
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=50_000)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args(argv)

    seeds = [args.seed + i for i in range(args.episodes)]
    jobs = [(player, seed, args.model) for player in PLAYERS for seed in seeds]
    print(
        f"{args.episodes} seeds x {len(PLAYERS)} players; the network is only "
        f"contributing if `hybrid` clearly beats `ablated`",
        flush=True,
    )

    scores: dict[str, dict[int, int]] = {player: {} for player in PLAYERS}
    handovers: list[int] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for player, result in pool.map(_one, jobs):
            scores[player][result["seed"]] = result["deliveries"]
            if player == "hybrid":
                handovers.append(result["handovers"])

    print(f"\nthe policy was consulted at {np.mean(handovers):.1f} points per game")
    for player in PLAYERS:
        values = np.array([scores[player][s] for s in seeds], dtype=float)
        stderr = values.std(ddof=1) / np.sqrt(len(values)) if len(values) > 1 else 0.0
        print(
            f"  {player:<10} mean {values.mean():7.2f} +/-{1.96 * stderr:6.2f}  "
            f"median {np.median(values):6.1f}  max {values.max():.0f}"
        )

    def paired(left: str, right: str) -> None:
        gap = np.array([scores[left][s] - scores[right][s] for s in seeds], dtype=float)
        stderr = gap.std(ddof=1) / np.sqrt(len(gap)) if len(gap) > 1 else 0.0
        verdict = "BEATS" if gap.mean() - 1.96 * stderr > 0 else "does NOT beat"
        print(
            f"  {left} {verdict} {right}: paired {gap.mean():+.2f} "
            f"+/-{1.96 * stderr:.2f}, won {int((gap > 0).sum())}/{len(gap)}"
        )

    print()
    paired("hybrid", "ablated")
    paired("hybrid", "heuristic")
    paired("policy", "heuristic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

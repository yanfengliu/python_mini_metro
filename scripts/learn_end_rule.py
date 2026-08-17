"""Learn the one decision this game has, by optimising the outcome directly.

E46 measured that the action space offers exactly one choice with more than one
option -- which END of the single line a new station joins -- and that it spans
104 deliveries: nearest 253.3, arbitrary 193.1, farthest 149.1. Every learned
policy this project has produced scores 175-189, which is the band an arbitrary
rule produces. So beating the scripted policy means beating **greedy
nearest-end insertion**, and nothing else in this action space is worth
optimising.

Greedy is not optimal for growing a path: a sequence of locally minimal
insertions can lose to one that occasionally takes the longer end. That residual
is what honest search measured at +7.55 +/-17.70 (n=20, E36) and nobody has
re-measured.

**Why cross-entropy method and not PPO.** Per-episode deliveries have a standard
deviation near 95 while the effect being chased is order 10, and the decision
fires about 59 times an episode. PPO has to attribute an episode-scale outcome
to individual actions through a value function, and the residual run measured
what that costs: it spent 30,000 steps un-learning the noise of its own
initialisation (E45). CEM never attributes anything to an action. It scores a
whole policy against the scripted one **on identical seeds**, so board luck
cancels inside every comparison, and it searches six numbers instead of forty
thousand.

**The search starts AT the heuristic.** Weights `[-1, 0, 0, 0, 0, 0]` score each
candidate end by the negative distance to it, which is exactly "take the nearest
end". Generation zero is therefore the bar itself, and this is checked rather
than asserted -- the opening report prints the mean weight vector's paired gap,
which must be 0.00 on every seed.

**Selection is separated from reporting.** The search optimises on one seed base
and the result must be confirmed on another with `paired_eval.py`; the best-of-N
gap printed here is a selection statistic and is labelled as one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

Z95 = 1.959963985
# 80%-power minimum detectable effect, matching paired_eval.py.
MDE80 = 2.801585

# The weights that reproduce the scripted rule exactly: score = -gap, so the
# nearest end wins. Every other feature starts at zero, so generation zero is
# the bar and the search is a residual around it.
HEURISTIC_WEIGHTS = np.array([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0])

FEATURE_NAMES = (
    "-gap_to_this_end",
    "gap_to_other_end",
    "is_head",
    "stations_on_line",
    "route_length",
    "bias",
)


def _episode(job) -> float:
    """One episode of the weighted policy, or of the scripted policy."""
    weights, seed = job
    from heuristic_variants import make_end_scorer

    from rl.event_gate import EventGatedSemanticEnv
    from rl.heuristic import choose

    policy = choose if weights is None else make_end_scorer(np.asarray(weights))
    env = EventGatedSemanticEnv()
    env.reset(seed=seed)
    total = 0.0
    try:
        while True:
            _, reward, terminated, truncated, _ = env.step(policy(env.inner))
            total += float(reward)
            if terminated or truncated:
                break
    finally:
        env.close()
    return total


def evaluate(pool, weights, seeds) -> np.ndarray:
    """Per-seed deliveries for one weight vector."""
    return np.array(
        list(pool.map(_episode, [(weights, s) for s in seeds], chunksize=1))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generations", type=int, default=8)
    parser.add_argument("--population", type=int, default=14)
    parser.add_argument("--elite", type=int, default=4)
    parser.add_argument("--sigma", type=float, default=0.35)
    parser.add_argument("--sigma-decay", type=float, default=0.85)
    parser.add_argument("--episodes", type=int, default=40)
    parser.add_argument("--seed-base", type=int, default=70_000)
    parser.add_argument("--workers", type=int, default=min(28, os.cpu_count() or 4))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="output/endrule/best.json")
    args = parser.parse_args(argv)

    seeds = [args.seed_base + i for i in range(args.episodes)]
    rng = np.random.default_rng(args.seed)
    mean = HEURISTIC_WEIGHTS.copy()
    sigma = np.full(len(mean), args.sigma)
    started = time.time()

    print(
        f"CEM on the graft-end rule: {args.generations} generations x "
        f"{args.population} candidates x {args.episodes} paired seeds "
        f"= {args.generations * args.population * args.episodes} episodes",
        flush=True,
    )
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        base = evaluate(pool, None, seeds)
        print(
            f"scripted heuristic on the search seeds: {base.mean():.2f} "
            f"({time.time() - started:.0f}s)",
            flush=True,
        )
        # Generation zero must BE the heuristic, not merely resemble it.
        opening = evaluate(pool, HEURISTIC_WEIGHTS, seeds)
        drift = float(np.abs(opening - base).max())
        print(
            f"weights {HEURISTIC_WEIGHTS.tolist()} reproduce it: "
            f"max per-seed |difference| = {drift:.2f}"
            + (
                ""
                if drift == 0
                else "   <-- NOT the heuristic, the search is not anchored"
            ),
            flush=True,
        )
        if drift != 0:
            return 1

        best = (0.0, HEURISTIC_WEIGHTS.copy())
        history = []
        for generation in range(args.generations):
            population = [
                mean + sigma * rng.standard_normal(len(mean))
                for _ in range(args.population)
            ]
            scored = []
            for weights in population:
                values = evaluate(pool, weights, seeds)
                diff = values - base
                scored.append((float(diff.mean()), weights, diff))
            scored.sort(key=lambda row: -row[0])
            elites = scored[: args.elite]
            mean = np.mean([row[1] for row in elites], axis=0)
            sigma = np.maximum(
                np.std([row[1] for row in elites], axis=0), sigma * args.sigma_decay
            )
            top_gap, top_weights, top_diff = scored[0]
            half = Z95 * float(np.std(top_diff, ddof=1)) / np.sqrt(len(top_diff))
            if top_gap > best[0]:
                best = (top_gap, top_weights.copy())
            history.append({"generation": generation, "gap": top_gap, "ci95": half})
            print(
                f"[gen {generation:>2}] best-of-{args.population} gap "
                f"{top_gap:+7.2f} +/-{half:.2f}  "
                f"won {int(np.sum(top_diff > 0))}/{len(top_diff)}  "
                f"elite mean gap {np.mean([r[0] for r in elites]):+7.2f}  "
                f"sigma {sigma.mean():.3f}  ({(time.time() - started) / 60:.1f} min)",
                flush=True,
            )

        final = evaluate(pool, mean, seeds)
        final_diff = final - base
        final_half = Z95 * float(np.std(final_diff, ddof=1)) / np.sqrt(len(final_diff))
        final_mde = MDE80 * float(np.std(final_diff, ddof=1)) / np.sqrt(len(final_diff))

    print(
        "\nfinal mean weights: "
        + ", ".join(f"{n}={w:+.3f}" for n, w in zip(FEATURE_NAMES, mean))
    )
    print(
        f"on the SEARCH seeds (a selection statistic, not a result): "
        f"{final.mean():.2f} vs {base.mean():.2f}, gap {final_diff.mean():+.2f} "
        f"+/-{final_half:.2f}, MDE(80%) +/-{final_mde:.2f}"
    )
    print(
        "CONFIRM ON HELD-OUT SEEDS before believing any of this:\n"
        "  python scripts/paired_eval.py --arms heuristic variant:learned "
        "--episodes 200 --seed-base 90000"
    )
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "mean_weights": mean.tolist(),
                "best_seen_weights": best[1].tolist(),
                "best_seen_gap_on_search_seeds": best[0],
                "final_gap_on_search_seeds": float(final_diff.mean()),
                "final_ci95": final_half,
                "search_seeds": seeds,
                "feature_names": list(FEATURE_NAMES),
                "history": history,
            },
            handle,
            indent=2,
        )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

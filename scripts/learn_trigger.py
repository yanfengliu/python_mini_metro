"""Learn WHEN to rebuild, against the hand-tuned constant that currently decides.

E48 beat the scripted policy by tearing the line down and re-laying it in a
2-opt order whenever that saved more than a fixed 20%. The constant is the whole
policy, and the dose-response around it is steep: measured at n=200 per arm, a
5% trigger is worth **-19.95** against the scripted bar, 20% is worth **+31.82**,
40% is worth **+2.73**. A single constant sitting on a curve that sharp is
leaving value behind, because whether a rebuild pays depends on the state --
tearing the line down while every queue is full is a different proposition from
doing it while the board is quiet, and a constant cannot tell the two apart.

So this searches a six-weight rule over the saving plus four things the constant
cannot see: unserved stations, the worst queue, the total waiting, and the
length of the line. The trigger fires when `weights . features > 0`.

**The baseline is the hand-tuned constant, not the scripted heuristic.** The
question is whether learning beats hand-tuning, so the paired comparison is
against `v16-rebuild-20pct` throughout. Beating the original heuristic would
prove nothing here -- E48 already does that, and this policy family contains it.

**The anchor is checked, not asserted.** `TRIGGER_ANCHOR` is
`[1, 0, 0, 0, 0, -0.20]`, which scores `saving - 0.20` and therefore fires on
exactly the states the fixed rule fires on. The run refuses to start unless the
max per-seed difference against `v16-rebuild-20pct` is exactly 0.00. An earlier
experiment in this project asserted its starting point instead of measuring it,
was wrong by 37 deliveries, and spent 30,000 steps un-learning the difference
while printing a closing gap (E45).

**Selection is separated from reporting.** The search optimises on one seed base
and prints its best-of-N gap labelled as a selection statistic; it is a result
only after a paired confirmation on seeds it has never seen.
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
MDE80 = 2.801585


def _episode(job) -> float:
    """One episode of the baseline or of a candidate trigger."""
    weights, seed = job
    from heuristic_variants import VARIANTS, make_learned_rebuilder

    from rl.event_gate import EventGatedSemanticEnv

    policy = (
        VARIANTS["v16-rebuild-20pct"]
        if weights is None
        else make_learned_rebuilder(np.asarray(weights))
    )
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


def evaluate_many(pool, population, seeds) -> list[np.ndarray]:
    """Every candidate's per-seed deliveries, through ONE barrier.

    Scoring candidates one at a time makes each its own barrier, and a
    `pool.map` finishes when its slowest task does; episode length varies
    several-fold with how well a policy plays, so that left 28 workers running
    at 3.5 cores busy. One job list per generation is the only barrier CEM needs.
    """
    jobs = [(weights, seed) for weights in population for seed in seeds]
    flat = list(pool.map(_episode, jobs, chunksize=1))
    width = len(seeds)
    return [
        np.array(flat[index * width : (index + 1) * width])
        for index in range(len(population))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generations", type=int, default=6)
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--elite", type=int, default=4)
    parser.add_argument("--sigma", type=float, default=0.25)
    parser.add_argument("--sigma-decay", type=float, default=0.85)
    parser.add_argument("--episodes", type=int, default=60)
    parser.add_argument("--seed-base", type=int, default=70_000)
    parser.add_argument("--workers", type=int, default=min(28, os.cpu_count() or 4))
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--out", default="output/trigger/best.json")
    args = parser.parse_args(argv)

    from heuristic_variants import TRIGGER_ANCHOR, TRIGGER_FEATURES

    anchor = np.array(TRIGGER_ANCHOR, dtype=float)
    seeds = [args.seed_base + i for i in range(args.episodes)]
    rng = np.random.default_rng(args.seed)
    mean = anchor.copy()
    sigma = np.full(len(mean), args.sigma)
    started = time.time()

    print(
        f"CEM on the rebuild trigger: {args.generations} generations x "
        f"{args.population} candidates x {args.episodes} paired seeds "
        f"= {args.generations * args.population * args.episodes} episodes",
        flush=True,
    )
    print("baseline is the HAND-TUNED CONSTANT (v16-rebuild-20pct).", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        base = evaluate_many(pool, [None], seeds)[0]
        opening = evaluate_many(pool, [anchor], seeds)[0]
        drift = float(np.abs(opening - base).max())
        print(
            f"fixed 20% trigger on the search seeds: {base.mean():.2f} "
            f"({time.time() - started:.0f}s)\n"
            f"anchor {list(TRIGGER_ANCHOR)} reproduces it: "
            f"max per-seed |difference| = {drift:.2f}"
            + ("" if drift == 0 else "   <-- NOT the fixed rule; search unanchored"),
            flush=True,
        )
        if drift != 0:
            return 1

        history = []
        for generation in range(args.generations):
            population = [
                mean + sigma * rng.standard_normal(len(mean))
                for _ in range(args.population)
            ]
            results = evaluate_many(pool, population, seeds)
            scored = [
                (float((values - base).mean()), weights, values - base)
                for weights, values in zip(population, results)
            ]
            scored.sort(key=lambda row: -row[0])
            elites = scored[: args.elite]
            mean = np.mean([row[1] for row in elites], axis=0)
            sigma = np.maximum(
                np.std([row[1] for row in elites], axis=0), sigma * args.sigma_decay
            )
            top_gap, _, top_diff = scored[0]
            half = Z95 * float(np.std(top_diff, ddof=1)) / np.sqrt(len(top_diff))
            history.append({"generation": generation, "gap": top_gap, "ci95": half})
            print(
                f"[gen {generation:>2}] best-of-{args.population} gap "
                f"{top_gap:+7.2f} +/-{half:.2f}  "
                f"won {int(np.sum(top_diff > 0))}/{len(top_diff)}  "
                f"elite mean gap {np.mean([r[0] for r in elites]):+7.2f}  "
                f"sigma {sigma.mean():.3f}  ({(time.time() - started) / 60:.1f} min)",
                flush=True,
            )

        final = evaluate_many(pool, [mean], seeds)[0]

    diff = final - base
    half = Z95 * float(np.std(diff, ddof=1)) / np.sqrt(len(diff))
    mde = MDE80 * float(np.std(diff, ddof=1)) / np.sqrt(len(diff))
    print(
        "\nfinal weights: "
        + ", ".join(f"{n}={w:+.3f}" for n, w in zip(TRIGGER_FEATURES, mean))
    )
    print(
        f"on the SEARCH seeds (a selection statistic, not a result): "
        f"{final.mean():.2f} vs {base.mean():.2f}, gap {diff.mean():+.2f} "
        f"+/-{half:.2f}, MDE(80%) +/-{mde:.2f}"
    )
    print(
        "CONFIRM ON HELD-OUT SEEDS:\n"
        "  python scripts/paired_eval.py --arms variant:v16-rebuild-20pct "
        "variant:trigger --reference variant:v16-rebuild-20pct "
        "--episodes 200 --seed-base 90000"
    )
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "mean_weights": mean.tolist(),
                "feature_names": list(TRIGGER_FEATURES),
                "anchor": list(TRIGGER_ANCHOR),
                "gap_on_search_seeds": float(diff.mean()),
                "ci95": half,
                "search_seeds": seeds,
                "history": history,
            },
            handle,
            indent=2,
        )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

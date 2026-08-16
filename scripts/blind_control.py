"""The null every claim in this project should have been measured against.

A network fed a CONSTANT vector, sampling under the legality mask, scores about
204 deliveries. What such a network learns is the MARGINAL action distribution of
its labels -- roughly 99.8% WAIT -- so it is a prior over actions with no state
information whatsoever.

That is emphatically not uniform-over-legal, which is the repo's `random` control
and scores 0.00: uniform keeps redrawing lines and the game collapses. Measured
here at n=100, uniform-over-legal reaches a longest line of 2.02 and delivers
nothing. The distinction is the whole point of this file. The distilled policy scores 203.71 +/-35.77. Five architectures
converged on a 158-195 band and were reported as beating controls that score
189.75 (`oneline`) and 0.00 (`random`) -- both BELOW this one. So every
"beats the baseline" result in this repository was measured against a broken
null, and the 158-195 band is not a property of imitation at all: it is the
score of mask-restricted prior sampling.

`random` scores 0 for a reason that makes it useless as a control: uniform over
ALL legal actions keeps redrawing lines, and the game collapses. Restricting to
the same legality mask a policy uses, but choosing with no information, isolates
exactly what the action mask alone is worth.

That number is the bar. A learned policy that does not clear it has not learned
to play; it has learned to sample.
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

from rl.semantic_env import ACTION_TABLE, SemanticMetroEnv  # noqa: E402

PLAYERS = ("blind", "policy")

# The dataset whose label marginal the blind control samples.
DATASET = Path("output/semantic/search-data.npz")


def play(player: str, seed: int, model=None, prior=None) -> dict:
    """One episode. `blind` never looks at the observation."""
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=seed)
    # Seeded per episode: stable_baselines3's load() does NOT call
    # set_random_seed, which is why earlier stochastic arms here were never
    # reproducible across runs.
    rng = np.random.default_rng(seed)
    if model is not None:
        import torch

        torch.manual_seed(seed)

    delivered = 0.0
    decisions = 0
    while True:
        mask = env.action_masks()
        if player == "blind":
            # Sample the MARGINAL action prior, restricted to legal actions and
            # renormalised. This is what a network fed constant input converges
            # to, and it is the honest null: it knows how often each action is
            # taken and nothing about the board.
            weights = prior[mask]
            total = weights.sum()
            legal = np.flatnonzero(mask)
            if total <= 0:
                action = int(rng.choice(legal))
            else:
                action = int(rng.choice(legal, p=weights / total))
        else:
            predicted, _ = model.predict(
                observation, action_masks=mask, deterministic=False
            )
            action = int(np.asarray(predicted).ravel()[0])
        observation, reward, terminated, truncated, _ = env.step(action)
        delivered += float(reward)
        decisions += 1
        if terminated or truncated:
            break

    mediator = env._mediator
    result = {
        "seed": seed,
        "deliveries": int(delivered),
        "decisions": decisions,
        # The primary outcome. longest_line alone explains R^2=0.892 of delivery
        # variance, and deliveries is a 4-5 rung ladder with ~90-delivery
        # spacing, so reporting deliveries alone costs roughly 3x the sample
        # size for the same certainty.
        "longest_line": max((len(p.stations) for p in mediator.paths), default=0),
        "lines": len(mediator.paths),
        "stations": len(mediator.stations),
    }
    env.close()
    return result


def action_prior(path: Path | None = None) -> np.ndarray:
    """The label marginal a network fed constant input converges to.

    Which distribution this is matters enormously, and two wrong answers are
    instructive. The heuristic's TRUE marginal is ~99.8% WAIT: sampling it
    builds nothing and scores 0.00 with a longest line of 0.38. Uniform over
    legal actions is the repo's `random` control: it redraws lines constantly
    and also scores 0.00, longest line 2.02.

    The distribution that matters is the TRAINING SET's marginal, because that
    is what a network trained on constant input actually fits. Behaviour cloning
    here subsamples WAIT at wait_keep=0.02, so the dataset is roughly 90% WAIT
    rather than 99.8% -- a policy sampling it acts about an order of magnitude
    more often than the teacher it was cloned from. That is the honest null: it
    knows the action frequencies its training data implied, and nothing about
    the board.
    """
    counts = np.ones(len(ACTION_TABLE), dtype=np.float64)  # Laplace
    if path is not None and path.exists():
        actions = np.load(path)["actions"]
        for action in actions:
            counts[int(action)] += 1.0
    return counts / counts.sum()


def _one(job):
    player, seed, path = job
    model = None
    if player == "policy":
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(path), device="cpu")
    return player, play(player, seed, model, prior=action_prior(DATASET))


def summarise(label: str, values: list[float]) -> dict:
    array = np.array(values, dtype=float)
    stderr = array.std(ddof=1) / np.sqrt(len(array)) if len(array) > 1 else 0.0
    return {
        "label": label,
        "n": len(array),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "q1": float(np.percentile(array, 25)),
        "q3": float(np.percentile(array, 75)),
        "ci95": float(1.96 * stderr),
        "max": float(array.max()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=70_000)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args(argv)

    seeds = [args.seed + i for i in range(args.episodes)]
    players = PLAYERS if args.model else ("blind",)
    jobs = [(player, seed, args.model) for player in players for seed in seeds]
    print(
        f"{args.episodes} paired seeds; the bar is masked-prior sampling, not "
        f"`random` or `oneline`",
        flush=True,
    )

    scores: dict[str, dict[int, dict]] = {p: {} for p in players}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for player, result in pool.map(_one, jobs):
            scores[player][result["seed"]] = result

    for metric in ("deliveries", "longest_line"):
        print(f"\n{metric}:")
        for player in players:
            row = summarise(player, [scores[player][s][metric] for s in seeds])
            print(
                f"  {row['label']:<8} mean {row['mean']:8.2f} +/-{row['ci95']:6.2f}  "
                f"median {row['median']:6.1f}  IQR [{row['q1']:.1f}, {row['q3']:.1f}]"
            )
        if len(players) > 1:
            gap = np.array(
                [
                    scores["policy"][s][metric] - scores["blind"][s][metric]
                    for s in seeds
                ],
                dtype=float,
            )
            stderr = gap.std(ddof=1) / np.sqrt(len(gap)) if len(gap) > 1 else 0.0
            ci = 1.96 * stderr
            # The minimum detectable effect at 80% power, stated beside every
            # null. Reporting "no difference" without it is what cost several
            # earlier conclusions in this project their headlines.
            mde = 2.8 * gap.std(ddof=1) / np.sqrt(len(gap)) if len(gap) > 1 else 0.0
            verdict = "BEATS" if gap.mean() - ci > 0 else "does NOT beat"
            print(
                f"  policy {verdict} blind: paired {gap.mean():+.2f} +/-{ci:.2f}, "
                f"won {int((gap > 0).sum())}/{len(gap)}, MDE(80%) {mde:.1f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

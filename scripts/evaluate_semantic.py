"""Score a semantic-lane policy against controls, with the noise stated.

Every score claim on this project has needed a control it did not have. "Random
legal play scores 0" was quoted for a while as evidence the task is hard, when it
may only show that random play destroys its own lines. And a 5-episode mean was
reported as an effect size when a fixed policy re-measured on fixed seeds spans
30.8 to 58.6.

So this reports a policy alongside three controls on the *same* held-out seeds,
in both action-selection modes, with a per-episode distribution rather than a
bare mean:

- ``random``  -- uniform over legal actions
- ``wait``    -- never acts; measures what the simulation scores by itself
- ``oneline`` -- connects everything reachable once, assigns the fleet, then
  waits forever. This is the control that matters: if a policy cannot beat it,
  the policy is not playing, it is watching.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402

CONTROLS = ("random", "wait", "oneline")


def _first_legal(env, kinds) -> int | None:
    mask = env.action_masks()
    for index in np.flatnonzero(mask):
        if ACTION_TABLE[index][0] in kinds:
            return int(index)
    return None


def play_control(name: str, seed: int, rng: np.random.Generator) -> dict:
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    total = 0.0
    decisions = 0
    try:
        while True:
            mask = env.action_masks()
            if name == "random":
                action = int(rng.choice(np.flatnonzero(mask)))
            elif name == "wait":
                action = 0
            else:
                # Build once, crew it, then stop touching anything.
                action = _first_legal(
                    env,
                    (
                        ActionKind.CONNECT,
                        ActionKind.EXTEND_LINE,
                        ActionKind.PURCHASE_LINE,
                        ActionKind.ASSIGN_LOCOMOTIVE,
                        ActionKind.ATTACH_CARRIAGE,
                    ),
                )
                if action is None:
                    action = 0
            _, reward, terminated, truncated, _ = env.step(action)
            total += float(reward)
            decisions += 1
            if terminated or truncated:
                break
    finally:
        env.close()
    return {"score": total, "decisions": decisions}


def play_policy(model, seed: int, deterministic: bool) -> dict:
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=seed)
    total = 0.0
    decisions = 0
    try:
        while True:
            action, _ = model.predict(
                observation,
                action_masks=env.action_masks(),
                deterministic=deterministic,
            )
            observation, reward, terminated, truncated, _ = env.step(action)
            total += float(reward)
            decisions += 1
            if terminated or truncated:
                break
    finally:
        env.close()
    return {"score": total, "decisions": decisions}


def summarise(label: str, scores: list[float]) -> dict:
    array = np.array(scores, dtype=float)
    # Standard error of the mean, so a difference can be judged rather than eyeballed.
    stderr = array.std(ddof=1) / np.sqrt(len(array)) if len(array) > 1 else 0.0
    return {
        "label": label,
        "n": len(array),
        "mean": round(float(array.mean()), 2),
        "median": round(float(np.median(array)), 1),
        "min": round(float(array.min()), 1),
        "max": round(float(array.max()), 1),
        "stderr": round(float(stderr), 2),
        "ci95": round(float(1.96 * stderr), 2),
        "scores": [int(value) for value in array],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", type=Path)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=9000)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    seeds = [args.seed + index for index in range(args.episodes)]
    results = []

    rng = np.random.default_rng(args.seed)
    for name in CONTROLS:
        scores = [play_control(name, seed, rng)["score"] for seed in seeds]
        results.append(summarise(f"control:{name}", scores))
        print(
            f"  control:{name:<8} mean {results[-1]['mean']:8.2f} "
            f"+/-{results[-1]['ci95']:6.2f}  median {results[-1]['median']:7.1f}  "
            f"max {results[-1]['max']:7.1f}"
        )

    if args.model and not args.controls_only:
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(args.model), device=args.device)
        for mode, deterministic in (("deterministic", True), ("stochastic", False)):
            scores = [
                play_policy(model, seed, deterministic)["score"] for seed in seeds
            ]
            results.append(summarise(f"policy:{mode}", scores))
            print(
                f"  policy:{mode:<11} mean {results[-1]['mean']:8.2f} "
                f"+/-{results[-1]['ci95']:6.2f}  median {results[-1]['median']:7.1f}  "
                f"max {results[-1]['max']:7.1f}"
            )

        best_control = max(
            (row for row in results if row["label"].startswith("control")),
            key=lambda row: row["mean"],
        )
        best_policy = max(
            (row for row in results if row["label"].startswith("policy")),
            key=lambda row: row["mean"],
        )
        margin = best_policy["mean"] - best_control["mean"]
        combined = (best_policy["ci95"] ** 2 + best_control["ci95"] ** 2) ** 0.5
        verdict = "BEATS" if margin > combined else "does NOT clearly beat"
        print(
            f"\n  {best_policy['label']} {verdict} {best_control['label']}: "
            f"margin {margin:+.1f}, combined 95% interval +/-{combined:.1f}"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

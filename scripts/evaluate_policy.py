"""Evaluate a saved policy on held-out seeds and report delivered passengers.

Runs through the same vector pipeline training uses, so the policy receives the
stacked observation it was trained on rather than a bare single frame. Deliveries
are accrued from the reward stream during the episode: a vector environment
auto-resets on termination, so any end-of-episode snapshot describes the next
game rather than the one just played.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from rl.history import default_history  # noqa: E402
from rl.protocol import TaskSpec, resolve_render_profile  # noqa: E402
from rl.training import build_vector_env  # noqa: E402


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return parsed


def evaluate(
    model_path: Path,
    *,
    episodes: int,
    seed: int,
    render_profile: str,
    device: str,
    max_decisions: int,
    deterministic: bool,
):
    from sb3_contrib import RecurrentPPO

    spec = TaskSpec(render_profile=resolve_render_profile(render_profile))
    vec = build_vector_env(spec, n_envs=1, seed=seed, history=default_history())
    model = RecurrentPPO.load(str(model_path), device=device)

    results = []
    try:
        for episode in range(episodes):
            # Reseed per episode: a vector env reset without this replays the
            # same game, which silently turns N episodes into one measured N times.
            vec.seed(seed + episode)
            observation = vec.reset()
            state = None
            starts = np.ones((1,), dtype=bool)
            delivered = 0.0
            decisions = 0
            while decisions < max_decisions:
                action, state = model.predict(
                    observation,
                    state=state,
                    episode_start=starts,
                    deterministic=deterministic,
                )
                observation, rewards, dones, _ = vec.step(action)
                delivered += float(rewards[0])
                decisions += 1
                starts = np.array(dones, dtype=bool)
                if bool(dones[0]):
                    break
            results.append((int(delivered), decisions))
            print(
                f"  episode {episode + 1}/{episodes}: "
                f"{int(delivered)} deliveries in {decisions} decisions"
            )
    finally:
        vec.close()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--episodes", type=_positive_int, default=10)
    parser.add_argument("--seed", type=int, default=9000)
    parser.add_argument("--render-profile", default="fast")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-decisions", type=_positive_int, default=4000)
    parser.add_argument("--stochastic", action="store_true")
    args = parser.parse_args(argv)

    print(f"evaluating {args.model} on seed base {args.seed}")
    results = evaluate(
        args.model,
        episodes=args.episodes,
        seed=args.seed,
        render_profile=args.render_profile,
        device=args.device,
        max_decisions=args.max_decisions,
        deterministic=not args.stochastic,
    )
    deliveries = [row[0] for row in results]
    print(
        f"\ndeliveries: mean {np.mean(deliveries):.2f}  median {np.median(deliveries):.1f}  "
        f"min {min(deliveries)}  max {max(deliveries)}"
    )
    print("reference: random 0, scripted expert ~20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

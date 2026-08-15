"""Train a masked PPO agent on the semantic lane.

MaskablePPO rather than PPO because the masks are the point: without them a
random policy builds a line in 2 of 12 episodes, with them in 12 of 12. Feeding
the same masks to the learner keeps it from spending probability mass on actions
the game will refuse.

Evaluation uses held-out seeds disjoint from training and reports the full
per-episode distribution, because episode outcomes here are high-variance and a
mean over a handful of episodes mostly counts lucky seeds -- an error already
made once on the pixel lane and corrected.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from rl.semantic_env import SemanticMetroEnv  # noqa: E402


def make_env(seed: int):
    from sb3_contrib.common.wrappers import ActionMasker

    def mask_fn(env):
        return env.action_masks()

    def thunk():
        env = SemanticMetroEnv()
        env.reset(seed=seed)
        return ActionMasker(env, mask_fn)

    return thunk


def evaluate(
    model, episodes: int, base_seed: int, *, deterministic: bool
) -> list[float]:
    """Play held-out episodes.

    Both modes are reported because they disagree enormously here. WAIT is
    the most likely action at almost every individual step -- correctly, since
    most steps should wait -- so a greedy argmax waits forever and scores
    zero, while sampling from the same policy delivers. Reporting only the
    deterministic figure would have recorded a working policy as a failure.
    """

    scores = []
    for index in range(episodes):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=base_seed + index)
        total = 0.0
        while True:
            masks = env.action_masks()
            action, _ = model.predict(
                observation, action_masks=masks, deterministic=deterministic
            )
            observation, reward, terminated, truncated, _ = env.step(action)
            total += float(reward)
            if terminated or truncated:
                break
        scores.append(total)
        env.close()
    return scores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-timesteps", type=int, default=300_000)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-episodes", type=int, default=20)
    parser.add_argument("--eval-seed", type=int, default=9000)
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--arch",
        choices=("mlp", "pointer"),
        default="mlp",
        help="pointer scores each action from the entities it names",
    )
    parser.add_argument("--output", default="output/semantic/model")
    args = parser.parse_args(argv)

    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

    vec = VecMonitor(
        DummyVecEnv([make_env(args.seed + rank) for rank in range(args.n_envs)])
    )
    if args.arch == "pointer":
        from rl.semantic_nets import PointerExtractor, build_pointer_policy_class

        policy = build_pointer_policy_class()
        policy_kwargs = dict(features_extractor_class=PointerExtractor)
    else:
        policy = "MlpPolicy"
        policy_kwargs = {}

    model = MaskablePPO(
        policy,
        vec,
        policy_kwargs=policy_kwargs,
        seed=args.seed,
        device=args.device,
        n_steps=256,
        batch_size=256,
        learning_rate=3e-4,
        ent_coef=0.01,
        verbose=1,
    )
    model.learn(total_timesteps=args.total_timesteps)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    model.save(args.output)

    for label, deterministic in (("deterministic", True), ("stochastic", False)):
        scores = evaluate(
            model, args.eval_episodes, args.eval_seed, deterministic=deterministic
        )
        print(
            f"{label} on {args.eval_episodes} held-out episodes "
            f"(seed base {args.eval_seed}):"
        )
        print(f"  per-episode: {[int(s) for s in scores]}")
        print(
            f"  deliveries: mean {np.mean(scores):.2f}  median {np.median(scores):.1f}  "
            f"max {max(scores):.0f}"
        )
    print(
        "reference: random legal play scores 0 on this action space -- there "
        "are real decisions to get wrong, so any positive score is learning"
    )
    vec.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

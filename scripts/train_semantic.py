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
from pathlib import Path

import numpy as np

NL_MARKER = chr(10)

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


class KeepBest:
    """Evaluate periodically and save whichever policy actually scored best.

    A run is not monotonic. The previous one peaked at 97.5 deliveries near
    500k steps and fell to 35.5 by 856k, and because the trainer only saved
    at the end, the best policy it ever had was thrown away. Keeping the
    final weights assumes the last update was the best one, which the
    measured curve says is false.
    """

    def __init__(self, output, every, episodes, seed):
        from stable_baselines3.common.callbacks import BaseCallback

        self.output = output
        self.every = every
        self.episodes = episodes
        self.seed = seed
        self.best = float("-inf")
        self.history = []
        self.last_eval = 0
        self._base = BaseCallback

    def build(self):
        keeper = self

        class _Callback(keeper._base):
            def _on_step(self) -> bool:
                # Elapsed-since-last, not modulo. `num_timesteps` advances by
                # n_envs per call, so it only ever takes multiples of n_envs --
                # and `num_timesteps % every` can therefore never be zero unless
                # n_envs happens to divide `every`. With --n-envs 6 and
                # --eval-every 1000000 the counter steps 6, 12, 18 ... and skips
                # every multiple of a million, so a run of any length would
                # produce no evaluation, no checkpoint and no best-model save,
                # silently.
                if self.num_timesteps - keeper.last_eval < keeper.every:
                    return True
                keeper.last_eval = self.num_timesteps
                scores = evaluate(
                    self.model,
                    keeper.episodes,
                    keeper.seed,
                    deterministic=False,
                )
                mean = float(np.mean(scores))
                keeper.history.append((self.num_timesteps, mean))
                marker = ""
                if mean > keeper.best:
                    keeper.best = mean
                    self.model.save(f"{keeper.output}-best")
                    marker = "  <- new best, saved"
                self.model.save(f"{keeper.output}-latest")
                print(
                    f"[eval] {self.num_timesteps:,} steps: "
                    f"{mean:.1f} deliveries over {keeper.episodes} "
                    f"held-out episodes{marker}",
                    flush=True,
                )
                return True

        return _Callback()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-timesteps", type=int, default=300_000)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-episodes", type=int, default=20)
    parser.add_argument("--eval-seed", type=int, default=9000)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--eval-every", type=int, default=50_000)
    parser.add_argument("--resume", type=Path, help="warm-start from a saved policy")
    parser.add_argument("--ent-coef", type=float, default=0.01)
    parser.add_argument("--anchor-coef", type=float, default=0.0)
    parser.add_argument("--checkpoint-episodes", type=int, default=5)
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

    if args.resume:
        # Start from a policy that already plays. From-scratch training on this
        # lane has failed in every configuration tried, and the cloned heuristic
        # starts at ~197 against random-never-removes' 181 and the script's 277.
        if args.anchor_coef > 0:
            # Hold the reference throughout, not just at initialisation.
            # AlphaStar measures init alone at +84 Elo and the continual KL
            # penalty at +380 on top; here an unanchored warm start decayed
            # from 146.5 deliveries at 50k to 46.4 by 100k.
            from rl.anchored_ppo import build_anchored_ppo_class

            reference = MaskablePPO.load(str(args.resume), device=args.device)
            model = build_anchored_ppo_class().load(
                str(args.resume), env=vec, device=args.device
            )
            model.set_anchor(reference, args.anchor_coef)
            print(f"anchored to {args.resume} at coef {args.anchor_coef}", flush=True)
        else:
            model = MaskablePPO.load(str(args.resume), env=vec, device=args.device)
        model.learning_rate = args.learning_rate
        model.ent_coef = args.ent_coef
        print(f"resumed from {args.resume}", flush=True)
    else:
        model = MaskablePPO(
            policy,
            vec,
            policy_kwargs=policy_kwargs,
            seed=args.seed,
            device=args.device,
            n_steps=256,
            batch_size=256,
            # Decayed, not flat. At a constant 3e-4 the previous run's approx_kl
            # rose from 0.0037 to 0.0128 and its clip fraction from 0.034 to
            # 0.082 while the score halved: updates got larger as the policy got
            # worse. A step size that suits a crude policy is too hot once an
            # episode runs thousands of decisions and one bad update costs a
            # whole network.
            learning_rate=lambda progress: args.learning_rate * progress,
            ent_coef=args.ent_coef,
            verbose=1,
        )
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    # `--eval-episodes`, NOT `--checkpoint-episodes`. This passed the latter for
    # the whole of this project's history, so every in-training evaluation ran on
    # 5 episodes whatever the flag said -- against a score distribution spanning
    # 110 to 800, an MDE near +/-190. Every "new best, saved" was therefore a
    # five-episode lottery, and the checkpoints selected that way are what later
    # comparisons were run against.
    keeper = KeepBest(args.output, args.eval_every, args.eval_episodes, args.eval_seed)
    model.learn(total_timesteps=args.total_timesteps, callback=keeper.build())
    model.save(args.output)

    if keeper.history:
        print(NL_MARKER + "evaluation history:")
        for step, mean in keeper.history:
            print(f"  {step:>10,}  {mean:8.1f}")
        print(f"best {keeper.best:.1f}, kept at {args.output}-best")
        from sb3_contrib import MaskablePPO as _Maskable

        model = _Maskable.load(f"{args.output}-best", device=args.device)

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
    # Measured on the same held-out seeds. A score against random alone is
    # meaningless here: random scores 0 only because it spams REMOVE_LINE and
    # destroys its own network. Excluding that one action, random scores 178.
    print("reference, same held-out seeds:")
    print("  scripted heuristic, no learning ... 277.2")
    print("  random legal play, no REMOVE ..... 178.2")
    print("  random legal play, with REMOVE ...   0.0  <- an artifact, not difficulty")
    print("  a policy must beat the scripted heuristic to be worth anything")
    vec.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Train a policy that starts as the heuristic and is paid to deviate.

Every learned policy on this task has been trained to agree with a teacher, and
agreement has never once predicted score: 0% agreement scores 183, 83% scores
189, and only the teacher's own play reaches 263. A policy that matches the
teacher on 83% of about fifteen real decisions lands on a different board within
a few moves, and from there the teacher's remaining answers are replies to
questions it is no longer being asked.

So this trains the residual instead. The environment offers one extra action,
DEFER, meaning "play whatever the heuristic would play here". A policy that
always defers *is* the heuristic -- proved action-by-action in
`test_event_gate.py`, and reproduced as the `defer` arm of `paired_eval.py`,
which returns the heuristic's score to the delivery. Training therefore starts
at the bar rather than 80 deliveries below it, compounding divergence is
something the policy chooses to incur rather than something it suffers at
initialisation, and the objective is deliveries rather than imitation.

Two things make it affordable. The event gate collapses an episode from ~7,600
decisions to ~51 policy queries, so credit no longer travels back across
thousands of no-ops. And the action head is initialised DEFER-dominant, so the
run opens near 263 instead of exploring its way there.

**The decisive metric is printed during the run**, not after it: a paired
difference against the heuristic on a fixed evaluation seed set, at a stated n,
with its 95% interval. The heuristic's per-seed scores are computed once and
cached, so each readout costs only the policy's own episodes.

**Kill criterion, stated before starting.** Stop if the paired gap is below
-25 deliveries at two consecutive readouts (the anchor is being destroyed), or
if the deviation rate is under 0.5% at three consecutive readouts (the policy
has collapsed onto DEFER and is learning nothing). Neither is a result worth
more hours.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

Z95 = 1.959963985


def _env_factory(spec: dict, reward_scale: float):
    def build():
        import gymnasium as gym

        from rl.event_gate import EventGatedSemanticEnv

        env = EventGatedSemanticEnv(
            defer=True,
            proposal_features=spec["proposal"],
            wait_backstop=spec["backstop"],
            deviation_scope=spec["scope"],
        )
        if reward_scale != 1.0:

            class Scaled(gym.Wrapper):
                """Training-time reward scale only.

                PPO's value head has to fit returns near 250 with per-step
                rewards that swing between 0 and 40, because one WAIT can
                fast-forward 400 decisions. Scaling is a training aid and lives
                in a wrapper; evaluation counts raw deliveries.
                """

                def step(self, action):
                    obs, reward, terminated, truncated, info = self.env.step(action)
                    return obs, reward / reward_scale, terminated, truncated, info

            env = Scaled(env)
        return env

    return build


def _score_one(job):
    """One evaluation episode, run in a worker process."""
    kind, payload, seed, spec = job
    from rl.event_gate import EventGatedSemanticEnv
    from rl.heuristic import choose

    env = EventGatedSemanticEnv(
        defer=True,
        proposal_features=spec["proposal"],
        wait_backstop=spec["backstop"],
        deviation_scope=spec["scope"],
    )
    obs, _ = env.reset(seed=seed)
    total, deviations, queries = 0.0, 0, 0
    model = None
    if kind == "model":
        global _EVAL_MODEL
        cached = globals().get("_EVAL_MODEL")
        if cached is None or cached[0] != payload:
            from sb3_contrib import MaskablePPO

            globals()["_EVAL_MODEL"] = (
                payload,
                MaskablePPO.load(payload, device="cpu"),
            )
        model = globals()["_EVAL_MODEL"][1]
    try:
        while True:
            mask = env.action_masks()
            if kind == "heuristic":
                action = choose(env.inner)
            else:
                action, _ = model.predict(obs, action_masks=mask, deterministic=False)
                action = int(np.asarray(action).ravel()[0])
                if action != env.DEFER:
                    deviations += 1
            obs, reward, terminated, truncated, _ = env.step(action)
            total += float(reward)
            queries += 1
            if terminated or truncated:
                break
    finally:
        env.close()
    return {"seed": seed, "score": total, "deviations": deviations, "queries": queries}


def heuristic_reference(seeds, spec, workers, cache_path) -> dict[int, float]:
    """Per-seed heuristic scores, computed once and reused every readout."""
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as handle:
            cached = json.load(handle)
        if cached.get("seeds") == list(seeds) and cached.get("spec") == spec:
            return {int(k): v for k, v in cached["scores"].items()}
    jobs = [("heuristic", None, seed, spec) for seed in seeds]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_score_one, jobs, chunksize=1))
    scores = {row["seed"]: row["score"] for row in rows}
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump(
            {"seeds": list(seeds), "spec": spec, "scores": scores}, handle, indent=2
        )
    return scores


def paired_readout(path, seeds, spec, workers, reference) -> dict:
    """The decisive metric: paired gap against the heuristic, with its interval."""
    jobs = [("model", path, seed, spec) for seed in seeds]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_score_one, jobs, chunksize=1))
    scores = np.array([row["score"] for row in rows], dtype=float)
    base = np.array([reference[row["seed"]] for row in rows], dtype=float)
    diff = scores - base
    n = len(diff)
    half = Z95 * float(np.std(diff, ddof=1)) / math.sqrt(n) if n > 1 else float("inf")
    return {
        "mean": float(scores.mean()),
        "heuristic": float(base.mean()),
        "gap": float(diff.mean()),
        "ci95": half,
        "won": int(np.sum(diff > 0)),
        "lost": int(np.sum(diff < 0)),
        "n": n,
        "deviation_rate": float(
            np.sum([r["deviations"] for r in rows])
            / max(1, sum(r["queries"] for r in rows))
        ),
        "queries": float(np.mean([r["queries"] for r in rows])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-timesteps", type=int, default=200_000)
    parser.add_argument("--envs", type=int, default=16)
    parser.add_argument("--n-steps", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.997)
    parser.add_argument("--ent-coef", type=float, default=0.003)
    parser.add_argument("--reward-scale", type=float, default=10.0)
    parser.add_argument(
        "--defer-bias",
        type=float,
        default=5.0,
        help="logit added to DEFER at init; 5.0 is ~85%% DEFER over 30 legal actions",
    )
    parser.add_argument("--proposal-features", action="store_true")
    parser.add_argument("--backstop", type=int, default=200)
    parser.add_argument("--deviation-scope", choices=("all", "kind"), default="all")
    parser.add_argument("--eval-every", type=int, default=25_000)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--eval-seed-base", type=int, default=70_000)
    parser.add_argument("--eval-workers", type=int, default=15)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    from rl.dependencies import require_rl_dependencies

    require_rl_dependencies()
    import torch as th
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv

    spec = {
        "proposal": bool(args.proposal_features),
        "backstop": int(args.backstop),
        "scope": args.deviation_scope,
    }
    eval_seeds = [args.eval_seed_base + i for i in range(args.eval_episodes)]
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    print(
        f"residual training: {args.total_timesteps} policy steps, {args.envs} envs, "
        f"proposal_features={spec['proposal']}, scope={spec['scope']}, "
        f"defer_bias={args.defer_bias}",
        flush=True,
    )
    print(
        "KILL CRITERION: gap < -25 at two consecutive readouts, or deviation "
        "rate < 0.5% at three consecutive readouts.",
        flush=True,
    )
    started = time.time()
    reference = heuristic_reference(
        eval_seeds,
        spec,
        args.eval_workers,
        os.path.join(os.path.dirname(args.output) or ".", "heuristic-reference.json"),
    )
    print(
        f"heuristic reference on {len(eval_seeds)} eval seeds: "
        f"{np.mean(list(reference.values())):.2f} "
        f"({time.time() - started:.0f}s)",
        flush=True,
    )

    envs = SubprocVecEnv(
        [_env_factory(spec, args.reward_scale) for _ in range(args.envs)]
    )
    model = MaskablePPO(
        "MlpPolicy",
        envs,
        learning_rate=args.learning_rate,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        gamma=args.gamma,
        ent_coef=args.ent_coef,
        seed=args.seed,
        verbose=0,
        device="cpu",
    )
    # Start as the heuristic. Shrinking the action head's weights makes the
    # opening policy nearly state-independent, and the bias then puts most of
    # the mass on DEFER; without this the run spends its first tens of
    # thousands of steps rediscovering that random deviation is bad.
    with th.no_grad():
        model.policy.action_net.weight.mul_(0.01)
        model.policy.action_net.bias.zero_()
        model.policy.action_net.bias[-1] = args.defer_bias

    class Readout(BaseCallback):
        def __init__(self):
            super().__init__()
            self.best = -float("inf")
            self.bad = 0
            self.flat = 0
            self.next_at = args.eval_every

        def _on_step(self) -> bool:
            if self.num_timesteps < self.next_at:
                return True
            self.next_at += args.eval_every
            latest = f"{args.output}-latest"
            self.model.save(latest)
            row = paired_readout(latest, eval_seeds, spec, args.eval_workers, reference)
            elapsed = time.time() - started
            print(
                f"[eval] step {self.num_timesteps:>8}  "
                f"policy {row['mean']:7.2f}  heuristic {row['heuristic']:7.2f}  "
                f"gap {row['gap']:+8.2f} +/-{row['ci95']:.2f}  "
                f"W/L {row['won']}/{row['lost']}  "
                f"deviate {row['deviation_rate'] * 100:5.2f}%  "
                f"({elapsed / 60:.1f} min)",
                flush=True,
            )
            if row["gap"] > self.best:
                self.best = row["gap"]
                self.model.save(f"{args.output}-best")
                print(f"       new best gap {row['gap']:+.2f}, saved", flush=True)
            self.bad = self.bad + 1 if row["gap"] < -25 else 0
            self.flat = self.flat + 1 if row["deviation_rate"] < 0.005 else 0
            if self.bad >= 2:
                print(
                    "KILL: gap below -25 twice; the anchor is being destroyed.",
                    flush=True,
                )
                return False
            if self.flat >= 3:
                print(
                    "KILL: deviation rate below 0.5% three times; collapsed onto "
                    "DEFER and learning nothing.",
                    flush=True,
                )
                return False
            return True

    model.learn(total_timesteps=args.total_timesteps, callback=Readout())
    model.save(args.output)
    envs.close()
    print(
        f"saved {args.output} after {(time.time() - started) / 60:.1f} min", flush=True
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

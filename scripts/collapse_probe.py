"""The fixed reproduction for the training-collapse search.

One command, one verdict, unchanged for the rest of the search, so competing
approaches are scored against the same thing rather than against each other's
reports. See `docs/threads/current/training-collapse/DIAGNOSIS.md` for the
done-condition and the disqualifier list.

Scoring deliberately uses `ep_rew_mean` over training episodes rather than the
held-out evaluation. A fixed policy re-evaluated on the same five held-out seeds
spanned 30.8 to 58.6, so that signal cannot resolve the effect being searched
for; `ep_rew_mean` averages over far more episodes.

Every knob a candidate might want to change is exposed here, so a branch is a
flag rather than an edited trainer -- otherwise two branches silently differ in
more than the thing under test.
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

from rl.semantic_env import SemanticMetroEnv  # noqa: E402

# A run that never learns cannot collapse, so a bare retention ratio would score
# a broken candidate as a success. Both thresholds have to be met.
MIN_PEAK = 40.0
PASS_RETENTION = 0.75
COLLAPSE_RETENTION = 0.25


class Recorder:
    """Capture ep_rew_mean and entropy at every rollout, not just at the end."""

    def __init__(self):
        from stable_baselines3.common.callbacks import BaseCallback

        self.rows: list[dict] = []
        self._base = BaseCallback

    def build(self):
        recorder = self

        class _Callback(recorder._base):
            def _on_rollout_end(self) -> None:
                buffer = getattr(self.model, "ep_info_buffer", None)
                if not buffer:
                    return
                rewards = [entry["r"] for entry in buffer]
                lengths = [entry["l"] for entry in buffer]
                recorder.rows.append(
                    {
                        "steps": int(self.num_timesteps),
                        "ep_rew_mean": float(np.mean(rewards)),
                        "ep_len_mean": float(np.mean(lengths)),
                    }
                )

            def _on_step(self) -> bool:
                return True

        return _Callback()


def run(args) -> dict:
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor, VecNormalize

    def make(rank: int):
        def thunk():
            env = SemanticMetroEnv(
                remove_min_age=args.remove_min_age,
                remove_penalty=args.remove_penalty,
            )
            env.reset(seed=args.seed + rank)
            return ActionMasker(env, lambda e: e.action_masks())

        return thunk

    vec = VecMonitor(DummyVecEnv([make(rank) for rank in range(args.n_envs)]))
    if args.normalize_returns:
        # Branch A: bound the value targets. Observations are already scaled by
        # the environment, so only returns are touched.
        vec = VecNormalize(vec, norm_obs=False, norm_reward=True, gamma=args.gamma)

    rate = args.learning_rate
    schedule = (lambda progress: rate * progress) if args.decay_lr else rate
    model = MaskablePPO(
        "MlpPolicy",
        vec,
        seed=args.seed,
        device=args.device,
        n_steps=args.n_steps,
        # SB3 defaults to 10 epochs; this repo's own reviewed PPO_DEFAULTS uses 4.
        # arXiv 2405.00662 measures that more epochs accelerates the rise in
        # pre-activation norm and the fall in feature rank that precede collapse,
        # and swept only 4/6/8 -- the semantic lane has been running above all of it.
        n_epochs=args.n_epochs,
        batch_size=args.batch_size,
        learning_rate=schedule,
        ent_coef=args.ent_coef,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        clip_range=args.clip_range,
        max_grad_norm=args.max_grad_norm,
        target_kl=args.target_kl,
        verbose=0,
    )
    recorder = Recorder()
    model.learn(total_timesteps=args.steps, callback=recorder.build())
    vec.close()

    rows = recorder.rows
    if not rows:
        return {"error": "no rollouts recorded"}
    curve = [row["ep_rew_mean"] for row in rows]
    peak = max(curve)
    peak_at = rows[int(np.argmax(curve))]["steps"]
    final = float(np.mean(curve[-10:]))
    retention = final / peak if peak > 0 else 0.0
    return {
        "label": args.label,
        "steps": args.steps,
        "seed": args.seed,
        "peak": round(peak, 2),
        "peak_at": peak_at,
        "final": round(final, 2),
        "retention": round(retention, 3),
        "collapsed": bool(retention < COLLAPSE_RETENTION),
        "passes": bool(peak >= MIN_PEAK and retention >= PASS_RETENTION),
        "curve": [(row["steps"], round(row["ep_rew_mean"], 1)) for row in rows[::4]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=400_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path)
    # Knobs a branch may vary. Defaults reproduce the collapsing configuration.
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--decay-lr", action="store_true")
    parser.add_argument("--ent-coef", type=float, default=0.01)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--gae-lambda", type=float, default=0.95)
    parser.add_argument("--clip-range", type=float, default=0.2)
    parser.add_argument("--max-grad-norm", type=float, default=0.5)
    parser.add_argument("--target-kl", type=float, default=None)
    parser.add_argument("--n-steps", type=int, default=256)
    parser.add_argument("--n-epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--normalize-returns", action="store_true")
    parser.add_argument("--remove-min-age", type=int, default=0)
    parser.add_argument("--remove-penalty", type=float, default=0.0)
    args = parser.parse_args(argv)

    result = run(args)
    print(json.dumps(result, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

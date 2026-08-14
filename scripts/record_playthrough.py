"""Record a playthrough as a watchable animation.

The frames written here are the exact observation tensor the policy receives, so
the recording shows what the agent sees rather than a privileged view of the
game. Animated GIF is deliberate: no video encoder is installed, and Mini
Metro's flat palette compresses well enough that a full episode stays small.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from PIL import Image  # noqa: E402

from rl.player_env import PlayerPixelEnv  # noqa: E402
from rl.protocol import FIDELITY_RENDER_PROFILE, resolve_render_profile  # noqa: E402

POLICIES = ("random", "noop", "model")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=POLICIES, default="random")
    parser.add_argument(
        "--model", type=Path, help="model zip, required for --policy model"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-decisions", type=_positive_int, default=3000)
    parser.add_argument("--render-profile", default=FIDELITY_RENDER_PROFILE.name)
    parser.add_argument(
        "--stride", type=_positive_int, default=3, help="record 1 of N decisions"
    )
    parser.add_argument("--scale", type=_positive_int, default=2)
    parser.add_argument("--fps", type=_positive_int, default=12)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)
    if args.policy == "model" and args.model is None:
        parser.error("--policy model requires --model")
    return args


class _Actor:
    """Chooses actions and, for recurrent models, carries per-episode state."""

    def __init__(
        self, kind: str, env: PlayerPixelEnv, model_path: Path | None, device: str
    ):
        self.kind = kind
        self.env = env
        self.model = None
        self.state = None
        if kind == "model":
            from sb3_contrib import RecurrentPPO

            self.model = RecurrentPPO.load(str(model_path), device=device)

    def reset(self) -> None:
        self.state = None

    def act(self, observation: np.ndarray) -> np.ndarray:
        if self.kind == "noop":
            return np.array([0, 0, 0], dtype=np.int64)
        if self.kind == "random":
            return self.env.action_space.sample()
        # A recurrent policy needs both its carried state and the episode-start
        # mask; omitting either silently degrades it to a stateless policy.
        action, self.state = self.model.predict(
            observation[None],
            state=self.state,
            episode_start=np.array([self.state is None]),
            deterministic=True,
        )
        return np.asarray(action[0], dtype=np.int64)


def record(args: argparse.Namespace) -> dict[str, object]:
    profile = resolve_render_profile(args.render_profile)
    env = PlayerPixelEnv(render_profile=profile)
    env.action_space.seed(args.seed)
    observation, _ = env.reset(seed=args.seed)

    frames: list[Image.Image] = []
    seed_used = args.seed
    deliveries = 0.0
    decisions = 0
    ended = "max-decisions"

    actor = _Actor(args.policy, env, args.model, args.device)
    actor.reset()

    def capture(frame: np.ndarray) -> None:
        image = Image.fromarray(np.transpose(frame, (1, 2, 0)))
        if args.scale != 1:
            image = image.resize(
                (image.width * args.scale, image.height * args.scale), Image.NEAREST
            )
        frames.append(image.convert("P", palette=Image.ADAPTIVE, colors=128))

    capture(observation)
    while decisions < args.max_decisions:
        observation, reward, terminated, truncated, _ = env.step(actor.act(observation))
        decisions += 1
        deliveries += float(reward)
        if decisions % args.stride == 0:
            capture(observation)
        if terminated or truncated:
            ended = "game-over" if terminated else "truncated"
            capture(observation)
            break
    env.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=max(1, round(1000 / args.fps)),
        loop=0,
        optimize=True,
    )
    # GIF collapses byte-identical consecutive frames, so what lands on disk can
    # legitimately be fewer than what was captured. Report both rather than one.
    with Image.open(args.output) as animation:
        written = int(getattr(animation, "n_frames", 1))

    return {
        "policy": args.policy,
        "seed": seed_used,
        "deliveries": int(deliveries),
        "decisions": decisions,
        "ended": ended,
        "frames_captured": len(frames),
        "frames_written": written,
        "output": str(args.output),
        "bytes": args.output.stat().st_size,
    }


def main(argv: list[str] | None = None) -> int:
    summary = record(parse_args(argv))
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Watch the semantic agent play, rendered as the real game.

The semantic environment drives a Mediator directly and never renders, because
its observation is structured rather than visual. That makes its play invisible,
which is the wrong trade for the one thing a scalar cannot tell you: whether the
network it builds looks like a metro system or like an accident that happens to
score.

So this attaches a renderer to the same live game the policy is acting on and
captures frames. Nothing is fed back to the agent; the drawing is purely for a
human.

Episodes here run to a real game over and can last thousands of decisions, so
frames are sampled on a stride and the animation is capped -- a full-rate
recording would be tens of thousands of frames.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

from config import screen_height, screen_width  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return parsed


def record(args: argparse.Namespace) -> dict[str, object]:
    from sb3_contrib import MaskablePPO

    pygame.init()
    surface = pygame.Surface((screen_width, screen_height))
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=args.seed)
    model = (
        None if args.random else MaskablePPO.load(str(args.model), device=args.device)
    )
    rng = np.random.default_rng(args.seed)

    frames: list[Image.Image] = []
    delivered = 0.0
    decisions = 0
    kinds: dict[int, int] = {}

    while decisions < args.max_decisions:
        mask = env.action_masks()
        if model is None:
            action = int(rng.choice(np.flatnonzero(mask)))
        else:
            predicted, _ = model.predict(
                observation, action_masks=mask, deterministic=False
            )
            action = int(np.asarray(predicted).ravel()[0])
        kinds[ACTION_TABLE[action][0]] = kinds.get(ACTION_TABLE[action][0], 0) + 1

        observation, reward, terminated, truncated, _ = env.step(action)
        delivered += float(reward)
        decisions += 1

        if decisions % args.stride == 0 and len(frames) < args.max_frames:
            surface.fill((255, 255, 255))
            env._mediator.render(surface)
            raw = pygame.surfarray.array3d(surface).transpose(1, 0, 2)
            image = Image.fromarray(raw).resize(
                (screen_width // args.shrink, screen_height // args.shrink),
                Image.BILINEAR,
            )
            frames.append(image.convert("P", palette=Image.ADAPTIVE, colors=96))
        if terminated or truncated:
            break

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=max(1, round(1000 / args.fps)),
        loop=0,
        optimize=True,
    )
    with Image.open(args.output) as animation:
        written = int(getattr(animation, "n_frames", 1))

    mediator = env._mediator
    summary = {
        "policy": "random" if model is None else str(args.model),
        "seed": args.seed,
        "deliveries": int(delivered),
        "decisions": decisions,
        "ended": "game-over" if terminated else "step-limit",
        "lines": len(mediator.paths),
        "longest_line": max((len(p.stations) for p in mediator.paths), default=0),
        "stations": len(mediator.stations),
        "frames_written": written,
        "output": str(args.output),
        "actions": {ActionKind(k).name: v for k, v in sorted(kinds.items())},
    }
    env.close()
    pygame.quit()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path("output/semantic/model-v3"))
    parser.add_argument(
        "--random", action="store_true", help="record random play instead"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=9000)
    parser.add_argument("--max-decisions", type=_positive_int, default=40_000)
    parser.add_argument("--stride", type=_positive_int, default=25)
    parser.add_argument("--max-frames", type=_positive_int, default=400)
    parser.add_argument("--shrink", type=_positive_int, default=3)
    parser.add_argument("--fps", type=_positive_int, default=14)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)

    for key, value in record(args).items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

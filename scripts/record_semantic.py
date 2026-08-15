"""Record a semantic-lane playthrough as a watchable animation.

The semantic environment is headless -- it hands the policy a 574-float vector,
never pixels -- so unlike the pixel lane there is no observation tensor to write
out. What is worth watching here is the *game*, because the interesting claim is
about play: search scores 803 on seed 9000 where the heuristic scores 275, and
the visible difference is that it commits to an 11-station line instead of
spreading across short ones.

So this renders the live game the same way the human client does, driven by
whichever player is chosen. Frames are sampled rather than captured every
decision -- an episode runs 8,000 or more decisions and almost all of them are
WAIT, so a frame per decision would be a mostly-static hour.

Players:
  heuristic  the scripted rule, ~262 deliveries
  search     rollout lookahead, ~408 -- slow, since each decision point costs
             several full-episode simulations
  model      a trained policy from --model
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
from search_policy import (  # noqa: E402
    STRUCTURAL,
    _restore,
    _rollout,
    _signature,
    shortlist_for,
)

from config import screen_height, screen_width  # noqa: E402
from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, SemanticMetroEnv  # noqa: E402
from save_game import serialize_game  # noqa: E402

PLAYERS = ("heuristic", "search", "model")


def _frame(mediator, surface) -> Image.Image:
    """Render the live game and hand back an RGB image."""
    surface.fill((255, 255, 255))
    mediator.render(surface)
    raw = pygame.image.tobytes(surface, "RGB")
    return Image.frombytes("RGB", surface.get_size(), raw)


def play(
    player: str,
    seed: int,
    every: int,
    candidates: int,
    cap: int,
    model=None,
) -> tuple[list[Image.Image], dict]:
    pygame.init()
    surface = pygame.Surface((screen_width, screen_height))
    env = SemanticMetroEnv()
    observation, _ = env.reset(seed=seed)
    rng = np.random.default_rng(seed)

    frames: list[Image.Image] = []
    delivered = 0.0
    decisions = 0
    last_signature: frozenset | None = None

    while True:
        if decisions % every == 0:
            frames.append(_frame(env._mediator, surface))

        if player == "heuristic":
            action = choose(env)
        elif player == "model":
            predicted, _ = model.predict(
                observation, action_masks=env.action_masks(), deterministic=True
            )
            action = int(np.asarray(predicted).ravel()[0])
        else:
            mask = env.action_masks()
            structural = [
                i for i in np.flatnonzero(mask) if ACTION_TABLE[i][0] in STRUCTURAL
            ]
            preferred = choose(env)
            signature = _signature(mask)
            if structural and (preferred != 0 or signature != last_signature):
                last_signature = signature
                shortlist = shortlist_for(rng, structural, preferred, candidates)
                document = serialize_game(env._mediator)
                at = env._decision
                scored = [
                    (_rollout(env, document, at, entry, cap), entry)
                    for entry in shortlist
                ]
                _restore(env, document, at)
                action = max(scored)[1]
            else:
                action = preferred

        observation, reward, terminated, truncated, _ = env.step(action)
        delivered += float(reward)
        decisions += 1
        if terminated or truncated:
            break

    frames.append(_frame(env._mediator, surface))
    mediator = env._mediator
    summary = {
        "deliveries": int(delivered),
        "decisions": decisions,
        "frames": len(frames),
        "lines": len(mediator.paths),
        "longest_line": max((len(p.stations) for p in mediator.paths), default=0),
        "stations": len(mediator.stations),
    }
    env.close()
    pygame.quit()
    return frames, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player", choices=PLAYERS, default="heuristic")
    parser.add_argument("--seed", type=int, default=9000)
    parser.add_argument("--every", type=int, default=40)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--cap", type=int, default=15_000)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument(
        "--output", type=Path, default=Path("output/semantic/playthrough.gif")
    )
    args = parser.parse_args(argv)

    model = None
    if args.player == "model":
        if args.model is None:
            raise SystemExit(
                "--player model needs --model pointing at a saved policy, e.g. "
                "output/semantic/distilled"
            )
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(args.model), device="cpu")

    print(f"recording {args.player} on seed {args.seed}, a frame every {args.every}")
    frames, summary = play(
        args.player, args.seed, args.every, args.candidates, args.cap, model
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=max(1, 1000 // args.fps),
        loop=0,
        optimize=True,
    )
    size = args.output.stat().st_size
    print(
        f"  {summary['deliveries']} deliveries over {summary['decisions']} decisions, "
        f"{summary['lines']} lines, longest {summary['longest_line']} of "
        f"{summary['stations']} stations"
    )
    # Frames captured and frames written differ: GIF collapses identical
    # consecutive frames, and this game is static between decisions.
    print(
        f"  {summary['frames']} frames captured -> {args.output} ({size / 1e6:.1f} MB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

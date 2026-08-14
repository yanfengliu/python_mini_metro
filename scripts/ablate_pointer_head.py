"""Ablate the pointer head: flat coordinate regression against a spatial heatmap.

Behaviour cloning learns *when* to act but not *where*. At the step the scripted
expert draws, the cloned policy puts 95% on motion/down/up yet only 0.63% on the
expert's x coordinate, against a 0.52% uniform. The question this answers is
whether that is a data limit or an architectural one.

The current head predicts x as a flat 192-way categorical and y as a flat
108-way categorical from a single global feature vector, so pointing has no
spatial structure: the network must memorise absolute coordinates for every
layout it sees. The spatial head instead reads a 1x1 convolution as a heatmap
over the convolutional grid, resamples it to the action grid, and marginalises
to x and y. Positions then stay aligned with the pixels that produced them.

Both arms share the same encoder architecture, the same data and the same
optimiser, so the comparison isolates the head.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from gymnasium import spaces  # noqa: E402
from pretrain_bc import NOOP, base_env  # noqa: E402
from torch import nn  # noqa: E402

from rl.history import default_history  # noqa: E402
from rl.model import MiniMetroCNN  # noqa: E402
from rl.protocol import TaskSpec, resolve_render_profile  # noqa: E402
from rl.training import build_vector_env  # noqa: E402

POINTER_KINDS = (1, 2, 3)  # motion, down, up -- the kinds whose coordinates matter


class FlatHead(nn.Module):
    """Today's head: two independent categoricals off a global feature vector."""

    def __init__(self, encoder: MiniMetroCNN, width: int, height: int):
        super().__init__()
        self.encoder = encoder
        self.x = nn.Linear(encoder.features_dim, width)
        self.y = nn.Linear(encoder.features_dim, height)

    def forward(self, observations):
        features = self.encoder(observations)
        return self.x(features), self.y(features)


class SpatialHead(nn.Module):
    """A heatmap over the convolutional grid, marginalised to x and y."""

    def __init__(self, encoder: MiniMetroCNN, width: int, height: int):
        super().__init__()
        self.encoder = encoder
        self.convolutions = encoder.encoder[:-1]  # drop the trailing Flatten
        channels = None
        for layer in self.convolutions:
            if isinstance(layer, nn.Conv2d):
                channels = layer.out_channels
        self.point = nn.Conv2d(channels, 1, kernel_size=1)
        self.width = width
        self.height = height

    def forward(self, observations):
        grid = self.convolutions(observations)
        heat = self.point(grid)
        heat = F.interpolate(
            heat, size=(self.height, self.width), mode="bilinear", align_corners=False
        ).squeeze(1)
        # Marginalise the 2D heatmap into the two independent categoricals the
        # MultiDiscrete action space exposes.
        return torch.logsumexp(heat, dim=1), torch.logsumexp(heat, dim=2)


def collect(episodes: int, render_profile: str, seed: int):
    """Collect only station-targeting pointer samples.

    The expert's pointer actions mix two very different populations: drags that
    target stations, whose coordinates move with the layout, and clicks on fleet
    controls, which sit at fixed UI pixels every single game. A flat head
    memorises the fixed ones trivially, so including them measures recall of a
    constant rather than the visual grounding this ablation is about.
    """
    from rl.demonstrator import _assign_locomotive_actions, drag_route_actions
    from rl.privileged_oracle import capture_privileged_snapshot

    spec = TaskSpec(render_profile=resolve_render_profile(render_profile))
    vec = build_vector_env(spec, n_envs=1, seed=seed, history=default_history())
    observations, coordinates = [], []
    try:
        for index in range(episodes):
            observation = vec.reset()
            env = base_env(vec)
            finished = [False]

            def apply(actions, record):
                nonlocal observation
                for action in actions:
                    if finished[0]:
                        return
                    array = np.asarray(action, dtype=np.int64)
                    if record and int(array[0]) in POINTER_KINDS:
                        observations.append(observation[0].copy())
                        coordinates.append(array[1:])
                    observation, _, dones, _ = vec.step(array[None])
                    finished[0] = bool(dones[0])

            initial = len(capture_privileged_snapshot(env).station_positions)
            apply(drag_route_actions(env, tuple(range(initial))), True)
            for _ in range(3):
                try:
                    apply(_assign_locomotive_actions(env), False)
                except Exception:
                    break
            connected = set(range(initial))
            steps = 0
            while not finished[0] and steps < 4000:
                apply([NOOP] * 30, False)
                steps += 30
                if finished[0]:
                    break
                snapshot = capture_privileged_snapshot(env)
                fresh = [
                    i
                    for i in range(len(snapshot.station_positions))
                    if i not in connected
                ]
                if fresh and snapshot.line_credits > 0:
                    group = tuple(dict.fromkeys(sorted(connected)[:2] + fresh))[:8]
                    if len(group) >= 2:
                        try:
                            apply(drag_route_actions(env, group), True)
                            connected |= set(group)
                            apply(_assign_locomotive_actions(env), False)
                        except Exception:
                            pass
            print(
                f"  episode {index + 1}/{episodes}: "
                f"{len(observations)} station-pointer samples so far"
            )
    finally:
        vec.close()
    return np.stack(observations), np.stack(coordinates).astype(np.int64)


def run_arm(name, head, train, validate, *, epochs, batch_size, lr, device):
    head = head.to(device)
    optimizer = torch.optim.Adam(head.parameters(), lr=lr)
    train_obs, train_xy = train
    val_obs, val_xy = validate
    for epoch in range(epochs):
        head.train()
        order = np.random.permutation(len(train_obs))
        for start in range(0, len(order), batch_size):
            index = order[start : start + batch_size]
            obs = torch.as_tensor(train_obs[index]).to(device).float() / 255.0
            target = torch.as_tensor(train_xy[index]).to(device)
            x_logits, y_logits = head(obs)
            loss = F.cross_entropy(x_logits, target[:, 0]) + F.cross_entropy(
                y_logits, target[:, 1]
            )
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(head.parameters(), 0.5)
            optimizer.step()
        if (epoch + 1) % max(1, epochs // 4) == 0:
            print(f"    {name} epoch {epoch + 1}/{epochs}")

    head.eval()
    probabilities, distances = [], []
    with torch.no_grad():
        for start in range(0, len(val_obs), batch_size):
            obs = (
                torch.as_tensor(val_obs[start : start + batch_size]).to(device).float()
                / 255.0
            )
            target = torch.as_tensor(val_xy[start : start + batch_size]).to(device)
            x_logits, y_logits = head(obs)
            px = torch.softmax(x_logits, -1).gather(1, target[:, :1]).squeeze(1)
            py = torch.softmax(y_logits, -1).gather(1, target[:, 1:]).squeeze(1)
            probabilities.append((px * py).cpu().numpy())
            dx = (x_logits.argmax(-1) - target[:, 0]).abs().float()
            dy = (y_logits.argmax(-1) - target[:, 1]).abs().float()
            distances.append(torch.sqrt(dx**2 + dy**2).cpu().numpy())
    return np.concatenate(probabilities), np.concatenate(distances)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--render-profile", default="fast")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)

    profile = resolve_render_profile(args.render_profile)
    print(
        f"collecting pointer samples at {profile.name} {profile.width}x{profile.height}"
    )
    observations, coordinates = collect(args.episodes, args.render_profile, args.seed)
    split = int(len(observations) * 0.8)
    train = (observations[:split], coordinates[:split])
    validate = (observations[split:], coordinates[split:])
    print(
        f"\n{len(observations)} pointer samples -> {split} train / {len(observations) - split} val"
    )

    shape = observations.shape[1:]
    space = spaces.Box(low=0, high=255, shape=shape, dtype="uint8")
    uniform = 1.0 / (profile.width * profile.height)

    results = {}
    for name, factory in (
        ("flat (current)", FlatHead),
        ("spatial heatmap", SpatialHead),
    ):
        torch.manual_seed(args.seed)
        np.random.seed(args.seed)
        head = factory(MiniMetroCNN(space, 256), profile.width, profile.height)
        parameters = sum(p.numel() for p in head.parameters())
        print(f"\n{name}: {parameters:,} parameters")
        probabilities, distances = run_arm(
            name,
            head,
            train,
            validate,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.learning_rate,
            device=args.device,
        )
        results[name] = (probabilities, distances)

    print(f"\n{'head':<18}{'P(expert x,y)':>16}{'vs uniform':>12}{'argmax err px':>15}")
    for name, (probabilities, distances) in results.items():
        print(
            f"{name:<18}{probabilities.mean():>16.5%}"
            f"{probabilities.mean() / uniform:>11.1f}x{distances.mean():>15.1f}"
        )
    print(f"{'uniform baseline':<18}{uniform:>16.5%}{1.0:>11.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

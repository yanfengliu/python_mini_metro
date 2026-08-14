"""Clone the expert with a conditional spatial pointer head, then play with it.

The ablation in ``ablate_pointer_head.py`` showed the flat coordinate head sits
at 1.9x uniform on station targets while a spatial heatmap reaches 9.5x. This
builds a complete policy around that head and asks the only question that
matters: does it actually deliver passengers?

The head is *conditional* in the sense the parameterized-action literature uses:
the action kind is predicted for every step, but the pointer loss is applied
only to the three kinds whose coordinates are read (motion, pointer-down,
pointer-up). The other five ignore coordinates entirely, so training them to
predict a location teaches noise.

This deliberately sits outside Stable-Baselines3. The point is to measure the
head against real gameplay before paying for a custom recurrent policy, and a
standalone module keeps a negative result cheap.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from gymnasium import spaces  # noqa: E402
from pretrain_bc import NOOP, base_env  # noqa: E402
from torch import nn  # noqa: E402

from rl.demonstrator import _assign_locomotive_actions, drag_route_actions  # noqa: E402
from rl.history import default_history  # noqa: E402
from rl.model import MiniMetroCNN  # noqa: E402
from rl.privileged_oracle import capture_privileged_snapshot  # noqa: E402
from rl.protocol import TaskSpec, resolve_render_profile  # noqa: E402
from rl.training import build_vector_env  # noqa: E402

POINTER_KINDS = (1, 2, 3)


class ConditionalSpatialPolicy(nn.Module):
    """Action kind from global features, pointer location from a heatmap."""

    def __init__(
        self,
        observation_space,
        width: int,
        height: int,
        features_dim: int = 256,
        pointer_depth: int = 6,
    ):
        super().__init__()
        self.encoder = MiniMetroCNN(observation_space, features_dim)
        self.convolutions = self.encoder.encoder[:-1]
        # The heatmap can be read from an earlier, finer grid. MiniMetroCNN
        # strides 4/2/2 down to 7x12, so a heatmap taken at the end is upsampled
        # ~16x to reach the action grid while a station is about 10 px wide.
        # SC2LE's fully convolutional agent preserves resolution for exactly
        # this reason. Depth 2 keeps 27x48, depth 4 keeps 13x24, depth 6 is 7x12.
        self.pointer_layers = self.encoder.encoder[:pointer_depth]
        channels = [
            layer.out_channels
            for layer in self.encoder.encoder[:pointer_depth]
            if isinstance(layer, nn.Conv2d)
        ][-1]
        self.kind = nn.Sequential(
            nn.Linear(features_dim, 128), nn.ReLU(), nn.Linear(128, 8)
        )
        self.point = nn.Conv2d(channels, 1, kernel_size=1)
        self.width = width
        self.height = height

    def forward(self, observations):
        grid = self.convolutions(observations)
        features = self.encoder.projection(torch.flatten(grid, 1))
        heat = F.interpolate(
            self.point(self.pointer_layers(observations)),
            size=(self.height, self.width),
            mode="bilinear",
            align_corners=False,
        ).squeeze(1)
        return (
            self.kind(features),
            torch.logsumexp(heat, dim=1),
            torch.logsumexp(heat, dim=2),
        )

    @torch.no_grad()
    def act(self, observation, device, deterministic: bool):
        obs = torch.as_tensor(observation[None]).to(device).float() / 255.0
        kind_logits, x_logits, y_logits = self(obs)
        if deterministic:
            kind = int(kind_logits.argmax(-1))
            x = int(x_logits.argmax(-1))
            y = int(y_logits.argmax(-1))
        else:
            kind = int(torch.distributions.Categorical(logits=kind_logits).sample())
            x = int(torch.distributions.Categorical(logits=x_logits).sample())
            y = int(torch.distributions.Categorical(logits=y_logits).sample())
        return np.array([kind, x, y], dtype=np.int64)


def collect(vec, episodes: int):
    """Play scripted games, keeping every action with its observation."""
    observations, actions = [], []
    scores = []
    for index in range(episodes):
        observation = vec.reset()
        env = base_env(vec)
        finished = [False]
        delivered = [0.0]

        def apply(sequence):
            nonlocal observation
            for action in sequence:
                if finished[0]:
                    return
                array = np.asarray(action, dtype=np.int64)
                observations.append(observation[0].copy())
                actions.append(array)
                observation, rewards, dones, _ = vec.step(array[None])
                delivered[0] += float(rewards[0])
                finished[0] = bool(dones[0])

        initial = len(capture_privileged_snapshot(env).station_positions)
        apply(drag_route_actions(env, tuple(range(initial))))
        for _ in range(3):
            try:
                apply(_assign_locomotive_actions(env))
            except Exception:
                break
        connected = set(range(initial))
        while not finished[0] and len(observations) < 400000:
            apply([NOOP] * 30)
            if finished[0]:
                break
            snapshot = capture_privileged_snapshot(env)
            fresh = [
                i for i in range(len(snapshot.station_positions)) if i not in connected
            ]
            if fresh and snapshot.line_credits > 0:
                group = tuple(dict.fromkeys(sorted(connected)[:2] + fresh))[:8]
                if len(group) >= 2:
                    try:
                        apply(drag_route_actions(env, group))
                        connected |= set(group)
                        apply(_assign_locomotive_actions(env))
                    except Exception:
                        pass
        scores.append(int(delivered[0]))
        print(
            f"  episode {index + 1}/{episodes}: {scores[-1]} deliveries, {len(observations)} samples"
        )
    return np.stack(observations), np.stack(actions), scores


def balance(observations, actions, noop_keep: float, rng):
    """Keep every meaningful action and only a slice of the waiting."""
    keep = np.array(
        [int(action[0]) != 0 or rng.random() < noop_keep for action in actions]
    )
    return observations[keep], actions[keep]


def train(model, observations, actions, *, epochs, batch_size, lr, device):
    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    pointer = torch.as_tensor(
        np.isin(actions[:, 0], POINTER_KINDS).astype(np.float32)
    ).to(device)
    for epoch in range(epochs):
        order = np.random.permutation(len(observations))
        kind_losses, point_losses = [], []
        for start in range(0, len(order), batch_size):
            index = order[start : start + batch_size]
            obs = torch.as_tensor(observations[index]).to(device).float() / 255.0
            target = torch.as_tensor(actions[index]).to(device)
            mask = pointer[index]
            kind_logits, x_logits, y_logits = model(obs)
            kind_loss = F.cross_entropy(kind_logits, target[:, 0])
            # Only the kinds that read coordinates contribute pointer loss; the
            # rest ignore them, so supervising those would fit noise.
            per_x = F.cross_entropy(x_logits, target[:, 1], reduction="none")
            per_y = F.cross_entropy(y_logits, target[:, 2], reduction="none")
            denominator = mask.sum().clamp(min=1.0)
            point_loss = ((per_x + per_y) * mask).sum() / denominator
            loss = kind_loss + point_loss
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            optimizer.step()
            kind_losses.append(float(kind_loss.item()))
            point_losses.append(float(point_loss.item()))
        print(
            f"  epoch {epoch + 1}/{epochs}: kind {np.mean(kind_losses):.4f}  "
            f"pointer {np.mean(point_losses):.4f}"
        )


def play(
    model, vec, *, episodes, device, deterministic, max_decisions, seed, record=None
):
    from PIL import Image

    results = []
    best = (-1, None)
    for episode in range(episodes):
        vec.seed(seed + episode)
        observation = vec.reset()
        delivered = 0.0
        decisions = 0
        frames = []
        while decisions < max_decisions:
            if record is not None and decisions % 4 == 0:
                # The newest frame of the stack is the current view.
                latest = observation[0][-3:]
                image = Image.fromarray(np.transpose(latest, (1, 2, 0)))
                frames.append(
                    image.resize(
                        (image.width * 2, image.height * 2), Image.NEAREST
                    ).convert("P", palette=Image.ADAPTIVE, colors=128)
                )
            action = model.act(observation[0], device, deterministic)
            observation, rewards, dones, _ = vec.step(action[None])
            delivered += float(rewards[0])
            decisions += 1
            if bool(dones[0]):
                break
        results.append((int(delivered), decisions))
        if record is not None and int(delivered) > best[0]:
            best = (int(delivered), frames)
        print(
            f"  episode {episode + 1}/{episodes}: {int(delivered)} deliveries in {decisions} decisions"
        )
    if record is not None and best[1]:
        record.parent.mkdir(parents=True, exist_ok=True)
        best[1][0].save(
            record,
            save_all=True,
            append_images=best[1][1:],
            duration=80,
            loop=0,
            optimize=True,
        )
        print(f"  recorded best episode ({best[0]} deliveries) -> {record}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=40)
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=96)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--noop-keep", type=float, default=0.06)
    parser.add_argument("--eval-episodes", type=int, default=6)
    parser.add_argument("--max-decisions", type=int, default=4000)
    parser.add_argument("--render-profile", default="fast")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--record", type=Path, help="write a GIF of the best episode")
    parser.add_argument(
        "--pointer-depth",
        type=int,
        default=6,
        help="encoder depth the heatmap is read from: 2 keeps 27x48, 6 keeps 7x12",
    )
    args = parser.parse_args(argv)

    profile = resolve_render_profile(args.render_profile)
    spec = TaskSpec(render_profile=profile)
    vec = build_vector_env(spec, n_envs=1, seed=args.seed, history=default_history())
    rng = np.random.default_rng(args.seed)
    torch.manual_seed(args.seed)

    try:
        observations, actions, scores = collect(vec, args.episodes)
        observations, actions = balance(observations, actions, args.noop_keep, rng)
        print(
            f"\nexpert mean {np.mean(scores):.1f} deliveries | "
            f"training on {len(observations)} samples "
            f"({observations.nbytes / 2**20:.0f} MiB)"
        )

        space = spaces.Box(low=0, high=255, shape=observations.shape[1:], dtype="uint8")
        model = ConditionalSpatialPolicy(
            space, profile.width, profile.height, pointer_depth=args.pointer_depth
        )
        print(f"policy parameters: {sum(p.numel() for p in model.parameters()):,}\n")
        train(
            model,
            observations,
            actions,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.learning_rate,
            device=args.device,
        )

        for label, deterministic in (("deterministic", True), ("stochastic", False)):
            print(f"\nplaying, {label}:")
            results = play(
                model,
                vec,
                episodes=args.eval_episodes,
                device=args.device,
                deterministic=deterministic,
                max_decisions=args.max_decisions,
                seed=9000,
                record=args.record if deterministic else None,
            )
            deliveries = [row[0] for row in results]
            print(
                f"  -> mean {np.mean(deliveries):.2f}  max {max(deliveries)}  "
                f"(random 0, scripted expert ~20)"
            )
    finally:
        vec.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

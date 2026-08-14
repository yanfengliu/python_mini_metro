"""Bootstrap a policy past the exploration barrier with behaviour cloning.

Vanilla RL cannot start on this task. Drawing a line needs pointer-down on a
station, motion, then pointer-up on another, and with roughly ten-pixel targets
in a 192x108 coordinate space random exploration never produces that sequence:
measured over 12 random episodes and 4170 decisions, zero built a usable line.
Every reward is then 0, every advantage is 0, and the policy gradient carries no
signal at all.

This clones the repository's scripted expert instead, using the policy's own
``evaluate_actions`` so the loss is exactly the negative log probability of the
expert's action and the trained weights drop straight into RecurrentPPO.

Two deliberate simplifications, stated because they bound what this proves.
Expert episodes are dominated by waiting, so noop steps are subsampled to stop
the policy learning that doing nothing is always correct. And each sample is
cloned with a reset recurrent state rather than as part of a carried sequence,
so this teaches a reactive mapping and leaves recurrence to the PPO stage.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import torch  # noqa: E402

from rl.demonstrator import _assign_locomotive_actions, drag_route_actions  # noqa: E402
from rl.history import default_history  # noqa: E402
from rl.policy import make_model  # noqa: E402
from rl.privileged_oracle import capture_privileged_snapshot  # noqa: E402
from rl.protocol import TaskSpec, resolve_render_profile  # noqa: E402
from rl.training import build_vector_env  # noqa: E402

NOOP = np.array([0, 0, 0], dtype=np.int64)
WAIT_STEPS = 30


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return parsed


def base_env(vec):
    """Reach the PlayerPixelEnv that the scripted expert needs to read."""
    node = vec
    for _ in range(8):
        if hasattr(node, "envs"):
            node = node.envs[0]
            break
        node = getattr(node, "venv", None) or getattr(node, "env", None)
        if node is None:
            raise RuntimeError("wrapper chain ended before a vector env was found")
    for _ in range(8):
        if hasattr(node, "task_spec"):
            return node
        node = getattr(node, "env", None)
        if node is None:
            break
    raise RuntimeError("could not reach PlayerPixelEnv through the wrapper chain")


def expert_episode(vec, *, noop_keep, rng, max_decisions):
    """Play one scripted game, returning the kept observation/action pairs."""
    observation = vec.reset()
    env = base_env(vec)
    kept = []
    taken = 0
    finished = False
    delivered = 0.0

    def apply(actions):
        nonlocal observation, taken, finished, delivered
        for action in actions:
            if finished or taken >= max_decisions:
                return
            array = np.asarray(action, dtype=np.int64)
            if int(array[0]) != 0 or rng.random() < noop_keep:
                kept.append((observation[0].copy(), array))
            observation, rewards, dones, _ = vec.step(array[None])
            # A vector env auto-resets on termination, so the end-of-episode
            # snapshot describes the NEXT game. Accumulate reward instead.
            delivered += float(rewards[0])
            taken += 1
            finished = bool(dones[0])

    initial = len(capture_privileged_snapshot(env).station_positions)
    apply(drag_route_actions(env, tuple(range(initial))))
    for _ in range(3):
        try:
            apply(_assign_locomotive_actions(env))
        except Exception:
            break

    connected = set(range(initial))
    while not finished and taken < max_decisions:
        apply([NOOP] * WAIT_STEPS)
        if finished:
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
    return kept, int(delivered), taken


def clone(model, observations, actions, *, epochs, batch_size, lr):
    """Maximise the log probability the policy assigns to the expert's actions."""
    from sb3_contrib.common.recurrent.type_aliases import RNNStates

    policy = model.policy
    device = model.device
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    lstm = policy.lstm_actor
    total = len(observations)
    history = []
    for epoch in range(epochs):
        order = np.random.permutation(total)
        losses = []
        for start in range(0, total, batch_size):
            index = order[start : start + batch_size]
            if len(index) < 2:
                continue
            obs = torch.as_tensor(observations[index]).to(device).float() / 255.0
            act = torch.as_tensor(actions[index]).to(device)
            shape = (lstm.num_layers, len(index), lstm.hidden_size)
            zeros = (
                torch.zeros(shape, device=device),
                torch.zeros(shape, device=device),
            )
            # Each sample is its own sequence start, so recurrent state never
            # carries between unrelated samples inside a shuffled batch.
            starts = torch.ones(len(index), device=device)
            _, log_prob, _ = policy.evaluate_actions(
                obs, act, RNNStates(zeros, zeros), starts
            )
            loss = -log_prob.mean()
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            optimizer.step()
            losses.append(float(loss.item()))
        history.append(float(np.mean(losses)))
        print(f"  epoch {epoch + 1}/{epochs}: mean -log_prob {history[-1]:.4f}")
    return history


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=_positive_int, default=24)
    parser.add_argument("--epochs", type=_positive_int, default=8)
    parser.add_argument("--batch-size", type=_positive_int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--noop-keep", type=float, default=0.08)
    parser.add_argument("--max-decisions", type=_positive_int, default=4000)
    parser.add_argument("--render-profile", default="fast")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    spec = TaskSpec(render_profile=resolve_render_profile(args.render_profile))
    vec = build_vector_env(spec, n_envs=1, seed=args.seed, history=default_history())
    model = make_model(
        vec, algorithm="recurrent_ppo", seed=args.seed, n_envs=1, device=args.device
    )
    rng = np.random.default_rng(args.seed)

    started = time.perf_counter()
    pairs = []
    scores = []
    for episode in range(args.episodes):
        kept, deliveries, taken = expert_episode(
            vec, noop_keep=args.noop_keep, rng=rng, max_decisions=args.max_decisions
        )
        pairs.extend(kept)
        scores.append(deliveries)
        print(
            f"episode {episode + 1}/{args.episodes}: {deliveries} deliveries, "
            f"{taken} decisions, kept {len(kept)} (total {len(pairs)})"
        )

    observations = np.stack([pair[0] for pair in pairs])
    actions = np.stack([pair[1] for pair in pairs])
    print(
        f"\ndataset {observations.shape} "
        f"({observations.nbytes / 2**20:.0f} MiB) in "
        f"{time.perf_counter() - started:.0f}s"
    )
    print(f"expert deliveries: mean {np.mean(scores):.1f}, max {max(scores)}")
    print(f"action-kind counts: {np.bincount(actions[:, 0], minlength=8).tolist()}")

    history = clone(
        model,
        observations,
        actions,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.learning_rate,
    )
    uniform = float(np.log(8) + np.log(192) + np.log(108))
    print(f"\n-log_prob {uniform:.3f} (uniform) -> {history[-1]:.3f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))
    print(f"saved: {args.output}")
    vec.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

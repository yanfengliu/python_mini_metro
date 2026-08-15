"""Clone the scripted heuristic -- policy AND value -- then hand PPO the weights.

Training this lane from scratch has failed in every configuration tried, and the
best learned policy still loses to a fifteen-action script. So PPO starts from a
policy that already plays, which is what finally worked on the pixel lane.

Two things are cloned, and the second one is not optional. Cloning only the
policy leaves the critic at its initialisation -- measured at 0.28 while true
discounted returns are ~30-60 at gamma=0.999 -- so PPO's very first advantages
are (return minus garbage) and the fine-tune destroys the cloned policy within
50,000 steps. That was observed twice before the cause was found.

The dataset is brutally imbalanced by construction: the heuristic acts about 14
times in 7,000 decisions, so ~99.8% of its labels are WAIT. Cloning that directly
produces a policy that waits forever, which is the greedy-no-op failure already
recorded as E20. Non-WAIT decisions are therefore kept in full and WAIT is
subsampled, with the resulting mix reported rather than assumed.

Cross-entropy is computed over the *masked* distribution, because that is what
the policy actually samples from.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import torch  # noqa: E402

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402


def collect(episodes: int, wait_keep: float, seed: int, gamma: float):
    """Play the heuristic, keeping every real decision and a slice of the waits."""
    rng = np.random.default_rng(seed)
    observations, actions, masks, returns = [], [], [], []
    scores = []
    for index in range(episodes):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=seed + index)
        delivered = 0.0
        kept_at, rewards = [], []
        try:
            while True:
                mask = env.action_masks()
                action = choose(env)
                if action != 0 or rng.random() < wait_keep:
                    observations.append(observation.copy())
                    actions.append(action)
                    masks.append(mask.copy())
                    kept_at.append(len(rewards))
                observation, reward, terminated, truncated, _ = env.step(action)
                rewards.append(float(reward))
                delivered += float(reward)
                if terminated or truncated:
                    break
        finally:
            env.close()

        # Discounted return-to-go for every kept state, so the critic can be
        # fitted to what this policy actually earns from here.
        togo = np.zeros(len(rewards) + 1, dtype=np.float64)
        for step in range(len(rewards) - 1, -1, -1):
            togo[step] = rewards[step] + gamma * togo[step + 1]
        returns.extend(float(togo[at]) for at in kept_at)

        scores.append(delivered)
        print(
            f"  episode {index + 1}/{episodes}: {int(delivered)} deliveries, "
            f"{len(observations)} samples kept",
            flush=True,
        )
    return (
        np.stack(observations),
        np.array(actions, dtype=np.int64),
        np.stack(masks),
        np.array(returns, dtype=np.float32),
        scores,
    )


def clone(model, observations, actions, masks, returns, *, epochs, batch_size, lr):
    policy = model.policy
    device = model.device
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    total = len(observations)
    for epoch in range(epochs):
        order = np.random.permutation(total)
        action_losses, value_losses, correct = [], [], 0
        for start in range(0, total, batch_size):
            index = order[start : start + batch_size]
            obs = torch.as_tensor(observations[index]).to(device).float()
            target = torch.as_tensor(actions[index]).to(device)
            mask = torch.as_tensor(masks[index]).to(device)
            target_value = torch.as_tensor(returns[index]).to(device).float()

            features = policy.extract_features(obs)
            latent_pi, latent_vf = policy.mlp_extractor(features)
            logits = policy.action_net(latent_pi).masked_fill(~mask, -1e8)
            value = policy.value_net(latent_vf).flatten()

            action_loss = torch.nn.functional.cross_entropy(logits, target)
            value_loss = torch.nn.functional.mse_loss(value, target_value)
            loss = action_loss + 0.5 * value_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            optimizer.step()
            action_losses.append(float(action_loss.item()))
            value_losses.append(float(value_loss.item()))
            correct += int((logits.argmax(-1) == target).sum())
        print(
            f"  epoch {epoch + 1}/{epochs}: action {np.mean(action_losses):.4f}  "
            f"value {np.mean(value_losses):.1f}  agreement {correct / total:.1%}",
            flush=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--wait-keep", type=float, default=0.02)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path, default=Path("output/semantic/bc"))
    args = parser.parse_args(argv)

    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from stable_baselines3.common.vec_env import DummyVecEnv

    observations, actions, masks, returns, scores = collect(
        args.episodes, args.wait_keep, args.seed, args.gamma
    )
    kinds = {}
    for action in actions:
        name = ActionKind(ACTION_TABLE[action][0]).name
        kinds[name] = kinds.get(name, 0) + 1
    print(f"\nteacher: mean {np.mean(scores):.1f} deliveries over {len(scores)} games")
    print(f"dataset: {len(observations)} samples, label mix {kinds}")
    print(
        f"returns to fit: mean {returns.mean():.1f}  max {returns.max():.1f} "
        f"(gamma {args.gamma})"
    )

    venv = DummyVecEnv(
        [lambda: ActionMasker(SemanticMetroEnv(), lambda e: e.action_masks())]
    )
    model = MaskablePPO(
        "MlpPolicy",
        venv,
        seed=args.seed,
        device=args.device,
        n_steps=256,
        gamma=args.gamma,
        verbose=0,
    )
    clone(
        model,
        observations,
        actions,
        masks,
        returns,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.learning_rate,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))
    print(f"saved: {args.output}")
    venv.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

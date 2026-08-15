"""DAgger: label the states the CLONE visits, not the ones the teacher visits.

Plain cloning reproduces about 72% of the teacher's ~14 real decisions per
episode -- roughly four wrong choices, costing ~70 deliveries against a teacher
at 262. More offline demonstrations do not fix that, because they keep
demonstrating states the *teacher* reaches. The clone's mistakes take it
somewhere the teacher never goes, and it has never been told what to do there.

DAgger (Ross, Gordon & Bagnell 2011) closes exactly that loop: roll out the
current policy, ask the teacher what it would have done in each state the policy
actually reached, add those labels, retrain. The training distribution converges
on the policy's own state distribution rather than the teacher's.

Two details that matter here. The aggregated dataset keeps every earlier round,
so the policy cannot forget what it already learned. And rollouts use the current
policy from the first round onward -- no expert mixing -- because the clone is
already competent enough to reach useful states, and mixing would just re-collect
the teacher's own distribution.
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


def roll_out(model, episodes: int, seed: int, gamma: float, wait_keep: float, rng):
    """Play with the current policy; label every state with the teacher's choice."""
    observations, actions, masks, returns = [], [], [], []
    scores, agreements = [], []
    for index in range(episodes):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=seed + index)
        delivered = 0.0
        kept_at, rewards = [], []
        agree = real = 0
        try:
            while True:
                mask = env.action_masks()
                teacher = choose(env)
                predicted, _ = model.predict(
                    observation, action_masks=mask, deterministic=True
                )
                taken = int(np.asarray(predicted).ravel()[0])
                if teacher != 0:
                    real += 1
                    agree += int(taken == teacher)
                # The label is the TEACHER's action; the state is where the
                # POLICY went. That asymmetry is the whole method.
                if teacher != 0 or rng.random() < wait_keep:
                    observations.append(observation.copy())
                    actions.append(teacher)
                    masks.append(mask.copy())
                    kept_at.append(len(rewards))
                observation, reward, terminated, truncated, _ = env.step(taken)
                rewards.append(float(reward))
                delivered += float(reward)
                if terminated or truncated:
                    break
        finally:
            env.close()
        togo = np.zeros(len(rewards) + 1, dtype=np.float64)
        for step in range(len(rewards) - 1, -1, -1):
            togo[step] = rewards[step] + gamma * togo[step + 1]
        returns.extend(float(togo[at]) for at in kept_at)
        scores.append(delivered)
        agreements.append(agree / max(real, 1))
    return (
        np.stack(observations),
        np.array(actions, dtype=np.int64),
        np.stack(masks),
        np.array(returns, dtype=np.float32),
        float(np.mean(scores)),
        float(np.mean(agreements)),
    )


def fit(model, data, *, epochs, batch_size, lr):
    observations, actions, masks, returns = data
    policy = model.policy
    device = model.device
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    total = len(observations)
    for _ in range(epochs):
        order = np.random.permutation(total)
        for start in range(0, total, batch_size):
            index = order[start : start + batch_size]
            obs = torch.as_tensor(observations[index]).to(device).float()
            target = torch.as_tensor(actions[index]).to(device)
            mask = torch.as_tensor(masks[index]).to(device)
            target_value = torch.as_tensor(returns[index]).to(device).float()
            features = policy.extract_features(obs)
            latent_pi, latent_vf = policy.mlp_extractor(features)
            raw = (
                policy._action_logits(latent_pi)
                if hasattr(policy, "_action_logits")
                else policy.action_net(latent_pi)
            )
            logits = raw.masked_fill(~mask, -1e8)
            value = policy.value_net(latent_vf).flatten()
            loss = torch.nn.functional.cross_entropy(
                logits, target
            ) + 0.5 * torch.nn.functional.mse_loss(value, target_value)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            optimizer.step()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=Path, default=Path("output/semantic/bc3"))
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--wait-keep", type=float, default=0.02)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path, default=Path("output/semantic/dagger"))
    args = parser.parse_args(argv)

    from sb3_contrib import MaskablePPO

    model = MaskablePPO.load(str(args.start), device=args.device)
    rng = np.random.default_rng(args.seed)
    pool: list[tuple] = []

    print(f"starting from {args.start}; teacher scores ~262")
    for round_index in range(args.rounds):
        # Fresh seeds each round, so the aggregate covers many layouts.
        seed = args.seed + round_index * args.episodes
        obs, act, msk, ret, score, agreement = roll_out(
            model, args.episodes, seed, args.gamma, args.wait_keep, rng
        )
        pool.append((obs, act, msk, ret))
        data = tuple(np.concatenate([p[i] for p in pool]) for i in range(4))
        kinds = {}
        for action in act:
            name = ActionKind(ACTION_TABLE[action][0]).name
            kinds[name] = kinds.get(name, 0) + 1
        print(
            f"round {round_index + 1}/{args.rounds}: policy scored {score:6.1f}, "
            f"agreed with teacher on {agreement:5.1%} of real decisions, "
            f"aggregated {len(data[0])} samples",
            flush=True,
        )
        fit(
            model,
            data,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.learning_rate,
        )
        model.save(str(args.output))

    obs, act, msk, ret, score, agreement = roll_out(
        model, args.episodes, args.seed + 5000, args.gamma, args.wait_keep, rng
    )
    print(f"\nfinal: {score:.1f} deliveries, {agreement:.1%} real-decision agreement")
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

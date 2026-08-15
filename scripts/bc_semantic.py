"""Clone the scripted heuristic, then hand the weights to PPO.

Training this lane from scratch has now failed in every configuration tried, and
the best learned policy (190.8) still loses to a fifteen-action script (276.9) on
17 of 20 seeds. Rather than keep searching for a from-scratch fix, this starts
PPO from a policy that already plays, which is what finally worked on the pixel
lane.

The dataset is brutally imbalanced by construction: the heuristic acts about 14
times in 7,000 decisions, so 99.8% of its labels are WAIT. Cloning that directly
produces a policy that waits forever -- the exact greedy-no-op failure already
recorded as E20. So non-WAIT decisions are kept in full and WAIT is subsampled,
with the ratio reported rather than assumed.

Cross-entropy is computed over the *masked* distribution, because that is what
the policy actually samples from; scoring against the unmasked logits would train
it on 364 actions the game will never offer.
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


def collect(episodes: int, wait_keep: float, seed: int):
    """Play the heuristic, keeping every real decision and a slice of the waits."""
    rng = np.random.default_rng(seed)
    observations, actions, masks = [], [], []
    scores = []
    for index in range(episodes):
        env = SemanticMetroEnv()
        observation, _ = env.reset(seed=seed + index)
        delivered = 0.0
        try:
            while True:
                mask = env.action_masks()
                action = choose(env)
                if action != 0 or rng.random() < wait_keep:
                    observations.append(observation.copy())
                    actions.append(action)
                    masks.append(mask.copy())
                observation, reward, terminated, truncated, _ = env.step(action)
                delivered += float(reward)
                if terminated or truncated:
                    break
        finally:
            env.close()
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
        scores,
    )


def clone(model, observations, actions, masks, *, epochs, batch_size, lr):
    policy = model.policy
    device = model.device
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    total = len(observations)
    for epoch in range(epochs):
        order = np.random.permutation(total)
        losses, correct = [], 0
        for start in range(0, total, batch_size):
            index = order[start : start + batch_size]
            obs = torch.as_tensor(observations[index]).to(device).float()
            target = torch.as_tensor(actions[index]).to(device)
            mask = torch.as_tensor(masks[index]).to(device)
            latent_pi, _ = policy.mlp_extractor(policy.extract_features(obs))
            logits = policy.action_net(latent_pi)
            # Score against what the policy will actually sample from.
            logits = logits.masked_fill(~mask, -1e8)
            loss = torch.nn.functional.cross_entropy(logits, target)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            optimizer.step()
            losses.append(float(loss.item()))
            correct += int((logits.argmax(-1) == target).sum())
        print(
            f"  epoch {epoch + 1}/{epochs}: loss {np.mean(losses):.4f}  "
            f"agreement {correct / total:.1%}",
            flush=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=25)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--wait-keep", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path, default=Path("output/semantic/bc"))
    args = parser.parse_args(argv)

    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from stable_baselines3.common.vec_env import DummyVecEnv

    observations, actions, masks, scores = collect(
        args.episodes, args.wait_keep, args.seed
    )
    kinds = {}
    for action in actions:
        name = ActionKind(ACTION_TABLE[action][0]).name
        kinds[name] = kinds.get(name, 0) + 1
    print(f"\nteacher: mean {np.mean(scores):.1f} deliveries over {len(scores)} games")
    print(f"dataset: {len(observations)} samples, label mix {kinds}")

    venv = DummyVecEnv(
        [lambda: ActionMasker(SemanticMetroEnv(), lambda e: e.action_masks())]
    )
    model = MaskablePPO(
        "MlpPolicy", venv, seed=args.seed, device=args.device, n_steps=256, verbose=0
    )
    clone(
        model,
        observations,
        actions,
        masks,
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

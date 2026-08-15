"""Distil search into a network, so the policy plays well without searching.

Search reaches decisions the heuristic misses -- 380 where the heuristic scores
275 at the opening of seed 9000 -- but it pays for them with hundreds of
full-episode rollouts per decision. A network that has absorbed those choices
plays at the same standard for one forward pass, which is the whole point of
distillation and the reason AlphaZero-style loops distil search back into a
policy rather than shipping the search.

This is deliberately the same cloning procedure already validated for the
heuristic lane, with one thing changed: the labels come from `search_dataset.py`
instead of from `rl.heuristic`. Everything the earlier work paid to learn is kept.

  * The value head is cloned alongside the policy. Leaving the critic at its
    initialisation -- 0.28 against true discounted returns of 30-60 -- made PPO's
    first advantages garbage and destroyed a good policy inside 50,000 steps.
    That was diagnosed twice before the cause was found.
  * Cross-entropy is over the MASKED distribution, since that is what the policy
    actually samples from.
  * Logits go through the policy's own path. `action_net` is dead on the pointer
    policy, which computes logits in `_action_logits`; training the dead one gave
    98% surface agreement and 0.2% agreement on decisions that matter.
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

from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402


def _real_agreement(policy, device, observations, actions, masks) -> float:
    """Agreement on decisions that are not WAIT, which is the only kind that
    distinguishes a player from a policy that waits forever.
    """
    import torch as th

    real = np.flatnonzero(actions != 0)
    if len(real) == 0:
        return float("nan")
    with th.no_grad():
        obs = th.as_tensor(observations[real]).to(device).float()
        mask = th.as_tensor(masks[real]).to(device)
        features = policy.extract_features(obs)
        latent_pi, _ = policy.mlp_extractor(features)
        raw = (
            policy._action_logits(latent_pi)
            if hasattr(policy, "_action_logits")
            else policy.action_net(latent_pi)
        )
        predicted = raw.masked_fill(~mask, -1e8).argmax(-1).cpu().numpy()
    return float((predicted == actions[real]).mean())


def fit(model, data, *, epochs, batch_size, lr, report, validation=None):
    observations, actions, masks, returns = data
    policy = model.policy
    device = model.device
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    total = len(observations)
    # Agreement on the decisions that matter is the number worth watching;
    # overall agreement is dominated by WAIT and stays high while the policy
    # learns nothing about when to act.
    real = np.flatnonzero(actions != 0)

    for epoch in range(epochs):
        order = np.random.permutation(total)
        action_losses, value_losses = [], []
        correct = real_correct = 0
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

            action_loss = torch.nn.functional.cross_entropy(logits, target)
            value_loss = torch.nn.functional.mse_loss(value, target_value)
            loss = action_loss + 0.5 * value_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            optimizer.step()

            hit = logits.argmax(-1) == target
            correct += int(hit.sum())
            real_correct += int((hit & (target != 0)).sum())
            action_losses.append(float(action_loss.item()))
            value_losses.append(float(value_loss.item()))

        if (epoch + 1) % report == 0 or epoch == epochs - 1:
            line = (
                f"  epoch {epoch + 1}/{epochs}: action {np.mean(action_losses):.4f}  "
                f"value {np.mean(value_losses):.1f}  "
                f"train real-decision {real_correct / max(len(real), 1):.1%}"
            )
            if validation is not None:
                held = _real_agreement(policy, device, *validation)
                line += f"  HELD-OUT {held:.1%}"
            print(line, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path("output/semantic/search-data.npz")
    )
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--arch", choices=("mlp", "pointer"), default="mlp")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--report", type=int, default=10)
    parser.add_argument(
        "--holdout",
        type=float,
        default=0.25,
        help="fraction of EPISODES reserved for validation (0 disables)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/semantic/distilled")
    )
    args = parser.parse_args(argv)

    if not args.data.exists():
        raise SystemExit(
            f"no dataset at {args.data}; run scripts/search_dataset.py first to "
            "generate search-labelled decisions"
        )

    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from stable_baselines3.common.vec_env import DummyVecEnv

    archive = np.load(args.data)
    observations = archive["observations"]
    actions = archive["actions"]
    masks = archive["masks"]
    returns = archive["returns"]
    episode = archive["episode"] if "episode" in archive.files else None

    # The split is by EPISODE, never by sample. Samples from one episode share a
    # board, a layout and a difficulty ramp, so a random sample split puts
    # near-duplicate states on both sides and reports a generalisation number
    # that is nothing of the kind -- which matters here, because 250 epochs
    # reached 92.7% training agreement on 4,815 labels and that is exactly the
    # regime where memorisation is indistinguishable from learning.
    validation = None
    if episode is not None and args.holdout > 0:
        seeds = np.unique(episode)
        held = seeds[: max(1, int(len(seeds) * args.holdout))]
        keep = ~np.isin(episode, held)
        validation = (
            observations[~keep],
            actions[~keep],
            masks[~keep],
        )
        print(
            f"held out {len(held)} of {len(seeds)} episodes "
            f"({int((~keep).sum())} labels) as a validation set"
        )
        observations, actions, masks, returns = (
            observations[keep],
            actions[keep],
            masks[keep],
            returns[keep],
        )
    elif episode is None:
        print(
            "WARNING: this dataset has no episode ids, so no honest held-out "
            "split is possible; training agreement alone cannot distinguish "
            "learning from memorisation"
        )

    kinds: dict[str, int] = {}
    for action in actions:
        name = ActionKind(ACTION_TABLE[action][0]).name
        kinds[name] = kinds.get(name, 0) + 1
    print(f"dataset: {len(actions)} labels from {args.data}")
    print(f"  mix {kinds}")
    print(
        f"  returns to fit: mean {returns.mean():.1f}  max {returns.max():.1f} "
        f"(gamma {args.gamma})"
    )

    venv = DummyVecEnv(
        [lambda: ActionMasker(SemanticMetroEnv(), lambda e: e.action_masks())]
    )
    if args.arch == "pointer":
        from rl.semantic_nets import PointerExtractor, build_pointer_policy_class

        policy_class = build_pointer_policy_class()
        policy_kwargs = dict(features_extractor_class=PointerExtractor)
    else:
        policy_class = "MlpPolicy"
        policy_kwargs = {}

    model = MaskablePPO(
        policy_class,
        venv,
        policy_kwargs=policy_kwargs,
        seed=args.seed,
        device=args.device,
        n_steps=256,
        gamma=args.gamma,
        verbose=0,
    )
    fit(
        model,
        (observations, actions, masks, returns),
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.learning_rate,
        report=args.report,
        validation=validation,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))
    print(f"saved: {args.output}")
    venv.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

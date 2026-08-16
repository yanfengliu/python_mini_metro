"""Train a policy on CONSTANT input and play it. The review's blind control.

The claim under test: such a network scores ~204 deliveries, statistically tied
with the distilled policy at 203.71, implying nothing learned in this project
beats a policy that cannot see the board.

Three cheaper reconstructions failed to reproduce it, and the spread between them
is the point -- "blind" is not one thing:

    uniform over legal actions        0.00   (redraws lines; the game collapses)
    the heuristic's true marginal     0.00   (99.8% WAIT; builds nothing)
    the dataset's label marginal     60.77   (WAIT subsampled at 0.02)
    a net trained on constant input  186.32  <- this file

So this builds it literally: the same architecture and the same cloning
procedure, with every observation replaced by a vector of ones.

Measured paired against the real policies on 40 shared seeds:

    blind      186.32 +/-26.60      longest_line 6.85
    distilled  175.78 +/-27.90      longest_line 6.72
    heuristic  248.78 +/-30.39      longest_line 7.50

    distilled vs blind   -10.55 +/-24.29, won 19/40   (MDE 34.7)
    distilled vs blind   -0.12 +/-0.32, won 10/40     on longest_line

The distilled policy does not beat a network that cannot see the board, and on
the primary outcome it is marginally worse. That is the bar any future policy in
this project has to clear before its observation can be said to be doing
anything at all.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path[:0] = ["src", "scripts"]

import numpy as np  # noqa: E402
import torch  # noqa: E402
from sb3_contrib import MaskablePPO  # noqa: E402
from sb3_contrib.common.wrappers import ActionMasker  # noqa: E402
from stable_baselines3.common.vec_env import DummyVecEnv  # noqa: E402

from rl.semantic_env import SemanticMetroEnv  # noqa: E402

DATA = "output/semantic/search-data.npz"

archive = np.load(DATA)
observations = archive["observations"]
actions = archive["actions"]
masks = archive["masks"]

# The whole point: the network sees nothing about the board.
blind = np.ones_like(observations)
print(f"training on {len(actions)} labels with observations replaced by ones")

venv = DummyVecEnv(
    [lambda: ActionMasker(SemanticMetroEnv(), lambda e: e.action_masks())]
)
model = MaskablePPO("MlpPolicy", venv, device="cpu", n_steps=256, seed=0, verbose=0)
policy = model.policy
optimizer = torch.optim.Adam(policy.parameters(), lr=3e-4)

for epoch in range(40):
    order = np.random.permutation(len(actions))
    losses = []
    for start in range(0, len(order), 128):
        index = order[start : start + 128]
        obs = torch.as_tensor(blind[index]).float()
        target = torch.as_tensor(actions[index])
        mask = torch.as_tensor(masks[index])
        features = policy.extract_features(obs)
        latent_pi, _ = policy.mlp_extractor(features)
        logits = policy.action_net(latent_pi).masked_fill(~mask, -1e8)
        loss = torch.nn.functional.cross_entropy(logits, target)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
        optimizer.step()
        losses.append(float(loss.item()))
    if (epoch + 1) % 10 == 0:
        print(f"  epoch {epoch + 1}: loss {np.mean(losses):.4f}", flush=True)

model.save("output/semantic/blind-net")
print("saved output/semantic/blind-net")

# Play it, feeding ones at inference too.
scores, lines = [], []
for seed in range(70_000, 70_030):
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    torch.manual_seed(seed)
    total = 0.0
    while True:
        mask = env.action_masks()
        predicted, _ = model.predict(
            np.ones(env.observation_space.shape, dtype=np.float32),
            action_masks=mask,
            deterministic=False,
        )
        _, reward, terminated, truncated, _ = env.step(
            int(np.asarray(predicted).ravel()[0])
        )
        total += float(reward)
        if terminated or truncated:
            break
    lines.append(max((len(p.stations) for p in env._mediator.paths), default=0))
    scores.append(total)
    env.close()

array = np.array(scores)
stderr = array.std(ddof=1) / np.sqrt(len(array))
print(
    f"\nblind net: mean {array.mean():.2f} +/-{1.96 * stderr:.2f}  "
    f"median {np.median(array):.1f}  IQR [{np.percentile(array, 25):.0f}, "
    f"{np.percentile(array, 75):.0f}]  max {array.max():.0f}"
)
print(f"longest_line: mean {np.mean(lines):.2f}  median {np.median(lines):.1f}")
print("claim under test: ~204 deliveries")
venv.close()

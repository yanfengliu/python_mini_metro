"""RecurrentPPO policy whose pointer comes from a full-resolution heatmap.

The cloning harness measured a resolution-preserving pointer at 11.8x the
probability on the expert's exact pixel against the strided stack it replaces,
and the deliveries that followed. That gain lived outside the training path:
RecurrentPPO still built its distribution from a flat categorical over a global
feature vector. This carries the head into the live policy.

Two structural facts drive the design. Coordinates are read by only three of the
eight action kinds -- motion, pointer-down and pointer-up -- so the pointer is
conditional in the sense the parameterized-action literature uses. And choosing
where to click is keypoint localisation, which needs spatial *equivariance*,
while the inherited Nature-DQN stack was built for the translation *invariance*
that suits an eighteen-way joystick.

The heatmap deliberately bypasses the recurrent path. Pointing at a station is a
function of the current frame, not of history; routing it through the LSTM would
force position through a 256-value bottleneck, which is the exact loss this
replaces. History still reaches the action-kind and value heads.
"""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

from rl.pointer_nets import UNetPointer


class SpatialPointerExtractor(nn.Module):
    """Global features for the recurrent heads, pointer logits for the action.

    The pointer logits are stashed on the instance rather than returned, because
    Stable-Baselines3 expects a features extractor to yield a single flat tensor.
    They are consumed by the policy later in the same forward pass, and the
    recurrent reshaping in between preserves batch order, so the two stay
    aligned.
    """

    def __init__(self, observation_space, features_dim: int = 256):
        super().__init__()
        channels, height, width = observation_space.shape
        self.features_dim = features_dim
        self.net = UNetPointer(channels, width, height, features_dim=features_dim)
        self.pointer_logits: tuple[torch.Tensor, torch.Tensor] | None = None

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        grid = self.net.enc0(observations)
        e1 = self.net.enc1(grid)
        e2 = self.net.enc2(e1)
        e3 = self.net.enc3(e2)
        features = self.net.project(e3.mean(dim=(2, 3)))

        d2 = self.net.smooth2(self.net.lat2(e2) + self.net._up(self.net.lat3(e3), e2))
        d1 = self.net.smooth1(self.net.lat1(e1) + self.net._up(d2, e1))
        d0 = self.net.smooth0(self.net.lat0(grid) + self.net._up(d1, grid))
        heat = self.net.point(
            nn.functional.interpolate(
                d0,
                size=(self.net.height, self.net.width),
                mode="bilinear",
                align_corners=False,
            )
        ).squeeze(1)
        self.pointer_logits = (
            torch.logsumexp(heat, dim=1),
            torch.logsumexp(heat, dim=2),
        )
        return features


def build_spatial_policy_class() -> type[Any]:
    """Build the policy class lazily, so importing this module needs no torch stack."""
    from sb3_contrib.common.recurrent.policies import RecurrentActorCriticCnnPolicy

    class SpatialRecurrentPolicy(RecurrentActorCriticCnnPolicy):
        """RecurrentPPO with the pointer distribution taken from the heatmap."""

        def _get_action_dist_from_latent(self, latent_pi: torch.Tensor):
            logits = self.action_net(latent_pi)
            extractor = self.features_extractor
            pointer = getattr(extractor, "pointer_logits", None)
            if pointer is None:
                return self.action_dist.proba_distribution(action_logits=logits)
            x_logits, y_logits = pointer
            if x_logits.shape[0] != logits.shape[0]:
                raise RuntimeError(
                    "pointer logits batch "
                    f"{x_logits.shape[0]} does not match the policy batch "
                    f"{logits.shape[0]}; the features extractor and the action "
                    "head have fallen out of step"
                )
            # Keep the action-kind logits, which see history through the LSTM,
            # and replace the coordinate halves with the spatial heatmap.
            kinds = logits[:, : logits.shape[1] - x_logits.shape[1] - y_logits.shape[1]]
            combined = torch.cat([kinds, x_logits, y_logits], dim=1)
            return self.action_dist.proba_distribution(action_logits=combined)

    return SpatialRecurrentPolicy

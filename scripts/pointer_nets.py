"""Pointer architectures for the pixel task, from lossy to resolution-preserving.

The task's output is a *location*, which makes it keypoint localisation rather
than classification. The encoder inherited from Nature DQN was built for the
opposite job: Atari needed translation *invariance* to pick one of eighteen
joystick actions, so it strides 4/2/2 and deliberately discards position. This
repository's variant strides 2 on the third layer where the original used stride
1, so it downsamples more aggressively still, and a passenger 0.5 px wide is
gone before the second layer runs.

Two arms live here so the comparison is exact -- identical data, loss and
optimiser, differing only in how much spatial detail survives to the heatmap:

``StridedPointer``
    The status quo. Full strided stack for context; the heatmap is read from an
    intermediate layer (depth 2 was the best of the earlier sweep) and resampled
    up to the action grid.

``UNetPointer``
    Downsamples for context, then climbs back to *full observation resolution*
    through skip connections, so the heatmap is produced at the same resolution
    the pointer action addresses and nothing is resampled. This is the standard
    shape for segmentation and pose estimation, which are the same problem:
    which pixel.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


def _conv(in_channels: int, out_channels: int, stride: int = 1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1),
        nn.GroupNorm(8, out_channels),
        nn.ReLU(inplace=True),
    )


class _PointerBase(nn.Module):
    """Shared action-kind head and sampling, so arms differ only in the encoder."""

    def __init__(self, width: int, height: int, features_dim: int):
        super().__init__()
        self.width = width
        self.height = height
        self.kind = nn.Sequential(
            nn.Linear(features_dim, 128), nn.ReLU(inplace=True), nn.Linear(128, 8)
        )

    def _marginals(self, heat: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Reduce a 2D heatmap to the two independent categoricals the action needs.

        logsumexp rather than a mean: it keeps a single confident peak sharp
        instead of averaging it away against the empty board around it.
        """
        if heat.shape[-2:] != (self.height, self.width):
            heat = F.interpolate(
                heat.unsqueeze(1),
                size=(self.height, self.width),
                mode="bilinear",
                align_corners=False,
            ).squeeze(1)
        return torch.logsumexp(heat, dim=1), torch.logsumexp(heat, dim=2)

    @torch.no_grad()
    def act(self, observation, device, deterministic: bool):
        import numpy as np

        obs = torch.as_tensor(observation[None]).to(device).float() / 255.0
        kind_logits, x_logits, y_logits = self(obs)
        if deterministic:
            choice = (kind_logits.argmax(-1), x_logits.argmax(-1), y_logits.argmax(-1))
        else:
            choice = tuple(
                torch.distributions.Categorical(logits=logits).sample()
                for logits in (kind_logits, x_logits, y_logits)
            )
        return np.array([int(value) for value in choice], dtype=np.int64)


class StridedPointer(_PointerBase):
    """Nature-DQN-shaped stack; heatmap read from an intermediate feature map."""

    def __init__(
        self,
        channels: int,
        width: int,
        height: int,
        features_dim: int = 256,
        depth: int = 2,
    ):
        super().__init__(width, height, features_dim)
        self.stack = nn.Sequential(
            nn.Conv2d(channels, 32, 8, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 4, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
        )
        self.depth = depth
        pointer_channels = 32 if depth <= 2 else 64
        self.point = nn.Conv2d(pointer_channels, 1, 1)
        with torch.no_grad():
            flat = (
                self.stack(torch.zeros(1, channels, height, width)).flatten(1).shape[1]
            )
        self.project = nn.Sequential(
            nn.Linear(flat, features_dim), nn.ReLU(inplace=True)
        )

    def forward(self, observations):
        grid = self.stack(observations)
        features = self.project(grid.flatten(1))
        heat = self.point(self.stack[: self.depth](observations)).squeeze(1)
        x_logits, y_logits = self._marginals(heat)
        return self.kind(features), x_logits, y_logits


class UNetPointer(_PointerBase):
    """Context from downsampling, detail restored to full resolution by skips."""

    def __init__(
        self,
        channels: int,
        width: int,
        height: int,
        features_dim: int = 256,
        stem: int = 32,
    ):
        super().__init__(width, height, features_dim)
        # A stride-2 stem keeps the first layer affordable at a 10-frame stack
        # while still costing far less resolution than the stride-4 it replaces.
        self.enc0 = _conv(channels, stem, stride=2)
        self.enc1 = _conv(stem, stem * 2, stride=2)
        self.enc2 = _conv(stem * 2, stem * 4, stride=2)
        self.enc3 = _conv(stem * 4, stem * 4, stride=2)

        self.lat3 = nn.Conv2d(stem * 4, stem * 2, 1)
        self.lat2 = nn.Conv2d(stem * 4, stem * 2, 1)
        self.lat1 = nn.Conv2d(stem * 2, stem * 2, 1)
        self.lat0 = nn.Conv2d(stem, stem * 2, 1)

        self.smooth2 = _conv(stem * 2, stem * 2)
        self.smooth1 = _conv(stem * 2, stem * 2)
        self.smooth0 = _conv(stem * 2, stem * 2)
        self.point = nn.Conv2d(stem * 2, 1, 1)

        self.project = nn.Sequential(
            nn.Linear(stem * 4, features_dim), nn.ReLU(inplace=True)
        )

    @staticmethod
    def _up(source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return F.interpolate(source, size=target.shape[-2:], mode="nearest")

    def forward(self, observations):
        e0 = self.enc0(observations)
        e1 = self.enc1(e0)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)

        # Global context is pooled, not flattened: the kind head wants "what is
        # happening", and pooling keeps it independent of observation size.
        features = self.project(e3.mean(dim=(2, 3)))

        d2 = self.smooth2(self.lat2(e2) + self._up(self.lat3(e3), e2))
        d1 = self.smooth1(self.lat1(e1) + self._up(d2, e1))
        d0 = self.smooth0(self.lat0(e0) + self._up(d1, e0))
        # Back to the exact action grid, so the heatmap is never resampled.
        full = F.interpolate(
            d0, size=(self.height, self.width), mode="bilinear", align_corners=False
        )
        heat = self.point(full).squeeze(1)
        x_logits, y_logits = self._marginals(heat)
        return self.kind(features), x_logits, y_logits


ARCHITECTURES = {"strided": StridedPointer, "unet": UNetPointer}

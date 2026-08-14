"""Compact CNN feature extraction for widescreen Mini Metro observations."""

from __future__ import annotations

from typing import Any

import torch
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn


class MiniMetroCNN(BaseFeaturesExtractor):
    """Downsample widescreen frames, keeping the convolutional grid intact.

    The flattened grid is sized from ``observation_space`` at construction, so a
    finer render profile yields a finer representation. An earlier revision
    pooled to a fixed 3x5 grid, which made every profile collapse to the same 960
    values and left each cell covering 64x60 px -- coarser than the station
    spacing the pointer action has to resolve.
    """

    def __init__(self, observation_space: Any, features_dim: int = 256) -> None:
        if isinstance(features_dim, bool) or not isinstance(features_dim, int):
            raise TypeError("features_dim must be an integer")
        if features_dim <= 0:
            raise ValueError("features_dim must be positive")
        shape = getattr(observation_space, "shape", None)
        if shape is None or len(shape) != 3:
            raise ValueError("MiniMetroCNN requires a channel-first image space")
        channels = int(shape[0])
        if channels <= 0:
            raise ValueError("image space must have at least one channel")

        super().__init__(observation_space, features_dim)
        self.encoder = nn.Sequential(
            nn.Conv2d(channels, 32, kernel_size=8, stride=4, padding=2),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        with torch.no_grad():
            probe = torch.zeros(1, channels, int(shape[1]), int(shape[2]))
            flattened_dim = int(self.encoder(probe).shape[1])
        self.projection = nn.Sequential(
            nn.Linear(flattened_dim, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        return self.projection(self.encoder(observations))

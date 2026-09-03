"""The pixel encoder must resolve position at the scale the game plays at.

A station is roughly ten pixels across and the policy has to point at one with a
per-pixel coordinate action, so an encoder whose representation is unchanged when
a station moves several station-widths cannot support the task no matter how it
is trained. These tests pin that capability rather than any particular layer.
"""

import os
import sys
import unittest
from importlib.util import find_spec

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

if any(find_spec(name) is None for name in ("stable_baselines3", "torch")):
    raise unittest.SkipTest(
        "PyTorch and Stable-Baselines3 are optional; rl.model imports both"
    )

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

from rl.model import MiniMetroCNN

FIDELITY = (180, 320)
STATION_PX = 10


def _frame(height: int, width: int, blob_x: int, blob_y: int) -> torch.Tensor:
    """One channel-first RGB frame holding a single station-sized blob."""
    frame = np.zeros((3, height, width), dtype=np.float32)
    frame[:, blob_y : blob_y + STATION_PX, blob_x : blob_x + STATION_PX] = 1.0
    return torch.from_numpy(frame)[None]


def _relative_change(
    extractor: MiniMetroCNN, a: torch.Tensor, b: torch.Tensor
) -> float:
    with torch.no_grad():
        fa = extractor.encoder(a).ravel()
        fb = extractor.encoder(b).ravel()
    return float(
        torch.linalg.vector_norm(fb - fa) / (torch.linalg.vector_norm(fa) + 1e-9)
    )


class SpatialAcuityTest(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(0)
        height, width = FIDELITY
        space = gym.spaces.Box(low=0, high=255, shape=(3, height, width), dtype="uint8")
        self.extractor = MiniMetroCNN(space, features_dim=256)

    def test_a_station_moving_three_station_widths_changes_the_representation(self):
        """Two boards differing only by one station's position must not encode alike."""
        height, width = FIDELITY
        left = _frame(height, width, blob_x=40, blob_y=90)
        right = _frame(height, width, blob_x=40 + 3 * STATION_PX, blob_y=90)

        change = _relative_change(self.extractor, left, right)

        self.assertGreater(
            change,
            0.10,
            "moving a station three station-widths changed the encoding by only "
            f"{change:.1%}; the encoder cannot distinguish board layouts at the "
            "scale the pointer action addresses",
        )

    def test_added_input_resolution_reaches_the_features(self):
        """A finer render profile must produce a finer representation, not the same one."""
        coarse_space = gym.spaces.Box(
            low=0, high=255, shape=(3, 108, 192), dtype="uint8"
        )
        fine_space = gym.spaces.Box(low=0, high=255, shape=(3, 180, 320), dtype="uint8")
        coarse = MiniMetroCNN(coarse_space, features_dim=256)
        fine = MiniMetroCNN(fine_space, features_dim=256)

        with torch.no_grad():
            coarse_cells = coarse.encoder(_frame(108, 192, 40, 50)).numel()
            fine_cells = fine.encoder(_frame(180, 320, 40, 90)).numel()

        self.assertGreater(
            fine_cells,
            coarse_cells,
            f"fidelity and fast both flatten to {fine_cells} values, so the extra "
            "pixels are discarded before the policy ever sees them",
        )


if __name__ == "__main__":
    unittest.main()

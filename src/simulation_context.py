"""Per-session sources of gameplay randomness."""

from __future__ import annotations

import random

import numpy as np


class SimulationContext:
    """Own independent Python and NumPy random streams for one game session."""

    def __init__(self, seed: int | None = None) -> None:
        seed_sequence = np.random.SeedSequence(seed)
        python_seed_sequence, numpy_seed_sequence = seed_sequence.spawn(2)
        python_seed_words = python_seed_sequence.generate_state(4, dtype=np.uint32)
        python_seed = sum(
            int(word) << (index * 32) for index, word in enumerate(python_seed_words)
        )
        self.python_random = random.Random(python_seed)
        self.numpy_random = np.random.default_rng(numpy_seed_sequence)

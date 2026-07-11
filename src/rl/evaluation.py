"""Policy evaluation that preserves game-level episode metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class EpisodeMetrics:
    reward: float
    length: int
    deliveries: int
    display_score: int
    seed: int | None
    termination_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reward": self.reward,
            "length": self.length,
            "deliveries": self.deliveries,
            "displayScore": self.display_score,
            "seed": self.seed,
            "terminationReason": self.termination_reason,
        }


def evaluate_vector_policy(
    model: Any,
    env: Any,
    *,
    episodes: int,
    deterministic: bool = True,
) -> tuple[EpisodeMetrics, ...]:
    """Evaluate one vectorized environment and retain terminal game metrics."""

    if isinstance(episodes, bool) or not isinstance(episodes, int):
        raise TypeError("episodes must be an integer")
    if episodes <= 0:
        raise ValueError("episodes must be positive")
    if getattr(env, "num_envs", 1) != 1:
        raise ValueError("game-metric evaluation requires exactly one environment")

    observation = env.reset()
    state = None
    episode_starts = np.ones((1,), dtype=bool)
    results: list[EpisodeMetrics] = []
    episode_reward = 0.0
    episode_length = 0
    while len(results) < episodes:
        action, state = model.predict(
            observation,
            state=state,
            episode_start=episode_starts,
            deterministic=deterministic,
        )
        observation, rewards, dones, infos = env.step(action)
        episode_starts = np.asarray(dones, dtype=bool)
        episode_reward += float(rewards[0])
        episode_length += 1
        if not bool(dones[0]):
            continue

        info = infos[0]
        try:
            game_episode = info["game_episode"]
        except KeyError as error:
            raise ValueError("terminal info is missing game_episode metrics") from error
        results.append(
            EpisodeMetrics(
                reward=episode_reward,
                length=episode_length,
                deliveries=int(game_episode["deliveries"]),
                display_score=int(game_episode["display_score"]),
                seed=(
                    int(game_episode["seed"])
                    if game_episode.get("seed") is not None
                    else None
                ),
                termination_reason=info.get("termination_reason"),
            )
        )
        episode_reward = 0.0
        episode_length = 0
    return tuple(results)

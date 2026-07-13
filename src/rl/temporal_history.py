"""Bounded vectorized temporal history for channel-first RGB observations."""

from __future__ import annotations

from typing import Any

import numpy as np
from gymnasium import spaces
from stable_baselines3.common.vec_env import VecEnv, VecEnvWrapper

from rl.history import HistoryDescriptor

__all__ = ("VecTemporalHistory",)


class VecTemporalHistory(VecEnvWrapper):
    """Sample exact decision offsets from one isolated circular ring per slot."""

    def __init__(self, venv: VecEnv, history: HistoryDescriptor) -> None:
        try:
            if not isinstance(history, HistoryDescriptor):
                raise TypeError("history must be a HistoryDescriptor")
            observation_space = venv.observation_space
            if not isinstance(observation_space, spaces.Box):
                raise TypeError("temporal history requires a Box observation space")
            if np.dtype(observation_space.dtype) != np.dtype(np.uint8):
                raise TypeError("temporal history requires uint8 observations")
            if len(observation_space.shape) != 3 or observation_space.shape[0] != 3:
                raise ValueError(
                    "temporal history requires channel-first RGB observations"
                )
            if np.any(observation_space.low > 0) or np.any(observation_space.high < 0):
                raise ValueError("observation bounds must contain zero for pre-history")

            self.history = history
            self._single_shape = tuple(observation_space.shape)
            self._ring_size = max(history.offsets) + 1
            self._ring = np.zeros(
                (venv.num_envs, self._ring_size, *self._single_shape),
                dtype=np.uint8,
            )
            self._write_positions = np.zeros(venv.num_envs, dtype=np.intp)
            self._maximum_valid_ages = np.zeros(venv.num_envs, dtype=np.intp)
            self._initialized = False

            stacked_low = np.concatenate(
                [observation_space.low] * history.frame_stack,
                axis=0,
            )
            stacked_high = np.concatenate(
                [observation_space.high] * history.frame_stack,
                axis=0,
            )
            stacked_space = spaces.Box(
                low=stacked_low,
                high=stacked_high,
                dtype=np.uint8,
            )
            super().__init__(venv, observation_space=stacked_space)
        except BaseException:
            try:
                venv.close()
            except BaseException:
                pass
            raise

    @property
    def history_buffer_nbytes(self) -> int:
        return int(self._ring.nbytes)

    @property
    def maximum_valid_ages(self) -> tuple[int, ...]:
        """Return an immutable per-slot snapshot of retained history ages."""

        return tuple(int(value) for value in self._maximum_valid_ages)

    def reset(self) -> np.ndarray:
        self._poison()
        try:
            observations = self._validate_batch(self.venv.reset(), "reset observations")
            self._ring[:, 0] = observations
            stacked_observations = self._assemble_batch()
        except BaseException:
            self._poison()
            raise
        self._initialized = True
        return stacked_observations

    def step_async(self, actions: np.ndarray) -> None:
        if not self._initialized:
            raise RuntimeError("temporal history must be reset before stepping")
        self.venv.step_async(actions)

    def step_wait(
        self,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
        if not self._initialized:
            raise RuntimeError("temporal history must be reset before stepping")
        try:
            observations, rewards, dones, infos = self.venv.step_wait()
            observations = self._validate_batch(observations, "step observations")
            self._validate_step_metadata(dones, infos)

            terminal_frames: dict[int, np.ndarray] = {}
            for env_index, done in enumerate(dones):
                if not done:
                    continue
                if "terminal_observation" not in infos[env_index]:
                    raise ValueError(
                        f"done slot {env_index} is missing terminal_observation"
                    )
                terminal_frames[env_index] = self._validate_frame(
                    infos[env_index]["terminal_observation"],
                    f"terminal_observation for slot {env_index}",
                )

            for env_index, observation in enumerate(observations):
                if dones[env_index]:
                    self._append(env_index, terminal_frames[env_index])
                    infos[env_index]["terminal_observation"] = self._assemble_slot(
                        env_index
                    )
                    self._reset_slot(env_index, observation)
                else:
                    self._append(env_index, observation)
            stacked_observations = self._assemble_batch()
        except BaseException:
            self._poison()
            raise
        return stacked_observations, rewards, dones, infos

    def _poison(self) -> None:
        self._ring.fill(0)
        self._write_positions.fill(0)
        self._maximum_valid_ages.fill(0)
        self._initialized = False

    def _validate_batch(self, value: Any, name: str) -> np.ndarray:
        if not isinstance(value, np.ndarray):
            raise TypeError(f"{name} must be a NumPy array")
        expected_shape = (self.num_envs, *self._single_shape)
        if value.shape != expected_shape:
            raise ValueError(
                f"{name} shape mismatch: expected={expected_shape}, actual={value.shape}"
            )
        if value.dtype != np.uint8:
            raise TypeError(f"{name} must have dtype uint8")
        return value

    def _validate_frame(self, value: Any, name: str) -> np.ndarray:
        if not isinstance(value, np.ndarray):
            raise TypeError(f"{name} must be a NumPy array")
        if value.shape != self._single_shape:
            raise ValueError(
                f"{name} shape mismatch: "
                f"expected={self._single_shape}, actual={value.shape}"
            )
        if value.dtype != np.uint8:
            raise TypeError(f"{name} must have dtype uint8")
        return value

    def _validate_step_metadata(
        self,
        dones: np.ndarray,
        infos: list[dict[str, Any]],
    ) -> None:
        if not isinstance(dones, np.ndarray) or dones.shape != (self.num_envs,):
            raise ValueError("dones must have one value per vector slot")
        if dones.dtype != np.bool_:
            raise TypeError("dones must have boolean dtype")
        if not isinstance(infos, list) or len(infos) != self.num_envs:
            raise ValueError("infos must have one dictionary per vector slot")
        if any(not isinstance(info, dict) for info in infos):
            raise TypeError("each info must be a dictionary")

    def _append(self, env_index: int, observation: np.ndarray) -> None:
        write_position = (int(self._write_positions[env_index]) + 1) % self._ring_size
        self._write_positions[env_index] = write_position
        self._ring[env_index, write_position] = observation
        self._maximum_valid_ages[env_index] = min(
            int(self._maximum_valid_ages[env_index]) + 1,
            self._ring_size - 1,
        )

    def _reset_slot(self, env_index: int, observation: np.ndarray) -> None:
        self._ring[env_index].fill(0)
        self._write_positions[env_index] = 0
        self._maximum_valid_ages[env_index] = 0
        self._ring[env_index, 0] = observation

    def _assemble_batch(self) -> np.ndarray:
        observations = np.zeros(
            (self.num_envs, *self.observation_space.shape),
            dtype=np.uint8,
        )
        for env_index in range(self.num_envs):
            self._fill_slot(observations[env_index], env_index)
        return observations

    def _assemble_slot(self, env_index: int) -> np.ndarray:
        channels, height, width = self._single_shape
        observation = np.zeros(
            (channels * self.history.frame_stack, height, width),
            dtype=np.uint8,
        )
        self._fill_slot(observation, env_index)
        return observation

    def _fill_slot(self, observation: np.ndarray, env_index: int) -> None:
        channels = self._single_shape[0]
        maximum_valid_age = int(self._maximum_valid_ages[env_index])
        write_position = int(self._write_positions[env_index])
        for sample_index, offset in enumerate(self.history.offsets):
            if offset > maximum_valid_age:
                continue
            ring_index = (write_position - offset) % self._ring_size
            start = sample_index * channels
            observation[start : start + channels] = self._ring[env_index, ring_index]

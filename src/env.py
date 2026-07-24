from typing import Any, Dict, Tuple

import numpy as np

from mediator import Mediator

DELIVERIES_REWARD_MODE = "deliveries"
LINE_CREDITS_DELTA_REWARD_MODE = "line_credits_delta"
_REWARD_MODES = (DELIVERIES_REWARD_MODE, LINE_CREDITS_DELTA_REWARD_MODE)


class MiniMetroEnv:
    def __init__(
        self,
        dt_ms: int | None = None,
        *,
        reward_mode: str = DELIVERIES_REWARD_MODE,
    ) -> None:
        self.dt_ms_default = dt_ms
        self.reward_mode = reward_mode
        self.mediator = Mediator()
        self.last_deliveries = self.mediator.deliveries
        self.last_line_credits = self.mediator.line_credits

    @property
    def reward_mode(self) -> str:
        return self._reward_mode

    @reward_mode.setter
    def reward_mode(self, value: str) -> None:
        if value not in _REWARD_MODES:
            choices = ", ".join(_REWARD_MODES)
            raise ValueError(f"reward_mode must be one of: {choices}")
        self._reward_mode = value

    @property
    def last_score(self) -> int:
        """Deprecated writable alias for the line-credit reward baseline."""

        return self.last_line_credits

    @last_score.setter
    def last_score(self, value: int) -> None:
        self.last_line_credits = value

    def reset(self, seed: int | None = None) -> Dict[str, Any]:
        retired: list[Any] = []
        seen: set[int] = set()
        old_mediator = getattr(self, "mediator", None)
        old_metros = list(getattr(old_mediator, "metros", ()))
        for path in getattr(old_mediator, "paths", ()):
            old_metros.extend(getattr(path, "metros", ()))
        for metro in old_metros:
            if id(metro) in seen:
                continue
            seen.add(id(metro))
            retired.append(metro)
        for metro in retired:
            metro._station_service_action = None
            metro.stop_time_remaining_ms = 0
            metro.boarding_progress_ms = 0
        self.mediator = Mediator(seed=seed)
        self.last_deliveries = self.mediator.deliveries
        self.last_line_credits = self.mediator.line_credits
        return self.observe()

    def _reward_delta(self) -> int:
        deliveries_delta = self.mediator.deliveries - self.last_deliveries
        line_credits_delta = self.mediator.line_credits - self.last_line_credits
        self.last_deliveries = self.mediator.deliveries
        self.last_line_credits = self.mediator.line_credits
        if self.reward_mode == DELIVERIES_REWARD_MODE:
            return deliveries_delta
        if self.reward_mode == LINE_CREDITS_DELTA_REWARD_MODE:
            return line_credits_delta
        raise RuntimeError(f"unsupported reward mode: {self.reward_mode!r}")

    def step(
        self, action: Dict[str, Any] | None = None, dt_ms: int | None = None
    ) -> Tuple[Dict[str, Any], int, bool, Dict[str, Any]]:
        if self.mediator.is_game_over:
            obs = self.observe()
            reward = self._reward_delta()
            return obs, reward, True, {"action_ok": False}

        if action is None:
            action = {"type": "noop"}
        action_ok = self.mediator.apply_action(action)

        return self._complete_step(action_ok, dt_ms)

    def step_legacy_auto_assignment(
        self, action: Dict[str, Any] | None = None, dt_ms: int | None = None
    ) -> Tuple[Dict[str, Any], int, bool, Dict[str, Any]]:
        """Reproduce the pre-explicit-fleet create-and-assign transition."""

        if self.mediator.is_game_over:
            return self.step(action, dt_ms=dt_ms)
        if type(action) is not dict or action.get("type") != "create_path":
            return self.step(action, dt_ms=dt_ms)

        had_capacity = len(self.mediator.metros) < self.mediator.num_metros
        existing_paths = tuple(self.mediator.paths)
        action_ok = self.mediator.apply_action(action)
        if action_ok and had_capacity:
            new_paths = [
                path
                for path in self.mediator.paths
                if all(path is not existing for existing in existing_paths)
            ]
            if len(new_paths) != 1:
                raise RuntimeError(
                    "legacy create_path did not append exactly one active path"
                )
            if not self.mediator.assign_locomotive(new_paths[0]):
                raise RuntimeError("legacy create_path locomotive assignment failed")

        return self._complete_step(action_ok, dt_ms)

    def _complete_step(
        self, action_ok: bool, dt_ms: int | None
    ) -> Tuple[Dict[str, Any], int, bool, Dict[str, Any]]:
        if dt_ms is None:
            dt_ms = self.dt_ms_default
        if action_ok and dt_ms is not None:
            self.mediator.step_time(dt_ms)

        obs = self.observe()
        reward = self._reward_delta()
        done = self.mediator.is_game_over
        info = {"action_ok": action_ok}
        return obs, reward, done, info

    def observe(self) -> Dict[str, Any]:
        station_id_to_index = {
            station.id: idx for idx, station in enumerate(self.mediator.stations)
        }
        path_id_to_index = {
            path.id: idx for idx, path in enumerate(self.mediator.paths)
        }
        metro_id_to_index = {
            metro.id: idx for idx, metro in enumerate(self.mediator.metros)
        }
        passenger_id_to_index = {
            passenger.id: idx for idx, passenger in enumerate(self.mediator.passengers)
        }
        metro_queue_states: Dict[int, bool] = {}
        for metro in self.mediator.metros:
            queue_state = getattr(metro, "is_unassignment_queued", None)
            if type(queue_state) is not bool:
                raise ValueError("metro unassignment queue state must be boolean")
            metro_queue_states[id(metro)] = queue_state

        passenger_locations: Dict[str, Tuple[str, str] | None] = {
            passenger.id: None for passenger in self.mediator.passengers
        }
        for station in self.mediator.stations:
            for passenger in station.passengers:
                passenger_locations[passenger.id] = ("station", station.id)
        for metro in self.mediator.metros:
            for passenger in metro.passengers:
                passenger_locations[passenger.id] = ("metro", metro.id)

        structured = {
            "stations": [
                {
                    "id": station.id,
                    "position": (station.position.left, station.position.top),
                    "shape_type": station.shape.type,
                    "passenger_ids": [p.id for p in station.passengers],
                    "passenger_count": len(station.passengers),
                }
                for station in self.mediator.stations
            ],
            "paths": [
                {
                    "id": path.id,
                    "station_ids": [s.id for s in path.stations],
                    "is_looped": path.is_looped,
                    "color": path.color,
                }
                for path in self.mediator.paths
            ],
            "metros": [
                {
                    "id": metro.id,
                    "path_id": metro.path_id,
                    "position": (
                        (metro.position.left, metro.position.top)
                        if metro.position is not None
                        else None
                    ),
                    "current_station_id": (
                        metro.current_station.id if metro.current_station else None
                    ),
                    "passenger_ids": [p.id for p in metro.passengers],
                    "unassignment_queued": metro_queue_states[id(metro)],
                    "capacity": metro.capacity,
                    "carriage_ids": [carriage.id for carriage in metro.carriages],
                }
                for metro in self.mediator.metros
            ],
            "carriages": [
                {
                    "id": carriage.id,
                    "capacity": carriage.capacity,
                    "metro_id": metro.id,
                    "attachment_index": attachment_index,
                }
                for metro in self.mediator.metros
                for attachment_index, carriage in enumerate(metro.carriages)
            ],
            "passengers": [
                {
                    "id": passenger.id,
                    "destination_shape_type": passenger.destination_shape.type,
                    "is_at_destination": passenger.is_at_destination,
                    "location": passenger_locations[passenger.id],
                }
                for passenger in self.mediator.passengers
            ],
            "fleet": {
                "locomotives_total": self.mediator.num_metros,
                "locomotives_assigned": len(self.mediator.metros),
                "locomotives_available": self.mediator.available_locomotives,
                "locomotives_queued": sum(metro_queue_states.values()),
                "carriages_total": self.mediator.num_carriages,
                "carriages_assigned": self.mediator.assigned_carriages,
                "carriages_available": self.mediator.available_carriages,
            },
            # GM-09c: a SIBLING of "fleet" (never inside it), so the checkpoint's
            # exact fleet-key whitelist is untouched and _normalize_observation
            # ignores this block; None on an unbounded map (CLASSIC).
            "tunnels": {
                "total": self.mediator.num_tunnels,
                "consumed": self.mediator.consumed_tunnels,
                "available": self.mediator.available_tunnels,
            },
            "deliveries": self.mediator.deliveries,
            "line_credits": self.mediator.line_credits,
            "score": self.mediator.score,
            "time_ms": self.mediator.time_ms,
            "steps": self.mediator.steps,
            "is_paused": self.mediator.is_paused,
            "is_game_over": self.mediator.is_game_over,
            "index": {
                "station_id_to_index": station_id_to_index,
                "path_id_to_index": path_id_to_index,
                "metro_id_to_index": metro_id_to_index,
                "passenger_id_to_index": passenger_id_to_index,
            },
        }

        arrays = self._encode_numpy(
            station_id_to_index,
            path_id_to_index,
            metro_id_to_index,
            passenger_id_to_index,
        )

        return {"structured": structured, "arrays": arrays}

    def _encode_numpy(
        self,
        station_id_to_index: Dict[str, int],
        path_id_to_index: Dict[str, int],
        metro_id_to_index: Dict[str, int],
        passenger_id_to_index: Dict[str, int],
    ) -> Dict[str, Any]:
        station_positions = np.array(
            [
                [station.position.left, station.position.top]
                for station in self.mediator.stations
            ],
            dtype=np.float32,
        )
        station_shape_types = np.array(
            [int(station.shape.type.value) for station in self.mediator.stations],
            dtype=np.int64,
        )
        station_passenger_counts = np.array(
            [len(station.passengers) for station in self.mediator.stations],
            dtype=np.int64,
        )
        path_station_indices = [
            np.array([station_id_to_index[s.id] for s in path.stations], dtype=np.int64)
            for path in self.mediator.paths
        ]
        path_is_looped = np.array(
            [int(path.is_looped) for path in self.mediator.paths], dtype=np.int64
        )

        metro_positions_list = [
            [metro.position.left, metro.position.top]
            if metro.position is not None
            else [-1, -1]
            for metro in self.mediator.metros
        ]
        if metro_positions_list:
            metro_positions = np.array(metro_positions_list, dtype=np.float32)
        else:
            metro_positions = np.zeros((0, 2), dtype=np.float32)
        metro_path_indices = np.array(
            [path_id_to_index.get(metro.path_id, -1) for metro in self.mediator.metros],
            dtype=np.int64,
        )

        passenger_destination_types = np.array(
            [
                int(passenger.destination_shape.type.value)
                for passenger in self.mediator.passengers
            ],
            dtype=np.int64,
        )
        passenger_station_indices = np.full(
            (len(self.mediator.passengers),), -1, dtype=np.int64
        )
        passenger_metro_indices = np.full(
            (len(self.mediator.passengers),), -1, dtype=np.int64
        )

        for station in self.mediator.stations:
            for passenger in station.passengers:
                idx = passenger_id_to_index.get(passenger.id)
                if idx is not None:
                    passenger_station_indices[idx] = station_id_to_index[station.id]
        for metro in self.mediator.metros:
            for passenger in metro.passengers:
                idx = passenger_id_to_index.get(passenger.id)
                if idx is not None:
                    passenger_metro_indices[idx] = metro_id_to_index[metro.id]

        return {
            "station_positions": station_positions,
            "station_shape_types": station_shape_types,
            "station_passenger_counts": station_passenger_counts,
            "path_station_indices": path_station_indices,
            "path_is_looped": path_is_looped,
            "metro_positions": metro_positions,
            "metro_path_indices": metro_path_indices,
            "passenger_destination_types": passenger_destination_types,
            "passenger_station_indices": passenger_station_indices,
            "passenger_metro_indices": passenger_metro_indices,
        }


def legacy_auto_assignment_step(
    env: MiniMetroEnv,
    action: Dict[str, Any] | None = None,
    dt_ms: int | None = None,
) -> Tuple[Dict[str, Any], int, bool, Dict[str, Any]]:
    """Run one historical transition without duplicating driver-side semantics."""

    if type(action) is dict and action.get("type") == "create_path":
        method = getattr(env, "step_legacy_auto_assignment", None)
        if method is None:
            raise ValueError(
                "legacy create_path replay requires explicit assignment support"
            )
        return method(action, dt_ms=dt_ms)
    return env.step(action, dt_ms=dt_ms)

import random
from typing import Any, Dict, List, Tuple

import numpy as np

from mediator import Mediator


class MiniMetroEnv:
    def __init__(self, dt_ms: int | None = None) -> None:
        self.dt_ms_default = dt_ms
        self.mediator = Mediator()
        self.last_score = self.mediator.score

    def reset(self, seed: int | None = None) -> Dict[str, Any]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        self.mediator = Mediator()
        self.last_score = self.mediator.score
        return self.observe()

    def step(
        self, action: Dict[str, Any] | None = None, dt_ms: int | None = None
    ) -> Tuple[Dict[str, Any], int, bool, Dict[str, Any]]:
        if action is None:
            action = {"type": "noop"}
        action_ok = self.mediator.apply_action(action)

        if dt_ms is None:
            dt_ms = self.dt_ms_default
        if dt_ms is not None:
            self.mediator.step_time(dt_ms)

        obs = self.observe()
        reward = self.mediator.score - self.last_score
        self.last_score = self.mediator.score
        done = False
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
                }
                for metro in self.mediator.metros
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
            "score": self.mediator.score,
            "time_ms": self.mediator.time_ms,
            "steps": self.mediator.steps,
            "is_paused": self.mediator.is_paused,
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
            np.array(
                [station_id_to_index[s.id] for s in path.stations], dtype=np.int64
            )
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
            [
                path_id_to_index.get(metro.path_id, -1)
                for metro in self.mediator.metros
            ],
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

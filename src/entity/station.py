from __future__ import annotations

import pygame
import random
from shortuuid import uuid  # type: ignore

from config import (
    station_capacity,
    station_passengers_per_row,
    station_size,
    passenger_spawning_interval_step,
    gamespeed,
    passenger_patience
)
from entity.holder import Holder
from geometry.point import Point
from geometry.shape import Shape


class Station(Holder):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            capacity=station_capacity,
            id=f"Station-{uuid()}-{shape.type}",
        )
        self.size = station_size
        self.position = position
        self.passengers_per_row = station_passengers_per_row

        self.steps = 0
        self.next_passenger_spawn_time = self.get_poisson_time()

    def __eq__(self, other: Station) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
    
    def get_poisson_time(self) -> int:
        return int(random.expovariate(1 / passenger_spawning_interval_step))

    def need_spawn_passenger(self) -> bool:
        if self.steps >= self.next_passenger_spawn_time:
            self.next_passenger_spawn_time += self.get_poisson_time()
            return True

        return False

    def update_passenger_wait_time(self) -> None:
        for passenger in self.passengers:
            if not passenger.is_at_destination:
                passenger.wait_timesteps += gamespeed

                if passenger.wait_timesteps >= passenger_patience:
                    raise Exception(
                        f"{passenger} has waited too long, gameover!"
                    )

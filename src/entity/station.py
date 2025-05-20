from __future__ import annotations
from math import cos, pi, sin

import pygame
from random import Random
from shortuuid import uuid  # type: ignore

from config import station_capacity, station_passengers_per_row, station_size, passenger_spawning_interval_step, station_full_timeout
from entity.holder import Holder
from geometry.point import Point
from geometry.shape import Shape


class Station(Holder):
    def __init__(self, rng: Random, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            capacity=station_capacity,
            id=f"Station-{uuid()}-{shape.type}",
        )
        self.rng = rng
        self.size = station_size
        self.position = position
        self.passengers_per_row = station_passengers_per_row

        self.steps = 0
        self.next_passenger_spawn_time = self.get_poisson_time()
        self.full_duration = 0
        self.full_timeout = station_full_timeout * 1000 # in ms
    
    def reset_progress(self, rng: Random) -> None:
        self.rng = rng
        self.steps = 0
        self.passengers = []
        self.next_passenger_spawn_time = self.get_poisson_time()
        self.full_duration = 0

        # self.full_timeout = station_full_timeout * 1000 # in ms // wont be altered, no need to reset
    
    def check_timeout(self, time_ms: int) -> bool:
        if len(self.passengers) < self.capacity:
            self.full_duration = 0
            return False
        self.full_duration += time_ms
        if self.full_duration > self.full_timeout:
            return True
        return False
    
    def is_full(self):
        return len(self.passengers) == self.capacity

    def __eq__(self, other: Station) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
    
    def get_poisson_time(self) -> int:
        return int(self.rng.expovariate(1 / passenger_spawning_interval_step))

    def need_spawn_passenger(self) -> bool:
        if self.steps >= self.next_passenger_spawn_time:
            self.next_passenger_spawn_time += self.get_poisson_time()
            return True

        return False
    
    @property
    def timeout_ratio(self) -> float:
        return self.full_duration / self.full_timeout

    def draw(self, surface):
        if self.is_full():
            if self.timeout_ratio > 0:
                points = [self.position.to_tuple()]
                radius = self.size * (1.5 + self.timeout_ratio * 1.5)
                deg = 0
                while deg <= max(self.timeout_ratio * 2 * pi, 0.05):
                    points.append((self.position.left + radius * cos(deg), self.position.top + radius * sin(deg)))
                    deg += 0.01
                pygame.draw.polygon(surface, (150, 150, 150), points)
        return super().draw(surface)
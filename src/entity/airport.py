from __future__ import annotations

import pygame
from shortuuid import uuid  # type: ignore

from config import airport_capacity, airport_passengers_per_row, airport_size
from entity.holder import Holder
from geometry.point import Point
from geometry.shape import Shape


class Airport(Holder):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            capacity=airport_capacity,
            id=f"Airport-{uuid()}-{shape.type}",
        )
        self.size = airport_size
        self.position = position
        self.passengers_per_row = airport_passengers_per_row
        self.overcrowd_start_time = 0
        self.is_overcrowded = False

    def __eq__(self, other: Airport) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

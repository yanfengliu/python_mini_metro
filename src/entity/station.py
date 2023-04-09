from __future__ import annotations

import pygame
from shortuuid import uuid  # type: ignore

from config import station_capacity, station_passengers_per_row, station_size
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

    def __eq__(self, other: Station) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

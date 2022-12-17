from __future__ import annotations

from uuid import uuid4

import pygame

from config import station_capacity
from entity.holder import Holder
from geometry.point import Point
from geometry.shape import Shape


class Station(Holder):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            capacity=station_capacity,
            id=f"Station-{uuid4()}",
        )
        self.position = position

    def __eq__(self, other: Station) -> bool:
        return self.id == other.id

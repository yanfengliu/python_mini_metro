from __future__ import annotations

import uuid

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
            id=f"S-{uuid.uuid4()}",
        )
        self.position = position

    def __eq__(self, other: Station) -> bool:
        return self.id == other.id

    def draw(self, surface: pygame.surface.Surface):
        self.shape.draw(surface, self.position)

from abc import ABC

import pygame

from geometry.point import Point
from geometry.shape import Shape


class Holder(ABC):
    def __init__(self, shape: Shape, capacity: int, id: str) -> None:
        self.shape = shape
        self.capacity = capacity
        self.id = id

    def __repr__(self) -> str:
        return self.id

    def draw(self, surface: pygame.Surface):
        self.shape.draw(surface, self.position)

    def contains(self, point: Point):
        return self.shape.contains(point)

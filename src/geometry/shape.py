from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import uuid4

import pygame

from geometry.point import Point
from geometry.type import ShapeType


class Shape(ABC):
    def __init__(self, type: ShapeType):
        self.type = type
        self.id = f"Shape-{uuid4()}"

    def __eq__(self, other: Shape) -> bool:
        return self.id == other.id

    @abstractmethod
    def draw(self, surface: pygame.surface.Surface, position: Point) -> None:
        self.position = position

    @abstractmethod
    def contains(self, point: Point) -> bool:
        pass

    def rotate(self, degree):
        pass

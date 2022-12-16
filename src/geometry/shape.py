from abc import ABC, abstractmethod

import pygame

from geometry.point import Point
from geometry.type import ShapeType


class Shape(ABC):
    def __init__(self, type: ShapeType):
        self.type = type

    @abstractmethod
    def draw(self, surface: pygame.surface.Surface, position: Point):
        self.position = position

    @abstractmethod
    def contains(self, point: Point) -> bool:
        pass

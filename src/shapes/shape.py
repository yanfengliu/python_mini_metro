from abc import ABC, abstractmethod

import pygame

from shapes.type import ShapeType
from type import Point


class Shape(ABC):
    def __init__(self, type: ShapeType):
        self.type = type

    @abstractmethod
    def draw(self, surface: pygame.Surface, position: Point):
        pass

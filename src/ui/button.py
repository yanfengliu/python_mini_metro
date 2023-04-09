from abc import ABC, abstractmethod

import pygame

from geometry.point import Point
from geometry.shape import Shape


class Button(ABC):
    def __init__(self, shape: Shape) -> None:
        super().__init__()
        self.shape = shape
        self.position: Point

    def draw(self, surface: pygame.surface.Surface) -> None:
        self.shape.draw(surface, self.position)

    def contains(self, point: Point) -> bool:
        return self.shape.contains(point)

    @abstractmethod
    def on_hover(self):
        pass

    @abstractmethod
    def on_exit(self):
        pass

    @abstractmethod
    def on_click(self):
        pass

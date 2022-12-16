import pygame

from geometry.point import Point
from geometry.shape import Shape
from geometry.type import ShapeType
from type import Color


class Rect(Shape):
    def __init__(self, color: Color, width: int, height: int) -> None:
        super().__init__(ShapeType.RECT)
        self.color = color
        self.width = width
        self.height = height

    def draw(self, surface: pygame.surface.Surface, position: Point):
        super().draw(surface, position)
        left = position.left
        top = position.top
        width = self.width
        height = self.height
        rect = pygame.Rect(left, top, width, height)
        return pygame.draw.rect(surface, self.color, rect)

    def contains(self, point: Point) -> bool:
        return (
            self.position.left < point.left < (self.position.left + self.width)
        ) and (self.position.top < point.top < self.position.top + self.height)

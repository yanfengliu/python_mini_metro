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

    def draw(self, surface: pygame.surface.Surface, position: Point) -> None:
        super().draw(surface, position)
        left = position.left
        top = position.top
        width = self.width
        height = self.height
        rect = pygame.Rect(
            int(left - width * 0.5), int(top - height * 0.5), width, height
        )
        pygame.draw.rect(surface, self.color, rect)

    def contains(self, point: Point) -> bool:
        return (
            int(self.position.left - self.width * 0.5)
            < point.left
            < int(self.position.left + self.width * 0.5)
        ) and (
            int(self.position.top - self.height * 0.5)
            < point.top
            < int(self.position.top + self.height * 0.5)
        )

import pygame
from shortuuid import uuid  # type: ignore

from geometry.point import Point
from geometry.shape import Shape
from geometry.type import ShapeType
from type import Color


class Circle(Shape):
    def __init__(self, color: Color, radius: int) -> None:
        super().__init__(ShapeType.CIRCLE, color)
        self.id = f"Circle-{uuid()}"
        self.radius = radius

    def draw(self, surface: pygame.surface.Surface, position: Point):
        super().draw(surface, position)
        center = (position.left, position.top)
        radius = self.radius
        return pygame.draw.circle(surface, self.color, center, radius)

    def contains(self, point: Point) -> bool:
        return (point.left - self.position.left) ** 2 + (
            point.top - self.position.top
        ) ** 2 <= self.radius**2

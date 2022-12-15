import pygame

from shapes.shape import Shape
from shapes.type import ShapeType
from type import Color, Point


class Circle(Shape):
    def __init__(self, color: Color, radius: int) -> None:
        super().__init__(ShapeType.CIRCLE)
        self.color = color
        self.radius = radius

    def draw(self, surface: pygame.Surface, position: Point):
        center = (position["left"], position["top"])
        radius = self.radius
        return pygame.draw.circle(surface, self.color, center, radius)

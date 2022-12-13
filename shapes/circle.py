from shapes.shape import Shape
from shapes.types import ShapeType
import pygame


class Circle(Shape):
    def __init__(self, color, radius) -> None:
        self.type = ShapeType.CIRCLE
        self.color = color
        self.radius = radius

    def draw(self, surface, position):
        center = (position["left"], position["top"])
        radius = self.radius
        return pygame.draw.circle(surface, self.color, center, radius)

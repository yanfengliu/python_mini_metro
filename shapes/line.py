from shapes.shape import Shape
from shapes.types import ShapeType
import pygame


class Line(Shape):
    def __init__(self, color, start, end, width) -> None:
        self.type = ShapeType.CIRCLE
        self.color = color
        self.start = start
        self.end = end
        self.width = width

    def draw(self, surface):
        return pygame.draw.line(surface, self.color, self.start, self.end, self.width)

import pygame

from shapes.shape import Shape
from shapes.type import ShapeType
from type import Color, Point


class Line(Shape):
    def __init__(
        self, color: Color, start: Point, end: Point, width: int
    ) -> None:
        super().__init__(ShapeType.LINE)
        self.color = color
        self.start = start
        self.end = end
        self.width = width

    def draw(self, surface: pygame.Surface):
        return pygame.draw.line(surface, self.color, self.start, self.end, self.width)

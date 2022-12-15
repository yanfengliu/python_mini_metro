import pygame

from shapes.shape import Shape
from shapes.type import ShapeType
from type import Color, Point


class Rect(Shape):
    def __init__(self, color: Color, width: int, height: int) -> None:
        self.type = ShapeType.RECT
        self.color = color
        self.width = width
        self.height = height

    def draw(self, surface: pygame.Surface, position: Point):
        left = position["left"]
        top = position["top"]
        width = self.width
        height = self.height
        rect = pygame.Rect(left, top, width, height)
        return pygame.draw.rect(surface, self.color, rect)

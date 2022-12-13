from shapes.shape import Shape
from shapes.types import ShapeType
import pygame


class Rect(Shape):
    def __init__(self, color, width, height) -> None:
        self.type = ShapeType.RECT
        self.color = color
        self.width = width
        self.height = height

    def draw(self, surface, position):
        left = position["left"]
        top = position["top"]
        width = self.width
        height = self.height
        rect = pygame.Rect(left, top, width, height)
        return pygame.draw.rect(surface, self.color, rect)

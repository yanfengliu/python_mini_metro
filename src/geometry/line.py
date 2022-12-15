import pygame

from type import Color, Point


class Line:
    def __init__(self, color: Color, start: Point, end: Point, width: int) -> None:
        self.color = color
        self.start = start
        self.end = end
        self.width = width

    def draw(self, surface: pygame.Surface):
        return pygame.draw.line(surface, self.color, self.start, self.end, self.width)
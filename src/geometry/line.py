from __future__ import annotations

import pygame
from shortuuid import uuid  # type: ignore

from geometry.point import Point
from type import Color


class Line:
    def __init__(self, color: Color, start: Point, end: Point, width: int) -> None:
        self.id = f"Line-{uuid()}"
        self.color = color
        self.start = start
        self.end = end
        self.width = width

    def __eq__(self, other: Line):
        return self.id == other.id

    def draw(self, surface: pygame.surface.Surface):
        return pygame.draw.line(
            surface, self.color, self.start.to_tuple(), self.end.to_tuple(), self.width
        )

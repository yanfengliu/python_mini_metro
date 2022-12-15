from typing import List

import pygame

from shapes.shape import Shape
from shapes.type import ShapeType
from type import Color, Point


class Polygon(Shape):
    def __init__(self, color: Color, points: List[Point]) -> None:
        super().__init__(ShapeType.POLYGON)
        self.color = color
        self.points = points

    def draw(self, surface, position):
        points = self.points
        for i in range(len(points)):
            points[i][0] += position[0]
            points[i][1] += position[1]

        return pygame.draw.circle(surface, self.color, points)

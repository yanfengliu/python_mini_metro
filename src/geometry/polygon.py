from typing import List

import pygame
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.polygon import Polygon as ShapelyPolygon

from geometry.point import Point
from geometry.shape import Shape
from geometry.type import ShapeType
from type import Color


class Polygon(Shape):
    def __init__(self, color: Color, points: List[Point]) -> None:
        super().__init__(ShapeType.POLYGON)
        self.color = color
        self.points = points

    def draw(self, surface: pygame.surface.Surface, position: Point):
        super().draw(surface, position)
        points = self.points
        for i in range(len(points)):
            points[i].left += position.left
            points[i].top += position.top

        return pygame.draw.polygon(surface, self.color, points)

    def contains(self, point: Point):
        point = ShapelyPoint(point.left, point.top)
        points = [(x.left, x.top) for x in self.points]
        polygon = ShapelyPolygon(points)
        return polygon.contains(point)

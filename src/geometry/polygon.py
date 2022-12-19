from typing import List

import pygame  # type: ignore
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.polygon import Polygon as ShapelyPolygon
from shortuuid import uuid  # type: ignore

from geometry.point import Point
from geometry.shape import Shape
from geometry.type import ShapeType
from type import Color


class Polygon(Shape):
    def __init__(self, color: Color, points: List[Point]) -> None:
        super().__init__(ShapeType.POLYGON)
        self.id = f"Polygon-{uuid()}"
        self.color = color
        self.points = points

    def draw(self, surface: pygame.surface.Surface, position: Point) -> None:
        super().draw(surface, position)
        tuples = []
        for i in range(len(self.points)):
            tuples.append((self.points[i] + self.position).to_tuple())
        pygame.draw.polygon(surface, self.color, tuples)

    def contains(self, point: Point) -> bool:
        shapely_point = ShapelyPoint(point.left, point.top)
        tuples = [(x + self.position).to_tuple() for x in self.points]
        polygon = ShapelyPolygon(tuples)
        return polygon.contains(shapely_point)

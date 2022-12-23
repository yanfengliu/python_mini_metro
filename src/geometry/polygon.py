import math
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
    def __init__(
        self, shape_type: ShapeType, color: Color, points: List[Point]
    ) -> None:
        super().__init__(shape_type, color)
        self.id = f"Polygon-{uuid()}"
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

    def rotate(self, degree: float) -> None:
        radians = math.radians(degree)
        s = math.sin(radians)
        c = math.cos(radians)

        for i in range(len(self.points)):
            x = self.points[i].left
            y = self.points[i].top
            self.points[i] = Point(
                round(c * x - s * y),
                round(s * x + c * y),
            )

import math
from typing import List

import pygame
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
        self.degrees: float = 0

    def draw(
        self,
        surface: pygame.surface.Surface,
        position: Point | tuple[float, float],
        rotation_degrees: float | None = None,
    ) -> None:
        center_x, center_y = (
            position if isinstance(position, tuple) else position.to_tuple()
        )
        degrees = self.degrees if rotation_degrees is None else rotation_degrees
        radians = math.radians(degrees)
        sine = math.sin(radians)
        cosine = math.cos(radians)
        tuples: list[tuple[float, float]] = []
        for point in self.points:
            rotated_x = round(cosine * point.left - sine * point.top)
            rotated_y = round(sine * point.left + cosine * point.top)
            tuples.append((rotated_x + center_x, rotated_y + center_y))
        pygame.draw.polygon(surface, self.color, tuples)

    def contains(self, point: Point) -> bool:
        shapely_point = ShapelyPoint(point.left, point.top)
        tuples = [(x + self.position).to_tuple() for x in self.points]
        polygon = ShapelyPolygon(tuples)
        return polygon.contains(shapely_point)

    def set_degrees(self, degrees: float):
        self.degrees = degrees

    def rotate(self, degree_diff: float) -> None:
        self.degrees += degree_diff

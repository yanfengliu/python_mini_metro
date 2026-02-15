import math

from geometry.point import Point
from geometry.polygon import Polygon
from geometry.type import ShapeType
from type import Color


class Star(Polygon):
    def __init__(self, color: Color, size: int) -> None:
        points = []
        inner_radius = round(size * 0.45)
        for idx in range(10):
            angle = math.radians(-90 + idx * 36)
            radius = size if idx % 2 == 0 else inner_radius
            points.append(
                Point(
                    round(radius * math.cos(angle)),
                    round(radius * math.sin(angle)),
                )
            )
        super().__init__(ShapeType.STAR, color, points)

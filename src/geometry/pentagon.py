import math

from geometry.point import Point
from geometry.polygon import Polygon
from geometry.type import ShapeType
from type import Color


class Pentagon(Polygon):
    def __init__(self, color: Color, size: int) -> None:
        points = []
        for idx in range(5):
            angle = math.radians(-90 + idx * 72)
            points.append(
                Point(
                    round(size * math.cos(angle)),
                    round(size * math.sin(angle)),
                )
            )
        super().__init__(ShapeType.PENTAGON, color, points)

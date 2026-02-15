from geometry.point import Point
from geometry.polygon import Polygon
from geometry.type import ShapeType
from type import Color


class Diamond(Polygon):
    def __init__(self, color: Color, size: int) -> None:
        points = [
            Point(0, -size),
            Point(size, 0),
            Point(0, size),
            Point(-size, 0),
        ]
        super().__init__(ShapeType.DIAMOND, color, points)

from geometry.point import Point
from geometry.polygon import Polygon
from geometry.type import ShapeType
from type import Color


class Cross(Polygon):
    def __init__(self, color: Color, size: int, width: int = 0) -> None:
        self.size = size
        if width == 0:
            self.width = round(2 * size / 3)
        else:
            self.width = width
        W = self.width
        L = round(0.5 * (2 * size - W))
        points = [
            Point(L, 0),
            Point(L + W, 0),
            Point(L + W, L),
            Point(2 * L + W, L),
            Point(2 * L + W, L + W),
            Point(L + W, L + W),
            Point(L + W, 2 * L + W),
            Point(L, 2 * L + W),
            Point(L, L + W),
            Point(0, L + W),
            Point(0, L),
            Point(L, L),
        ]
        for i in range(len(points)):
            points[i] += Point(-size, -size)
        super().__init__(ShapeType.CROSS, color, points)

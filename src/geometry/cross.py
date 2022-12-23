from geometry.point import Point
from geometry.polygon import Polygon
from geometry.type import ShapeType
from type import Color


class Cross(Polygon):
    def __init__(self, color: Color, size: int) -> None:
        self.size = size
        side = round(2 * size / 3)
        points = [
            Point(side, 0),
            Point(2 * side, 0),
            Point(2 * side, side),
            Point(3 * side, side),
            Point(3 * side, 2 * side),
            Point(2 * side, 2 * side),
            Point(2 * side, 3 * side),
            Point(side, 3 * side),
            Point(side, 2 * side),
            Point(0, 2 * side),
            Point(0, side),
            Point(side, side),
        ]
        for i in range(len(points)):
            points[i] += Point(-size, -size)
        super().__init__(ShapeType.CROSS, color, points)

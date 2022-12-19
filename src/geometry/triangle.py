from geometry.point import Point
from geometry.polygon import Polygon
from geometry.type import ShapeType
from type import Color


class Triangle(Polygon):
    def __init__(self, color: Color, size: int) -> None:
        # Equilateral triangle
        self.size = size
        points = [
            Point(-size, int(-0.866 * size)),
            Point(size, int(-0.866 * size)),
            Point(0, int(0.866 * size)),
        ]
        super().__init__(color, points)
        self.type = ShapeType.TRIANGLE

from shapes.shape import Shape
from shapes.types import ShapeType
import pygame


class Polygon(Shape):
    def __init__(self, color, points) -> None:
        self.type = ShapeType.POLYGON
        self.color = color
        self.points = points

    def draw(self, surface, position):
        points = self.points
        for i in range(len(points)):
            points[i][0] += position[0]
            points[i][1] += position[1]

        return pygame.draw.circle(surface, self.color, points)

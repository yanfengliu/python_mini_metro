import pygame
from shortuuid import uuid  # type: ignore

from geometry.point import Point
from geometry.polygon import Polygon
from geometry.shape import Shape
from geometry.type import ShapeType
from type import Color


class Rect(Polygon):
    def __init__(self, color: Color, width: int, height: int) -> None:
        points = [
            Point(round(-width * 0.5), round(-height * 0.5)),
            Point(round(width * 0.5), round(-height * 0.5)),
            Point(round(width * 0.5), round(height * 0.5)),
            Point(round(-width * 0.5), round(height * 0.5)),
        ]
        super().__init__(ShapeType.RECT, color, points)
        self.id = f"Rect-{uuid()}"
        self.color = color
        self.width = width
        self.height = height

import pygame
from shortuuid import uuid  # type: ignore

from config import path_width
from entity.segment import Segment
from geometry.line import Line
from geometry.point import Point
from type import Color


class PaddingSegment(Segment):
    def __init__(self, color: Color, start_point: Point, end_point: Point) -> None:
        super().__init__(color)
        self.id = f"PathSegment-{uuid()}"
        self.segment_start = start_point
        self.segment_end = end_point
        self.line = Line(
            color=self.color,
            start=self.segment_start,
            end=self.segment_end,
            width=path_width,
        )

from __future__ import annotations

from abc import ABC

import pygame
from shortuuid import uuid  # type: ignore

from config import screen_height, screen_width
from entity.station import Station
from geometry.line import Line
from geometry.point import Point
from type import Color
from utils import brighten_color


class Segment(ABC):
    def __init__(self, color: Color) -> None:
        self.id = f"Segment-{uuid()}"
        self.color = color
        self.start_station: Station | None = None
        self.end_station: Station | None = None
        self.segment_start: Point
        self.segment_end: Point
        self.line: Line

    def __eq__(self, other: Segment) -> bool:
        return self.id == other.id

    def draw(self, surface: pygame.surface.Surface, cancelled: bool = False) -> None:
        self.line.color = brighten_color(self.color, 0.5 if cancelled else 0)
        self.line.draw(surface)

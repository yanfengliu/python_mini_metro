from __future__ import annotations

import pygame  # type: ignore
from shortuuid import uuid  # type: ignore

from config import path_width
from entity.station import Station
from geometry.line import Line
from type import Color


class PathSegment:
    def __init__(
        self, color: Color, start_station: Station, end_station: Station
    ) -> None:
        self.id = f"PathSegment-{uuid()}"
        self.color = color
        self.start_station = start_station
        self.end_station = end_station
        self.line = Line(
            color=self.color,
            start=start_station.position,
            end=end_station.position,
            width=path_width,
        )

    def __eq__(self, other: PathSegment) -> bool:
        return self.id == other.id

    def draw(self, surface: pygame.surface.Surface) -> None:
        self.line.draw(surface)

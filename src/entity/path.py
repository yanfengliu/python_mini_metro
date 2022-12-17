import uuid
from typing import List

import pygame

from entity.station import Station
from geometry.point import Point
from utils import get_random_color


class Path:
    def __init__(self) -> None:
        self.id = f"P-{uuid.uuid4()}"
        self.color = get_random_color()
        self.stations: List[Station] = []
        self.is_looped = False
        self.temp_point: Point | None = None

    def __repr__(self) -> str:
        return self.id

    def add_station(self, station: Station) -> None:
        self.stations.append(station)

    def draw(self, surface: pygame.surface.Surface) -> None:
        for i in range(len(self.stations) - 1):
            start = self.stations[i].position.to_tuple()
            end = self.stations[i + 1].position.to_tuple()
            pygame.draw.line(surface, self.color, start, end)

        if self.temp_point:
            start = self.stations[-1].position.to_tuple()
            end = self.temp_point.to_tuple()
            pygame.draw.line(surface, self.color, start, end)

    def add_temporary_point(self, temp_point: Point) -> None:
        self.temp_point = temp_point

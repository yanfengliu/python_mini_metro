import uuid
from typing import List

import pygame

from config import path_width
from entity.metro import Metro
from entity.station import Station
from geometry.line import Line
from geometry.point import Point
from geometry.utils import direction, dist
from utils import get_random_color


class Path:
    def __init__(self) -> None:
        self.id = f"P-{uuid.uuid4()}"
        self.color = get_random_color()
        self.stations: List[Station] = []
        self.metros: List[Metro] = []
        self.is_looped = False
        self.is_being_created = False
        self.temp_point: Point | None = None
        self.lines: List[Line] = []

    def __repr__(self) -> str:
        return self.id

    def add_station(self, station: Station) -> None:
        self.stations.append(station)
        self.update_lines()

    def update_lines(self) -> None:
        self.lines = []
        for i in range(len(self.stations) - 1):
            self.lines.append(
                Line(
                    color=self.color,
                    start=self.stations[i].position,
                    end=self.stations[i + 1].position,
                    width=path_width,
                )
            )

    def draw(self, surface: pygame.surface.Surface) -> None:
        for line in self.lines:
            line.draw(surface)

        if self.temp_point:
            temp_line = Line(
                color=self.color,
                start=self.stations[-1].position,
                end=self.temp_point,
                width=path_width,
            )
            temp_line.draw(surface)

    def add_temporary_point(self, temp_point: Point) -> None:
        self.temp_point = temp_point

    def add_metro(self, metro: Metro) -> None:
        metro.position = self.stations[0].position
        metro.current_line = self.lines[metro.current_line_idx]
        self.metros.append(metro)

    def move_metro(self, metro: Metro, dt_ms: int) -> None:
        assert metro.current_line is not None
        if metro.is_forward:
            destination = metro.current_line.end
        else:
            destination = metro.current_line.start

        distance = dist(metro.position, destination)
        direct = direction(metro.position, destination)
        if distance >= (metro.speed * dt_ms):
            metro.position += Point(
                direct.left * metro.speed * dt_ms, direct.top * metro.speed * dt_ms
            )
        else:
            if metro.is_forward:
                if metro.current_line_idx + 1 <= len(self.lines) - 1:
                    metro.current_line_idx += 1
                else:
                    if self.is_looped:
                        metro.current_line_idx = 0
                    else:
                        metro.current_line_idx -= 1
                        metro.is_forward = not metro.is_forward
                metro.current_line = self.lines[metro.current_line_idx]
            else:
                if metro.current_line_idx - 1 >= 0:
                    metro.current_line_idx -= 1
                else:
                    if self.is_looped:
                        metro.current_line_idx = len(self.lines) - 1
                    else:
                        metro.current_line_idx += 1
                        metro.is_forward = not metro.is_forward
                metro.current_line = self.lines[metro.current_line_idx]

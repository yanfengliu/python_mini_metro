from typing import List

import pygame  # type: ignore
from shortuuid import uuid  # type: ignore

from config import path_width
from entity.metro import Metro
from entity.path_segment import PathSegment
from entity.station import Station
from geometry.line import Line
from geometry.point import Point
from geometry.utils import direction, distance
from utils import get_random_color


class Path:
    def __init__(self) -> None:
        self.id = f"Path-{uuid()}"
        self.color = get_random_color()
        self.stations: List[Station] = []
        self.metros: List[Metro] = []
        self.is_looped = False
        self.is_being_created = False
        self.temp_point: Point | None = None
        self.segments: List[PathSegment] = []

    def __repr__(self) -> str:
        return self.id

    def add_station(self, station: Station) -> None:
        self.stations.append(station)
        self.update_segments()

    def update_segments(self) -> None:
        self.segments = []
        for i in range(len(self.stations) - 1):
            self.segments.append(
                PathSegment(self.color, self.stations[i], self.stations[i + 1])
            )
        if self.is_looped:
            self.segments.append(
                PathSegment(self.color, self.stations[-1], self.stations[0])
            )

    def draw(self, surface: pygame.surface.Surface) -> None:
        for segment in self.segments:
            segment.draw(surface)

        if self.temp_point:
            temp_line = Line(
                color=self.color,
                start=self.stations[-1].position,
                end=self.temp_point,
                width=path_width,
            )
            temp_line.draw(surface)

    def set_temporary_point(self, temp_point: Point) -> None:
        self.temp_point = temp_point

    def remove_temporary_point(self) -> None:
        self.temp_point = None

    def set_loop(self) -> None:
        self.is_looped = True
        self.update_segments()

    def remove_loop(self) -> None:
        self.is_looped = False
        self.update_segments()

    def add_metro(self, metro: Metro) -> None:
        metro.position = self.stations[0].position
        metro.current_segment = self.segments[metro.current_segment_idx]
        metro.path_id = self.id
        self.metros.append(metro)

    def move_metro(self, metro: Metro, dt_ms: int) -> None:
        assert metro.current_segment is not None
        if metro.is_forward:
            dst_station = metro.current_segment.end_station
        else:
            dst_station = metro.current_segment.start_station

        dist = distance(metro.position, dst_station.position)
        direct = direction(metro.position, dst_station.position)
        if dist > (metro.speed * dt_ms):
            metro.current_station = None
            metro.position += Point(
                direct.left * metro.speed * dt_ms, direct.top * metro.speed * dt_ms
            )
        else:
            metro.current_station = dst_station
            if len(self.segments) == 1:
                metro.is_forward = not metro.is_forward
            elif metro.current_segment_idx == len(self.segments) - 1:
                if self.is_looped:
                    metro.current_segment_idx = 0
                else:
                    if metro.is_forward:
                        metro.is_forward = False
                    else:
                        metro.current_segment_idx -= 1
            elif metro.current_segment_idx == 0:
                if metro.is_forward:
                    metro.current_segment_idx += 1
                else:
                    if self.is_looped:
                        metro.current_segment_idx = len(self.segments) - 1
                    else:
                        metro.is_forward = True
            else:
                if metro.is_forward:
                    metro.current_segment_idx += 1
                else:
                    metro.current_segment_idx -= 1

            metro.current_segment = self.segments[metro.current_segment_idx]

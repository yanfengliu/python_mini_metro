import math
from typing import List

import pygame
from shortuuid import uuid  # type: ignore

from config import path_width
from entity.plane import plane
from entity.padding_segment import PaddingSegment
from entity.path_segment import PathSegment
from entity.segment import Segment
from entity.airport import airport
from geometry.line import Line
from geometry.point import Point
from geometry.utils import direction, distance
from type import Color


class Path:
    def __init__(self, color: Color) -> None:
        self.id = f"Path-{uuid()}"
        self.color = color
        self.airports: List[airport] = []
        self.planes: List[plane] = []
        self.is_looped = False
        self.is_being_created = False
        self.temp_point: Point | None = None
        self.segments: List[Segment] = []
        self.path_segments: List[PathSegment] = []
        self.padding_segments: List[PaddingSegment] = []
        self.path_order = 0

    def __repr__(self) -> str:
        return self.id

    def add_airport(self, airport: airport) -> None:
        self.airports.append(airport)
        self.update_segments()

    def update_segments(self) -> None:
        self.segments = []
        self.path_segments = []
        self.padding_segments = []

        for i in range(len(self.airports) - 1):
            self.path_segments.append(
                PathSegment(
                    self.color, self.airports[i], self.airports[i + 1], self.path_order
                )
            )

        if self.is_looped:
            self.path_segments.append(
                PathSegment(
                    self.color, self.airports[-1], self.airports[0], self.path_order
                )
            )

        for i in range(len(self.path_segments) - 1):
            padding_segment = PaddingSegment(
                self.color,
                self.path_segments[i].segment_end,
                self.path_segments[i + 1].segment_start,
            )
            self.padding_segments.append(padding_segment)
            self.segments.append(self.path_segments[i])
            self.segments.append(padding_segment)

        if self.path_segments:
            self.segments.append(self.path_segments[-1])

        if self.is_looped:
            padding_segment = PaddingSegment(
                self.color,
                self.path_segments[-1].segment_end,
                self.path_segments[0].segment_start,
            )
            self.padding_segments.append(padding_segment)
            self.segments.append(padding_segment)

    def insert_airport_on_segment(
        self,
        airport_to_insert: airport,
        existing_airport_1: airport,
        existing_airport_2: airport,
    ) -> bool:
        """
        Finds a segment between two existing airports and inserts a new airport.
        For example, turns a path ...-A-B-... into ...-A-C-B-...

        Args:
            airport_to_insert: The new airport object to add to the path.
            existing_airport_1: The first airport of the existing segment.
            existing_airport_2: The second airport of the existing segment.

        Returns:
            True if the segment was found and the airport was inserted, False otherwise.
        """
        for i in range(len(self.airports) - 1):
            airport_a = self.airports[i]
            airport_b = self.airports[i + 1]

            if (airport_a == existing_airport_1 and airport_b == existing_airport_2) or \
               (airport_a == existing_airport_2 and airport_b == existing_airport_1):
                
                insert_index = i + 1
                self.airports.insert(insert_index, airport_to_insert)
                self.update_segments()
                return True

        if self.is_looped and len(self.airports) > 1:
            airport_a = self.airports[-1]
            airport_b = self.airports[0]

            if (airport_a == existing_airport_1 and airport_b == existing_airport_2) or \
               (airport_a == existing_airport_2 and airport_b == existing_airport_1):
                
                self.airports.append(airport_to_insert)
                self.update_segments()
                return True

        return False

    def draw(self, surface: pygame.surface.Surface, path_order: int) -> None:
        self.path_order = path_order
        self.update_segments()

        for segment in self.segments:
            segment.draw(surface)

        if self.temp_point:
            temp_line = Line(
                color=self.color,
                start=self.airports[-1].position,
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

    def add_plane(self, plane: plane) -> None:
        plane.shape.color = self.color
        plane.current_segment = self.segments[plane.current_segment_idx]
        plane.position = plane.current_segment.segment_start
        plane.path_id = self.id
        self.planes.append(plane)

    def move_plane(self, plane: plane, dt_ms: int) -> None:
        assert plane.current_segment is not None
        if plane.is_forward:
            dst_airport = plane.current_segment.end_airport
            dst_position = plane.current_segment.segment_end
        else:
            dst_airport = plane.current_segment.start_airport
            dst_position = plane.current_segment.segment_start

        start_point = plane.position
        end_point = dst_position
        dist = distance(start_point, end_point)
        direct = direction(start_point, end_point)
        radians = math.atan2(direct.top, direct.left)
        degrees = math.degrees(radians)
        plane.shape.set_degrees(degrees)
        travel_dist_in_dt = plane.speed * dt_ms
        # plane is not at one end of segment
        if dist > travel_dist_in_dt:
            plane.current_airport = None
            plane.position += direct * travel_dist_in_dt
        # plane is at one end of segment
        else:
            plane.current_airport = dst_airport
            if len(self.segments) == 1:
                plane.is_forward = not plane.is_forward
            elif plane.current_segment_idx == len(self.segments) - 1:
                if self.is_looped:
                    plane.current_segment_idx = 0
                else:
                    if plane.is_forward:
                        plane.is_forward = False
                    else:
                        plane.current_segment_idx -= 1
            elif plane.current_segment_idx == 0:
                if plane.is_forward:
                    plane.current_segment_idx += 1
                else:
                    if self.is_looped:
                        plane.current_segment_idx = len(self.segments) - 1
                    else:
                        plane.is_forward = True
            else:
                if plane.is_forward:
                    plane.current_segment_idx += 1
                else:
                    plane.current_segment_idx -= 1

            plane.current_segment = self.segments[plane.current_segment_idx]

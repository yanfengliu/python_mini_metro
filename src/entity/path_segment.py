from __future__ import annotations

from config import path_order_shift, path_width
from entity.segment import Segment
from entity.station import Station
from geometry.line import Line
from geometry.point import Point
from geometry.utils import direction
from shortuuid import uuid  # type: ignore
from type import Color


class PathSegment(Segment):
    @staticmethod
    def _canonical_pair_direction(
        start_station: Station, end_station: Station
    ) -> Point:
        start_position = start_station.position
        end_position = end_station.position
        # Use one stable ordering per station pair so offsets are consistent
        # for both A->B and B->A segments.
        if (
            (start_position.left, start_position.top)
            <= (end_position.left, end_position.top)
        ):
            return direction(start_position, end_position)
        return direction(end_position, start_position)

    def __init__(
        self,
        color: Color,
        start_station: Station,
        end_station: Station,
        path_order: int,
    ) -> None:
        super().__init__(color)
        self.id = f"PathSegment-{uuid()}"
        self.start_station = start_station
        self.end_station = end_station
        self.path_order = path_order

        direct = self._canonical_pair_direction(start_station, end_station)
        buffer_vector = direct * path_order_shift
        buffer_vector = buffer_vector.rotate(90)

        self.segment_start = start_station.position + buffer_vector * self.path_order
        self.segment_end = end_station.position + buffer_vector * self.path_order
        self.line = Line(
            color=self.color,
            start=self.segment_start,
            end=self.segment_end,
            width=path_width,
        )

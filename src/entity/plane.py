import pygame
from shortuuid import uuid  # type: ignore

from config import (
    plane_capacity,
    plane_color,
    plane_passengers_per_row,
    plane_size,
    plane_speed_per_ms,
)
from entity.holder import Holder
from entity.segment import Segment
from entity.airport import airport
from geometry.rect import Rect


class plane(Holder):
    def __init__(self) -> None:
        self.size = plane_size
        plane_shape = Rect(color=plane_color, width=2 * self.size, height=self.size)
        super().__init__(
            shape=plane_shape,
            capacity=plane_capacity,
            id=f"plane-{uuid()}",
        )
        self.current_airport: airport | None = None
        self.current_segment: Segment | None = None
        self.current_segment_idx = 0
        self.path_id = ""
        self.speed = plane_speed_per_ms
        self.is_forward = True
        self.passengers_per_row = plane_passengers_per_row

import pygame
from math import ceil

from config import (
    metro_accel_time_ms,
    metro_boarding_time_per_passenger_ms,
    metro_capacity,
    metro_color,
    metro_decel_time_ms,
    metro_passengers_per_row,
    metro_size,
    metro_speed_per_ms,
    passenger_size,
)
from entity.holder import Holder
from entity.segment import Segment
from entity.station import Station
from geometry.point import Point
from geometry.rect import Rect
from shortuuid import uuid  # type: ignore


class Metro(Holder):
    def __init__(self) -> None:
        self.size = metro_size
        metro_shape = Rect(color=metro_color, width=2 * self.size, height=self.size)
        super().__init__(
            shape=metro_shape,
            capacity=metro_capacity,
            id=f"Metro-{uuid()}",
        )
        self.current_station: Station | None = None
        self.current_segment: Segment | None = None
        self.current_segment_idx = 0
        self.path_id = ""
        self.max_speed = metro_speed_per_ms
        self.speed = self.max_speed
        self.acceleration_per_ms = self.max_speed / metro_accel_time_ms
        self.deceleration_per_ms = self.max_speed / metro_decel_time_ms
        self.is_forward = True
        self.passengers_per_row = metro_passengers_per_row
        self.stop_time_remaining_ms = 0
        self.boarding_progress_ms = 0
        self.boarding_time_per_passenger_ms = metro_boarding_time_per_passenger_ms
        self.just_arrived_and_stopped = False

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        passenger_max_wait_time_ms: int | None = None,
    ) -> None:
        self.shape.draw(surface, self.position)

        grid_cols = self.passengers_per_row
        grid_rows = ceil(self.capacity / grid_cols)
        metro_width = 2 * self.size
        metro_height = self.size
        passenger_diameter = 2 * passenger_size
        x_gap = (metro_width - (grid_cols * passenger_diameter)) / (grid_cols + 1)
        y_gap = (metro_height - (grid_rows * passenger_diameter)) / (grid_rows + 1)
        x_step = passenger_diameter + x_gap
        y_step = passenger_diameter + y_gap
        x_start = (-metro_width / 2) + x_gap + passenger_size
        y_start = (-metro_height / 2) + y_gap + passenger_size
        metro_degrees = getattr(self.shape, "degrees", 0.0)

        for idx, passenger in enumerate(self.passengers):
            col = idx % grid_cols
            row = idx // grid_cols
            x_offset = x_start + (col * x_step)
            y_offset = y_start + (row * y_step)
            rotated_offset = Point(x_offset, y_offset).rotate(metro_degrees)
            passenger.position = self.position + rotated_offset
            passenger.draw(
                surface,
                current_time_ms=current_time_ms,
                max_wait_time_ms=passenger_max_wait_time_ms,
                rotation_degrees=metro_degrees,
            )

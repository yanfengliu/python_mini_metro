from math import ceil, cos, radians, sin
from typing import Any, Iterable

import pygame
from shortuuid import uuid  # type: ignore

from config import (
    metro_accel_time_ms,
    metro_boarding_time_per_passenger_ms,
    metro_capacity,
    metro_color,
    metro_decel_time_ms,
    metro_outline_color,
    metro_outline_width,
    metro_passengers_per_row,
    metro_queue_outline_color,
    metro_queue_outline_width,
    metro_size,
    metro_speed_per_ms,
    passenger_size,
)
from entity.holder import Holder
from entity.segment import Segment
from entity.station import Station
from geometry.point import Point
from geometry.rect import Rect


class Metro(Holder):
    def __init__(self) -> None:
        self.size = metro_size
        self.carriages: list[Any] = []
        self._base_capacity = 0
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
        self.is_unassignment_queued = False
        self._station_service_action: tuple[Any, Any] | None = None

    @property
    def capacity(self) -> int:
        return self._base_capacity + sum(
            carriage.capacity for carriage in self.carriages
        )

    @capacity.setter
    def capacity(self, value: int) -> None:
        if type(value) is not int:
            raise TypeError("Metro capacity must be an integer")
        attached_capacity = sum(
            carriage.capacity for carriage in getattr(self, "carriages", ())
        )
        passenger_count = len(getattr(self, "passengers", ()))
        if value < attached_capacity or value < passenger_count:
            raise ValueError("Metro capacity cannot strand attached capacity or riders")
        self._base_capacity = value - attached_capacity

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        passenger_max_wait_time_ms: int | None = None,
        display_position: Point | tuple[float, float] | None = None,
        rotation_degrees: float | None = None,
        *,
        passengers: Iterable[Any] | None = None,
        is_unassignment_queued: bool | None = None,
    ) -> None:
        draw_position = self.position if display_position is None else display_position
        center_x, center_y = (
            draw_position
            if isinstance(draw_position, tuple)
            else draw_position.to_tuple()
        )
        draw_degrees = (
            getattr(self.shape, "degrees", 0.0)
            if rotation_degrees is None
            else rotation_degrees
        )
        self.shape.draw(
            surface,
            draw_position,
            rotation_degrees=draw_degrees,
        )
        angle = radians(draw_degrees)
        sine = sin(angle)
        cosine = cos(angle)
        outline_points = [
            (
                round(cosine * point.left - sine * point.top) + center_x,
                round(sine * point.left + cosine * point.top) + center_y,
            )
            for point in self.shape.points
        ]
        queued = (
            self.is_unassignment_queued
            if is_unassignment_queued is None
            else is_unassignment_queued
        )
        if queued:
            pygame.draw.polygon(
                surface,
                metro_queue_outline_color,
                outline_points,
                metro_queue_outline_width,
            )
        pygame.draw.polygon(
            surface, metro_outline_color, outline_points, metro_outline_width
        )

        grid_cols = self.passengers_per_row
        grid_rows = ceil(self._base_capacity / grid_cols)
        metro_width = 2 * self.size
        metro_height = self.size
        passenger_diameter = 2 * passenger_size
        x_gap = (metro_width - (grid_cols * passenger_diameter)) / (grid_cols + 1)
        y_gap = (metro_height - (grid_rows * passenger_diameter)) / (grid_rows + 1)
        x_step = passenger_diameter + x_gap
        y_step = passenger_diameter + y_gap
        x_start = (-metro_width / 2) + x_gap + passenger_size
        y_start = (-metro_height / 2) + y_gap + passenger_size

        displayed_passengers = self.passengers if passengers is None else passengers
        for idx, passenger in enumerate(displayed_passengers):
            col = idx % grid_cols
            row = idx // grid_cols
            x_offset = x_start + col * x_step
            y_offset = y_start + row * y_step
            rotated_x = round(cosine * x_offset - sine * y_offset)
            rotated_y = round(sine * x_offset + cosine * y_offset)
            passenger.draw(
                surface,
                current_time_ms=current_time_ms,
                max_wait_time_ms=passenger_max_wait_time_ms,
                rotation_degrees=draw_degrees,
                display_position=(center_x + rotated_x, center_y + rotated_y),
            )

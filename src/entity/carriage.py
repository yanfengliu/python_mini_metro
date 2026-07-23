"""Attached passenger-capacity body rendered as part of a Metro consist."""

from __future__ import annotations

from math import ceil, cos, radians, sin
from typing import Any, Iterable

import pygame
from shortuuid import uuid  # type: ignore

from config import (
    carriage_capacity,
    carriage_color,
    carriage_outline_color,
    carriage_outline_width,
    carriage_passengers_per_row,
    carriage_queue_outline_color,
    carriage_queue_outline_width,
    carriage_size,
    passenger_size,
)
from geometry.point import Point
from geometry.rect import Rect


class Carriage:
    """One live attached carriage; unassigned inventory has no entity object."""

    def __init__(self) -> None:
        self.id = f"Carriage-{uuid()}"
        self.size = carriage_size
        self._capacity = carriage_capacity
        self.shape = Rect(
            color=carriage_color,
            width=2 * self.size,
            height=self.size,
        )
        self.position = Point(0, 0)
        self.passengers_per_row = carriage_passengers_per_row

    @property
    def capacity(self) -> int:
        return self._capacity

    def __repr__(self) -> str:
        return self.id

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        passenger_max_wait_time_ms: int | None = None,
        display_position: Point | tuple[float, float] | None = None,
        rotation_degrees: float | None = None,
        *,
        passengers: Iterable[Any] = (),
        is_unassignment_queued: bool = False,
        reduced_motion: bool = False,
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
        self.shape.draw(surface, draw_position, rotation_degrees=draw_degrees)

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
        if is_unassignment_queued:
            pygame.draw.polygon(
                surface,
                carriage_queue_outline_color,
                outline_points,
                carriage_queue_outline_width,
            )
        pygame.draw.polygon(
            surface,
            carriage_outline_color,
            outline_points,
            carriage_outline_width,
        )

        grid_cols = self.passengers_per_row
        grid_rows = ceil(self.capacity / grid_cols)
        body_width = 2 * self.size
        body_height = self.size
        passenger_diameter = 2 * passenger_size
        x_gap = (body_width - grid_cols * passenger_diameter) / (grid_cols + 1)
        y_gap = (body_height - grid_rows * passenger_diameter) / (grid_rows + 1)
        x_start = (-body_width / 2) + x_gap + passenger_size
        y_start = (-body_height / 2) + y_gap + passenger_size
        x_step = passenger_diameter + x_gap
        y_step = passenger_diameter + y_gap

        for index, passenger in enumerate(passengers):
            col = index % grid_cols
            row = index // grid_cols
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
                reduced_motion=reduced_motion,
            )

from __future__ import annotations

import pygame
from config import (
    station_capacity,
    station_passengers_per_row,
    station_size,
    station_snap_blip_duration_ms,
    station_snap_blip_radius_growth,
    station_snap_blip_width,
    unlock_blink_count,
    unlock_blink_duration_ms,
)
from entity.holder import Holder
from geometry.point import Point
from geometry.shape import Shape
from shortuuid import uuid  # type: ignore
from type import Color


class Station(Holder):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            capacity=station_capacity,
            id=f"Station-{uuid()}-{shape.type}",
        )
        self.size = station_size
        self.position = position
        self.passengers_per_row = station_passengers_per_row
        self.unlock_blink_start_time_ms: int | None = None
        self.snap_blips: list[tuple[int, Color]] = []

    def __eq__(self, other: Station) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def start_unlock_blink(self, current_time_ms: int) -> None:
        self.unlock_blink_start_time_ms = current_time_ms

    def is_unlock_blink_active(self, current_time_ms: int) -> bool:
        if self.unlock_blink_start_time_ms is None:
            return False
        return (
            current_time_ms - self.unlock_blink_start_time_ms
            < unlock_blink_duration_ms
        )

    def is_unlock_blink_visible(self, current_time_ms: int) -> bool:
        if not self.is_unlock_blink_active(current_time_ms):
            return True
        assert self.unlock_blink_start_time_ms is not None
        elapsed_ms = current_time_ms - self.unlock_blink_start_time_ms
        phase_duration_ms = unlock_blink_duration_ms / (unlock_blink_count * 2)
        phase_index = int(elapsed_ms / phase_duration_ms)
        return phase_index % 2 == 0

    def start_snap_blip(self, current_time_ms: int, color: Color) -> None:
        self.snap_blips.append((current_time_ms, color))

    def get_active_snap_blips(self, current_time_ms: int) -> list[tuple[int, Color]]:
        return [
            (start_time_ms, color)
            for start_time_ms, color in self.snap_blips
            if current_time_ms - start_time_ms < station_snap_blip_duration_ms
        ]

    def draw_snap_blips(
        self, surface: pygame.surface.Surface, current_time_ms: int
    ) -> None:
        self.snap_blips = self.get_active_snap_blips(current_time_ms)
        for start_time_ms, color in self.snap_blips:
            elapsed_ms = current_time_ms - start_time_ms
            progress = elapsed_ms / station_snap_blip_duration_ms
            radius = int(self.size + (station_snap_blip_radius_growth * progress))
            if radius > self.size:
                pygame.draw.circle(
                    surface,
                    color,
                    self.position.to_tuple(),
                    radius,
                    station_snap_blip_width,
                )

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        passenger_max_wait_time_ms: int | None = None,
    ) -> None:
        if (
            current_time_ms is not None
            and not self.is_unlock_blink_visible(current_time_ms)
        ):
            return
        super().draw(
            surface,
            current_time_ms=current_time_ms,
            passenger_max_wait_time_ms=passenger_max_wait_time_ms,
        )
        if current_time_ms is not None:
            self.draw_snap_blips(surface, current_time_ms)

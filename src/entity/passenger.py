import pygame
from config import passenger_blink_interval_ms, passenger_blink_warning_time_ms
from geometry.point import Point
from geometry.shape import Shape
from shortuuid import uuid  # type: ignore


class Passenger:
    def __init__(self, destination_shape: Shape) -> None:
        self.id = f"Passenger-{uuid()}"
        self.position = Point(0, 0)
        self.destination_shape = destination_shape
        self.is_at_destination = False
        self.wait_ms = 0

    def __repr__(self) -> str:
        return f"{self.id}-{self.destination_shape.type}"

    def __hash__(self) -> int:
        return hash(self.id)

    def is_in_warning_window(self, max_wait_time_ms: int) -> bool:
        return (
            self.wait_ms < max_wait_time_ms
            and (max_wait_time_ms - self.wait_ms) <= passenger_blink_warning_time_ms
        )

    def is_waiting_too_long(self, max_wait_time_ms: int) -> bool:
        return self.wait_ms >= max_wait_time_ms

    def should_blink_for_wait(self, max_wait_time_ms: int) -> bool:
        return self.is_in_warning_window(max_wait_time_ms) or self.is_waiting_too_long(
            max_wait_time_ms
        )

    def is_warning_blink_visible(self, current_time_ms: int) -> bool:
        phase_index = int(current_time_ms / passenger_blink_interval_ms)
        return phase_index % 2 == 0

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        max_wait_time_ms: int | None = None,
    ):
        if (
            current_time_ms is not None
            and max_wait_time_ms is not None
            and self.should_blink_for_wait(max_wait_time_ms)
            and not self.is_warning_blink_visible(current_time_ms)
        ):
            return
        self.destination_shape.draw(surface, self.position)

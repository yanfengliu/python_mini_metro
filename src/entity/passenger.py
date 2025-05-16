import pygame
from shortuuid import uuid  # type: ignore

from geometry.point import Point
from geometry.shape import Shape


class Passenger:
    def __init__(self, destination_shape: Shape) -> None:
        self.id = f"Passenger-{uuid()}"
        self.position = Point(0, 0)
        self.destination_shape = destination_shape
        self.is_at_destination = False

    def __repr__(self) -> str:
        return f"{self.id}-{self.destination_shape.type}"

    def __hash__(self) -> int:
        return hash(self.id)

    def draw(self, surface: pygame.surface.Surface):
        self.destination_shape.draw(surface, self.position)

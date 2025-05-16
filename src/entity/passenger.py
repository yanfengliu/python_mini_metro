import pygame
from shortuuid import uuid  # type: ignore

from geometry.point import Point
from geometry.shape import Shape

from config import passenger_patience


class Passenger:
    def __init__(self, destination_shape: Shape) -> None:
        self.id = f"Passenger-{uuid()}"
        self.position = Point(0, 0)
        self.destination_shape = destination_shape
        self.is_at_destination = False
        
        self.wait_timesteps = 0
        self.original_color = self.destination_shape.color
        self.patience_color = (255, 0, 0)

    def __repr__(self) -> str:
        return f"{self.id}-{self.destination_shape.type}"

    def __hash__(self) -> int:
        return hash(self.id)
    
    def get_patience_color(self) -> tuple[int, int, int]:
        # interpolate between original color and patience color
        patience_factor = self.wait_timesteps / passenger_patience
        return tuple(s + patience_factor * (e - s) for s, e in zip(self.original_color, self.patience_color))

    def draw(self, surface: pygame.surface.Surface):
        self.destination_shape.color = self.get_patience_color()
        self.destination_shape.draw(surface, self.position)

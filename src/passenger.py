import uuid

import pygame

from geometry.shape import Shape


class Passenger:
    def __init__(self, destination_shape: Shape) -> None:
        self.id = f"P-{uuid.uuid4()}"
        self.destination_shape = destination_shape

    def __repr__(self) -> str:
        return self.id

    def draw(self, surface: pygame.Surface):
        self.destination_shape.draw(surface, self.position)

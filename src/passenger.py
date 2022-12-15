import pygame

from holder import Holder
from metro import Metro
from shapes.shape import Shape
from utils import get_uuid


class Passenger:
    def __init__(self, destination_shape: Shape) -> None:
        self.id = f"P-{get_uuid()}"
        self.destination_shape = destination_shape

    def __repr__(self) -> str:
        return self.id

    def draw(self, surface: pygame.Surface):
        self.destination_shape.draw(surface, self.position)

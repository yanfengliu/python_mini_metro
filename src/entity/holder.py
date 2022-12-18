from abc import ABC
from typing import List
from uuid import uuid4

import pygame

from config import passenger_display_buffer, passenger_size
from entity.passenger import Passenger
from geometry.point import Point
from geometry.shape import Shape


class Holder(ABC):
    def __init__(self, shape: Shape, capacity: int, id: str) -> None:
        self.shape = shape
        self.capacity = capacity
        self.id = id
        self.position = Point(0, 0)
        self.passengers: List[Passenger] = []
        self.passengers_per_row = 1
        self.size = 1

    def __repr__(self) -> str:
        return self.id

    def draw(self, surface: pygame.surface.Surface):
        # draw self
        self.shape.draw(surface, self.position)

        # draw passengers
        row = 0
        col = 0
        for passenger in self.passengers:
            passenger.position = (
                self.position
                + Point(
                    (-2 * passenger_size - passenger_display_buffer), 1.5 * self.size
                )
                + Point(
                    col * (passenger_size + passenger_display_buffer),
                    row * (passenger_size + passenger_display_buffer),
                )
            )

            passenger.draw(surface)

            if col < (self.passengers_per_row - 1):
                col += 1
            else:
                row += 1
                col = 0

    def contains(self, point: Point):
        return self.shape.contains(point)

    def has_room(self) -> bool:
        return self.capacity > len(self.passengers)

    def add_passenger(self, passenger: Passenger) -> None:
        assert self.has_room()
        self.passengers.append(passenger)

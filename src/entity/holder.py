from __future__ import annotations

from abc import ABC
from typing import List

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
        self.position: Point
        self.passengers: List[Passenger] = []
        self.passengers_per_row: int
        self.size: int

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

    def remove_passenger(self, passenger: Passenger) -> None:
        assert passenger in self.passengers
        self.passengers.remove(passenger)

    def move_passenger(self, passenger: Passenger, holder: Holder) -> None:
        assert holder.has_room()
        holder.add_passenger(passenger)
        self.remove_passenger(passenger)

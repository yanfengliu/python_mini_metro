from __future__ import annotations

from abc import ABC
from math import cos, pi, sin
from typing import List

import pygame

from config import passenger_display_buffer, passenger_size
from entity.passenger import Passenger
from geometry.point import Point
from geometry.shape import Shape
from utils import lerp


class Holder(ABC):
    def __init__(self, shape: Shape, capacity: int, id: str) -> None:
        self.shape = shape
        self.capacity = capacity
        self.id = id
        self.position: Point
        self.passengers: List[Passenger] = []
        self.passenger_rotation: List[float] = [0 for _ in range(capacity)]
        self.size: int

    def __repr__(self) -> str:
        return self.id

    def draw(self, surface: pygame.surface.Surface):
        # draw self
        self.shape.draw(surface, self.position)

        # draw passengers
        rot_per_passenger = 2 * pi / len(self.passengers) if len(self.passengers) > 0 else 0
        for i in range(len(self.passengers)):
            self.passenger_rotation[i] = lerp(self.passenger_rotation[i], rot_per_passenger * (len(self.passengers) - i - 1), 0.2)

        for i, passenger in enumerate(self.passengers):
            passenger.position = (
                self.position
                + Point(
                    self.size * 2.5 * cos(self.passenger_rotation[i]), self.size * 2.5 * sin(self.passenger_rotation[i])
                )
                + Point(
                    0, sin(pygame.time.get_ticks() / 200 + self.passenger_rotation[i])
                )
            )
            passenger.draw(surface)

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

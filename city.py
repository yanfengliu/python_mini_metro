import random
from typing import Tuple

import pygame

from station import Station


class City:
    def __init__(self, width: int, height: int, station_radius: int):
        self.width = width
        self.height = height
        self.station_radius = station_radius
        self.min_station_distance = 100
        self.stations = []
        self.generate_station()

    def station_at_position(self, pos: Tuple[int, int]) -> Station:
        for station in self.stations:
            if station.contains(pos):
                return station
        return None

    def generate_station(self) -> None:
        valid_position = False
        position = None

        while not valid_position:
            position = (
                random.randint(self.station_radius, self.width - self.station_radius),
                random.randint(self.station_radius, self.height - self.station_radius),
            )
            valid_position = True
            for station in self.stations:
                distance = (
                    (position[0] - station.position[0]) ** 2
                    + (position[1] - station.position[1]) ** 2
                ) ** 0.5
                if distance < self.min_station_distance:
                    valid_position = False
                    break

        new_station = Station(position, self.station_radius)
        self.stations.append(new_station)

    def render(self, screen: pygame.Surface) -> None:
        for station in self.stations:
            station.render(screen)

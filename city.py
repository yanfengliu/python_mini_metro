import math
import random
from typing import Optional, Tuple

import pygame

from station import Station


class City:
    def __init__(self, max_stations: int = 20):
        self.stations = []
        self.max_stations = max_stations
        self.generate_station()
        self.station_timer = 0
        self.station_generation_interval = (
            3000  # Time in milliseconds between station generations
        )

    def update(self, dt: int) -> None:
        """Update the city, generating new stations based on the timer.

        :param dt: Time passed since the last frame in milliseconds.
        """
        if len(self.stations) < self.max_stations:
            self.station_timer += dt
            if self.station_timer >= self.station_generation_interval:
                self.generate_station()
                self.station_timer = 0

    def render(self, screen: pygame.Surface) -> None:
        """Render the city, drawing all stations on the screen.

        :param screen: The Pygame surface to draw on.
        """
        for station in self.stations:
            station.render(screen)

    def generate_station(self) -> None:
        """Generate a new station in the city."""
        position = (random.randint(50, 750), random.randint(50, 550))
        station_type = random.choice(Station.TYPES)
        new_station = Station(position, station_type)
        self.stations.append(new_station)

    def station_at_position(
        self, pos: Tuple[int, int], radius: int = 15
    ) -> Optional[Station]:
        """Return the station at the given position, if any.

        :param pos: A tuple representing the position (x, y) to check for a station.
        :param radius: The radius around the position to search for a station.
        :return: The station at the given position, if any. None if no station is found.
        """
        for station in self.stations:
            distance = math.sqrt(
                (station.position[0] - pos[0]) ** 2
                + (station.position[1] - pos[1]) ** 2
            )
            if distance <= radius:
                return station
        return None

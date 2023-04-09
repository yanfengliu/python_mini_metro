import math
import random

import pygame

from station import Station


class City:
    def __init__(self):
        self.stations = []
        self.generate_station()

    def update(self):
        pass  # Implement any city updates you need, like generating new stations periodically

    def render(self, screen):
        for station in self.stations:
            station.render(screen)

    def generate_station(self):
        position = (random.randint(50, 750), random.randint(50, 550))
        station_type = random.choice(Station.TYPES)
        new_station = Station(position, station_type)
        self.stations.append(new_station)

    def station_at_position(self, pos, radius=15):
        """
        Return the station at the given position, if any.

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

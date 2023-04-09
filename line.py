import random
from typing import List

import pygame

from station import Station


class Line:
    def __init__(self, name: str):
        self.name = name
        self.stations = []
        self.color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )

    def add_station(self, station: Station) -> None:
        if station not in self.stations:
            self.stations.append(station)

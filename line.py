from typing import List

from station import Station


class Line:
    def __init__(self, name: str):
        self.name = name
        self.stations = []

    def add_station(self, station: Station) -> None:
        """Add a station to the line.

        :param station: The Station object to be added.
        """
        self.stations.append(station)

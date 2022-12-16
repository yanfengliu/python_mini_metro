import uuid
from typing import List

from entity.station import Station


class Path:
    def __init__(self):
        self.id = f"P-{uuid.uuid4()}"
        self.stations: List[Station] = []

    def __repr__(self) -> str:
        return self.id

    def add_station(self, station: Station):
        self.stations.append(station)

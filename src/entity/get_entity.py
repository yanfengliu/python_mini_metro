from typing import List

from config import screen_height, screen_width
from entity.metro import Metro
from entity.station import Station
from geometry.utils import distance
from utils import get_random_position, get_random_station_shape


def get_random_station() -> Station:
    shape = get_random_station_shape()
    position = get_random_position(screen_width, screen_height)
    return Station(shape, position)

def get_random_stations(num: int) -> List[Station]:
    stations: List[Station] = []
    for _ in range(num):
        stations.append(get_random_station())
    return stations

def try_spawn_random_stations(num: int, min_dist_between_stations: int = 25) -> List[Station]:
    stations: List[Station] = []
    for _ in range(num):
        new_station = get_random_station()
        while len(stations) > 0 and not all([
            distance(new_station.position, station.position) >= min_dist_between_stations
            for station in stations
            ]):
            new_station = get_random_station()
        stations.append(new_station)
    return stations


def get_metros(num: int) -> List[Metro]:
    metros: List[Metro] = []
    for _ in range(num):
        metros.append(Metro())
    return metros

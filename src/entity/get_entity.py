import random
from typing import List

from config import (
    screen_height,
    screen_width,
    station_color,
    station_shape_type_list,
    station_size,
    station_unique_shape_type_list,
    station_unique_spawn_chance,
    station_unique_spawn_start_index,
)
from entity.metro import Metro
from entity.station import Station
from geometry.type import ShapeType
from utils import get_random_position, get_random_station_shape, get_shape_from_type


def get_random_station(shape_type: ShapeType | None = None) -> Station:
    shape = (
        get_shape_from_type(shape_type, station_color, station_size)
        if shape_type is not None
        else get_random_station_shape()
    )
    position = get_random_position(screen_width, screen_height)
    return Station(shape, position)


def get_random_stations(num: int) -> List[Station]:
    stations: List[Station] = []
    used_unique_shape_types: set[ShapeType] = set()
    for station_idx in range(num):
        shape_type = random.choice(station_shape_type_list)
        if (
            station_idx >= station_unique_spawn_start_index
            and random.random() < station_unique_spawn_chance
        ):
            available_unique_shape_types = [
                unique_shape_type
                for unique_shape_type in station_unique_shape_type_list
                if unique_shape_type not in used_unique_shape_types
            ]
            if available_unique_shape_types:
                shape_type = random.choice(available_unique_shape_types)
                used_unique_shape_types.add(shape_type)
        stations.append(get_random_station(shape_type))
    return stations


def get_metros(num: int) -> List[Metro]:
    metros: List[Metro] = []
    for _ in range(num):
        metros.append(Metro())
    return metros

from typing import List

from config import screen_height, screen_width
from entity.metro import Metro
from entity.station import Station
from geometry.shape import ShapeType
from utils import get_random_position, get_random_station_shape, get_grid_pos, get_certain_shape

import random


def get_random_station() -> Station:
    shape = get_random_station_shape()
    position = get_random_position(screen_width, screen_height)
    return Station(shape, position)

def get_station_at_grid(seq: int, need_new_shape: bool=False, choose_from_types=List[ShapeType]) -> Station:
    shape = None
    if need_new_shape and len(choose_from_types) > 0:
        shape = get_certain_shape(random.choice(choose_from_types))
    else:
        shape = get_random_station_shape()

    pos = get_grid_pos(seq)

    return Station(shape, pos)

# due to need_new_shape, procedure of try_spawn_random_stations() needs to be written in mediator.py

def get_metros(num: int) -> List[Metro]:
    metros: List[Metro] = []
    for _ in range(num):
        metros.append(Metro())
    return metros

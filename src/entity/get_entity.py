import random
from typing import List

from config import screen_height, screen_width, station_size
from entity.metro import Metro
from entity.station import Station
from geometry.point import Point
from geometry.type import ShapeType
from utils import get_random_position, get_random_station_shape, get_shape_from_type


def get_new_random_station() -> Station:
    all_shape_types = list(ShapeType)
    
    weights_map = {
        ShapeType.CIRCLE: 0.40,
        ShapeType.TRIANGLE: 0.30,
        ShapeType.RECT: 0.20,
        ShapeType.CROSS: 0.10
    }
    
    ordered_weights = [weights_map[shape_type] for shape_type in all_shape_types]
    
    chosen_shape_type = random.choices(all_shape_types, ordered_weights, k=1)[0]
    
    position = get_random_position(screen_width, screen_height)
    shape = get_shape_from_type(chosen_shape_type, (0, 0, 0), station_size)
    return Station(shape, position)

def get_initial_stations() -> List[Station]:
    stations: List[Station] = []
    
    initial_shapes = [ShapeType.TRIANGLE, ShapeType.CIRCLE, ShapeType.RECT]
    
    positions = [
        Point(screen_width * 0.25, screen_height * 0.3),
        Point(screen_width * 0.75, screen_height * 0.3),
        Point(screen_width * 0.5, screen_height * 0.7),
    ]

    for i, shape_type in enumerate(initial_shapes):
        shape = get_shape_from_type(shape_type, (0, 0, 0), station_size)
        station = Station(shape, positions[i])
        stations.append(station)
        
    return stations

def get_random_station() -> Station:
    shape = get_random_station_shape()
    position = get_random_position(screen_width, screen_height)
    return Station(shape, position)

def get_metros(num: int) -> List[Metro]:
    metros: List[Metro] = []
    for _ in range(num):
        metros.append(Metro())
    return metros

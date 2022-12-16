import colorsys
import random
import uuid
from typing import List

import numpy as np

from config import passenger_size, screen_height, screen_width, station_size
from geometry.circle import Circle
from geometry.rect import Rect
from geometry.shape import Shape
from geometry.type import ShapeType, station_shape_list
from metro import Metro
from station import Station
from type import Color, Point


def get_random_position(width: int, height: int) -> Point:
    padding_ratio = 0.1
    return {
        "left": int(
            width * (padding_ratio + np.random.rand() * (1 - padding_ratio * 2))
        ),
        "top": int(
            height * (padding_ratio + np.random.rand() * (1 - padding_ratio * 2))
        ),
    }


def get_random_color() -> Color:
    return tuple(255 * np.asarray(colorsys.hsv_to_rgb(np.random.rand(), 1.0, 1.0)))


def get_random_shape(shape_type_list: List[ShapeType], size: int) -> Shape:
    color = get_random_color()
    shape_type = random.choice(shape_type_list)
    if shape_type == ShapeType.RECT:
        return Rect(color=color, width=2 * size, height=2 * size)
    elif shape_type == ShapeType.CIRCLE:
        return Circle(color=color, radius=size)


station_shape_list = [ShapeType.RECT, ShapeType.CIRCLE]


def get_random_station_shape() -> Shape:
    return get_random_shape(station_shape_list, station_size)


def get_random_passenger_shape() -> Shape:
    return get_random_shape(station_shape_list, passenger_size)


def get_random_station() -> Station:
    shape = get_random_station_shape()
    position = get_random_position(screen_width, screen_height)
    return Station(shape, position)


def get_random_stations(num: int) -> List[Station]:
    stations: List[Station] = []
    for _ in range(num):
        stations.append(get_random_station())
    return stations


def get_metros(num: int) -> List[Metro]:
    metros: List[Metro] = []
    for _ in range(num):
        metros.append(Metro())
    return metros

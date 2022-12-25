import colorsys
import random
from typing import List, Tuple

import numpy as np

from config import passenger_size, station_color, station_shape_type_list, station_size
from geometry.circle import Circle
from geometry.cross import Cross
from geometry.point import Point
from geometry.rect import Rect
from geometry.shape import Shape
from geometry.triangle import Triangle
from geometry.type import ShapeType
from type import Color


def get_random_position(width: int, height: int) -> Point:
    padding_ratio = 0.1
    return Point(
        left=round(
            width * (padding_ratio + np.random.rand() * (1 - padding_ratio * 2))
        ),
        top=round(
            height * (padding_ratio + np.random.rand() * (1 - padding_ratio * 2))
        ),
    )


def get_random_color() -> Color:
    return hue_to_rgb(np.random.rand())


def hue_to_rgb(hue: float) -> Color:
    return tuple(255 * np.asarray(colorsys.hsv_to_rgb(hue, 1.0, 1.0)))


def get_random_shape(
    shape_type_list: List[ShapeType], color: Color, size: int
) -> Shape:
    shape_type = random.choice(shape_type_list)
    return get_shape_from_type(shape_type, color, size)


def get_random_station_shape() -> Shape:
    return get_random_shape(station_shape_type_list, station_color, station_size)


def get_random_passenger_shape() -> Shape:
    return get_random_shape(station_shape_type_list, get_random_color(), passenger_size)


def tuple_to_point(tuple: Tuple[int, int]) -> Point:
    return Point(left=tuple[0], top=tuple[1])


def get_shape_from_type(type: ShapeType, color: Color, size: int) -> Shape:
    if type == ShapeType.RECT:
        return Rect(color=color, width=2 * size, height=2 * size)
    elif type == ShapeType.CIRCLE:
        return Circle(color=color, radius=size)
    elif type == ShapeType.TRIANGLE:
        return Triangle(color=color, size=size)
    else:
        return Cross(color=color, size=size)


def within_time_window(game_time_ms: int, time_mark_ms: int, window_ms: int):
    return window_ms <= game_time_ms - time_mark_ms < (2 * window_ms)

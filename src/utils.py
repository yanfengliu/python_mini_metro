import colorsys
from random import Random
from typing import List, Tuple

import numpy as np

from config import (
    passenger_size,
    station_color,
    station_shape_type_list,
    station_size,
    station_grid_size,
    station_padding,
    screen_width,
    screen_height
)
from geometry.circle import Circle
from geometry.cross import Cross
from geometry.point import Point
from geometry.rect import Rect
from geometry.shape import Shape
from geometry.triangle import Triangle
from geometry.type import ShapeType
from type import Color


def get_random_position(width: int, height: int, rng: Random) -> Point:
    padding_ratio = 0.1
    return Point(
        left=round(
            width * (padding_ratio + rng.rand() * (1 - padding_ratio * 2))
        ),
        top=round(
            height * (padding_ratio + rng.rand() * (1 - padding_ratio * 2))
        ),
    )

padding = station_padding
grid_nx, grid_ny = station_grid_size
total_grid_num = grid_nx * grid_ny
grid_dx = int((screen_width - 2*padding) / grid_nx)
grid_dy = int((screen_height - 2*padding) / grid_ny)

def get_grid_pos(seq: int) -> Point:
    nx = seq // grid_ny
    ny = seq % grid_ny

    return Point(
        padding + nx * grid_dx,
        padding + ny * grid_dy
    )


def get_random_grid_seqs(used: List[bool], rng: Random, num: int = 1) -> List[int]:
    choices = [i for i in range(total_grid_num) if i not in used]
    return rng.sample(choices, num)


def get_random_color(rng: Random) -> Color:
    return hue_to_rgb(rng.random())


def hue_to_rgb(hue: float) -> Color:
    return tuple(255 * np.asarray(colorsys.hsv_to_rgb(hue, 1.0, 1.0)))


def get_random_shape(
    shape_type_list: List[ShapeType], color: Color, size: int, rng: Random
) -> Shape:
    shape_type = rng.choice(shape_type_list)
    return get_shape_from_type(shape_type, color, size)

def get_certain_shape(shapetype: ShapeType):
    return get_shape_from_type(shapetype, station_color, station_size)

def get_random_station_shape(rng: Random) -> Shape:
    return get_random_shape(station_shape_type_list, station_color, station_size, rng)


def get_random_passenger_shape(rng: Random) -> Shape:
    return get_random_shape(station_shape_type_list, get_random_color(rng), passenger_size, rng)


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

def brighten_color(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple([int(c + (255 - c) * factor) for c in color])

def lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t
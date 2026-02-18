import colorsys
import random
from typing import List, Tuple

import numpy as np
from config import passenger_size, station_color, station_shape_type_list, station_size
from geometry.circle import Circle
from geometry.cross import Cross
from geometry.diamond import Diamond
from geometry.pentagon import Pentagon
from geometry.point import Point
from geometry.rect import Rect
from geometry.shape import Shape
from geometry.star import Star
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


def hue_to_rgb(hue: float, saturation: float = 1.0, value: float = 1.0) -> Color:
    return tuple(255 * np.asarray(colorsys.hsv_to_rgb(hue, saturation, value)))


def hue_circular_distance(hue_a: float, hue_b: float) -> float:
    distance = abs(hue_a - hue_b)
    return min(distance, 1 - distance)


def pick_distinct_hue(existing_hues: List[float], candidate_hues: List[float]) -> float:
    if not candidate_hues:
        raise ValueError("candidate_hues must not be empty")
    if not existing_hues:
        return candidate_hues[0]
    return max(
        candidate_hues,
        key=lambda candidate: min(
            hue_circular_distance(candidate, existing_hue)
            for existing_hue in existing_hues
        ),
    )


def get_random_shape(
    shape_type_list: List[ShapeType], color: Color, size: int
) -> Shape:
    shape_type = random.choice(shape_type_list)
    return get_shape_from_type(shape_type, color, size)


def get_random_station_shape() -> Shape:
    return get_random_shape(station_shape_type_list, station_color, station_size)


def get_random_passenger_shape() -> Shape:
    return get_random_shape(station_shape_type_list, get_random_color(), passenger_size)


def tuple_to_point(coords: Tuple[int, int]) -> Point:
    return Point(left=coords[0], top=coords[1])


def get_shape_from_type(shape_type: ShapeType, color: Color, size: int) -> Shape:
    if shape_type == ShapeType.RECT:
        return Rect(color=color, width=2 * size, height=2 * size)
    if shape_type == ShapeType.CIRCLE:
        return Circle(color=color, radius=size)
    if shape_type == ShapeType.TRIANGLE:
        return Triangle(color=color, size=size)
    if shape_type == ShapeType.CROSS:
        return Cross(color=color, size=size)
    if shape_type == ShapeType.DIAMOND:
        return Diamond(color=color, size=size)
    if shape_type == ShapeType.PENTAGON:
        return Pentagon(color=color, size=size)
    if shape_type == ShapeType.STAR:
        return Star(color=color, size=size)
    raise ValueError(f"Unsupported shape type: {shape_type}")


def within_time_window(game_time_ms: int, time_mark_ms: int, window_ms: int) -> bool:
    return window_ms <= game_time_ms - time_mark_ms < (2 * window_ms)

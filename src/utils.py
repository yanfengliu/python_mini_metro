import colorsys
import random
import uuid
from typing import List

import numpy as np

from config import passenger_size, station_size
from shapes.circle import Circle
from shapes.rect import Rect
from shapes.type import ShapeType, station_shape_list
from type import Point


def get_random_position(width: int, height: int) -> Point:
    return {
        "left": int(np.random.rand() * width),
        "top": int(np.random.rand() * height),
    }


def get_random_color():
    return 255 * np.asarray(colorsys.hsv_to_rgb(np.random.rand(), 1.0, 1.0))


def get_random_shape(shape_type_list: List[ShapeType], size: int):
    color = get_random_color()
    shape_type = random.choice(shape_type_list)
    if shape_type == ShapeType.RECT:
        return Rect(color=color, width=2 * size, height=2 * size)
    elif shape_type == ShapeType.CIRCLE:
        return Circle(color=color, radius=size)


station_shape_list = [ShapeType.RECT, ShapeType.CIRCLE]


def get_random_station_shape():
    return get_random_shape(station_shape_list, station_size)


def get_random_passenger_shape():
    return get_random_shape(station_shape_list, passenger_size)


def get_uuid():
    return uuid.uuid4().hex

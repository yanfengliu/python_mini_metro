import colorsys
import random

import numpy as np

from shapes.circle import Circle
from shapes.rect import Rect
from shapes.types import ShapeType, station_shape_list


def get_random_position(width, height):
    return {
        "left": int(np.random.rand() * width),
        "top": int(np.random.rand() * height),
    }


def get_random_color():
    return 255 * np.asarray(colorsys.hsv_to_rgb(np.random.rand(), 1.0, 1.0))


def get_random_shape(shape_type_list, size):
    color = get_random_color()
    shape_type = random.choice(shape_type_list)
    if shape_type == ShapeType.RECT:
        return Rect(color=color, width=2 * size, height=2 * size)
    elif shape_type == ShapeType.CIRCLE:
        return Circle(color=color, radius=size)


def get_random_station_shape():
    station_shape_list = [ShapeType.RECT, ShapeType.CIRCLE]
    station_size = 10
    return get_random_shape(station_shape_list, station_size)

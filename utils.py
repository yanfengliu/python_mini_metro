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


def get_random_shape():
    color = get_random_color()
    shape_type = random.choice(station_shape_list)
    if shape_type == ShapeType.RECT:
        return Rect(color=color, width=20, height=20)
    elif shape_type == ShapeType.CIRCLE:
        return Circle(color=color, radius=10)

import numpy as np
import math

from geometry.point import Point


def distance(p1: Point, p2: Point) -> float:
    return np.sqrt((p1.left - p2.left) ** 2 + (p1.top - p2.top) ** 2)


def direction(start: Point, end: Point) -> Point:
    diff = end - start
    diff_magnitude = math.sqrt(diff.left**2 + diff.top**2)
    if diff_magnitude == 0:
        return Point(0, 0)
    return Point(diff.left / diff_magnitude, diff.top / diff_magnitude)

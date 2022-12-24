from __future__ import annotations

import math
from copy import deepcopy

from shortuuid import uuid  # type: ignore


class Point:
    def __init__(self, left: int | float, top: int | float) -> None:
        self.left = left
        self.top = top
        self.id = f"Point-{uuid()}"

    def __repr__(self) -> str:
        return f"Point(left = {self.left}, top = {self.top})"

    def __add__(self, other: Point | int | float) -> Point:
        if isinstance(other, Point):
            return Point(self.left + other.left, self.top + other.top)
        elif isinstance(other, int) or isinstance(other, float):
            return Point(self.left + other, self.top + other)

    def __radd__(self, other: Point | int | float) -> Point:
        return self.__add__(other)

    def __sub__(self, other: Point | int | float) -> Point:
        if isinstance(other, Point):
            return Point(self.left - other.left, self.top - other.top)
        elif isinstance(other, int) or isinstance(other, float):
            return Point(self.left - other, self.top - other)

    def __rsub__(self, other: Point | int | float) -> Point:
        if isinstance(other, Point):
            return Point(other.left - self.left, other.top - self.top)
        elif isinstance(other, int) or isinstance(other, float):
            return Point(other - self.left, other - self.top)

    def __mul__(self, other: int | float) -> Point:
        if isinstance(other, int) or isinstance(other, float):
            return Point(other * self.left, other * self.top)

    def __rmul__(self, other: int | float) -> Point:
        return self.__mul__(other)

    def __eq__(self, other: Point) -> bool:
        return self.left == other.left and self.top == other.top

    def rotate(self, degrees: float) -> Point:
        # Rotate around the origin.
        # A point is also a vector from the origin.
        radians = math.radians(degrees)
        s = math.sin(radians)
        c = math.cos(radians)
        x = self.left
        y = self.top
        new_left = round(c * x - s * y)
        new_top = round(s * x + c * y)

        return Point(new_left, new_top)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def to_tuple(self):
        return (self.left, self.top)

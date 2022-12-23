from __future__ import annotations

from copy import deepcopy

from shortuuid import uuid  # type: ignore


class Point:
    def __init__(self, left: int | float, top: int | float) -> None:
        self.left = left
        self.top = top
        self.id = f"Point-{uuid()}"

    def __repr__(self) -> str:
        return f"Point(left = {self.left}, top = {self.top})"

    def __add__(self, other: Point):
        return Point(self.left + other.left, self.top + other.top)

    def __sub__(self, other: Point):
        return Point(self.left - other.left, self.top - other.top)

    def __eq__(self, other: Point) -> bool:
        return self.left == other.left and self.top == other.top

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def to_tuple(self):
        return (self.left, self.top)

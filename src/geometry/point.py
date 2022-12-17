from __future__ import annotations

from typing import Tuple


class Point:
    def __init__(self, left: int | float, top: int | float) -> None:
        self.left = left
        self.top = top

    def __repr__(self) -> str:
        return f"Point(left = {self.left}, top = {self.top})"

    def __add__(self, other: Point):
        return Point(self.left + other.left, self.top + other.top)

    def __sub__(self, other: Point):
        return Point(self.left - other.left, self.top - other.top)

    def __eq__(self, other: Point) -> bool:
        return self.left == other.left and self.top == other.top

    def to_tuple(self):
        return (self.left, self.top)

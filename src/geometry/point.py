from __future__ import annotations


class Point:
    def __init__(self, left: int, top: int) -> None:
        self.left = left
        self.top = top

    def __add__(self, other: Point):
        return Point(self.left + other.left, self.top + other.top)

    def __eq__(self, other: Point) -> bool:
        return self.left == other.left and self.top == other.top

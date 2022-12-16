from typing import Tuple, TypedDict


class Point(TypedDict):
    left: int
    top: int

Color = Tuple[int, int, int]

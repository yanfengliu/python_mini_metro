from pygame import Surface

from config import metro_capacity, metro_color, metro_size
from holder import Holder
from path import Path
from shapes.rect import Rect
from station import Station
from type import Point
from utils import get_uuid


class Metro(Holder):
    def __init__(self, position: Point) -> None:
        metro_shape = Rect(color=metro_color, width=3 * metro_size, height=metro_size)
        super().__init__(
            shape=metro_shape,
            position=position,
            capacity=metro_capacity,
            id=f"M-{get_uuid()}",
        )

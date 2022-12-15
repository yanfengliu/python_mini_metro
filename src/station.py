from typing import List

from pygame import Surface

from config import station_capacity
from holder import Holder
from path import Path
from shapes.shape import Shape
from type import Point
from utils import get_uuid


class Station(Holder):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            position=position,
            capacity=station_capacity,
            id=f"S-{get_uuid()}",
        )

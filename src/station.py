from config import station_capacity
from geometry.shape import Shape
from holder import Holder
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

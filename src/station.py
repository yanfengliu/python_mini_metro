from config import station_capacity
from geometry.shape import Shape
from holder import Holder
from type import Point
from utils import uuid


class Station(Holder):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(
            shape=shape,
            capacity=station_capacity,
            id=f"S-{uuid.uuid4()}",
        )
        self.position = position

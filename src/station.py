from holder import Holder
from utils import get_uuid


class Station(Holder):
    def __init__(self, shape, position) -> None:
        super().__init__(shape)
        self.position = position
        self.id = f"S-{get_uuid()}"
        self.capacity = 12

    def draw(self, surface):
        self.shape.draw(surface, self.position)

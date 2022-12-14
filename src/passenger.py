from utils import get_uuid


class Passenger:
    def __init__(self, shape) -> None:
        self.id = f"P-{get_uuid()}"
        self.shape = shape
        # passenger's holder is either a station or a metro
        self.holder = None

    def __repr__(self) -> str:
        return self.id

    def draw(self, surface):
        self.shape.draw(surface, self.position)

    def set_holder(self, holder):
        self.holder = holder

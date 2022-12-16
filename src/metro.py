from config import metro_capacity, metro_color, metro_size
from geometry.rect import Rect
from holder import Holder
from utils import uuid


class Metro(Holder):
    def __init__(self) -> None:
        metro_shape = Rect(color=metro_color, width=3 * metro_size, height=metro_size)
        super().__init__(
            shape=metro_shape,
            capacity=metro_capacity,
            id=f"M-{uuid.uuid4()}",
        )

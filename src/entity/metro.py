from uuid import uuid4

from config import metro_capacity, metro_color, metro_size, metro_speed_per_ms
from entity.holder import Holder
from geometry.line import Line
from geometry.rect import Rect


class Metro(Holder):
    def __init__(self) -> None:
        metro_shape = Rect(color=metro_color, width=2 * metro_size, height=metro_size)
        super().__init__(
            shape=metro_shape,
            capacity=metro_capacity,
            id=f"Metro-{uuid4()}",
        )
        self.is_in_station = True
        self.is_waiting = True
        self.current_line: Line | None = None
        self.current_line_idx = 0
        self.speed = metro_speed_per_ms
        self.is_forward = True

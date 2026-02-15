from config import (
    metro_accel_time_ms,
    metro_boarding_time_per_passenger_ms,
    metro_capacity,
    metro_color,
    metro_decel_time_ms,
    metro_passengers_per_row,
    metro_size,
    metro_speed_per_ms,
)
from entity.holder import Holder
from entity.segment import Segment
from entity.station import Station
from geometry.rect import Rect
from shortuuid import uuid  # type: ignore


class Metro(Holder):
    def __init__(self) -> None:
        self.size = metro_size
        metro_shape = Rect(color=metro_color, width=2 * self.size, height=self.size)
        super().__init__(
            shape=metro_shape,
            capacity=metro_capacity,
            id=f"Metro-{uuid()}",
        )
        self.current_station: Station | None = None
        self.current_segment: Segment | None = None
        self.current_segment_idx = 0
        self.path_id = ""
        self.max_speed = metro_speed_per_ms
        self.speed = self.max_speed
        self.acceleration_per_ms = self.max_speed / metro_accel_time_ms
        self.deceleration_per_ms = self.max_speed / metro_decel_time_ms
        self.is_forward = True
        self.passengers_per_row = metro_passengers_per_row
        self.stop_time_remaining_ms = 0
        self.boarding_progress_ms = 0
        self.boarding_time_per_passenger_ms = metro_boarding_time_per_passenger_ms
        self.just_arrived_and_stopped = False

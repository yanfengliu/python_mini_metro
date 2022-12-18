from __future__ import annotations

from entity.path import Path
from entity.station import Station


class TravelPlan:
    def __init__(
        self, get_on_path: Path | None, then_get_off_station: Station | None
    ) -> None:
        self.get_on_path = get_on_path
        self.get_off_station = then_get_off_station

    def __repr__(self) -> str:
        return f"TravelPlan = get on {self.get_on_path}, then get off at {self.get_off_station}"

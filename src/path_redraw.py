"""Pure transient state for one selected-line redraw gesture."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class PathRedrawGesture:
    """An immutable off-live route draft owned by the active facade."""

    path: Any
    stations: tuple[Any, ...] = ()
    loop: bool = False
    temp_point: Any | None = None
    invalid: bool = False
    handle_edit: Any | None = None

    @property
    def is_valid(self) -> bool:
        return not self.invalid and len(self.stations) >= 2

    def move_to(self, point: Any) -> PathRedrawGesture:
        return replace(self, temp_point=point)

    def enter_station(
        self, station: Any, point: Any | None = None
    ) -> PathRedrawGesture:
        station_point = getattr(station, "position", None)
        temp_point = point if station_point is None else station_point
        if self.invalid:
            return replace(self, temp_point=temp_point)
        if self.stations and station is self.stations[-1]:
            return replace(self, temp_point=temp_point)
        if self.loop and station is self.stations[0]:
            return replace(self, temp_point=temp_point)

        matches = [
            index for index, captured in enumerate(self.stations) if captured is station
        ]
        if matches:
            if matches == [0] and len(self.stations) >= 2:
                return replace(self, loop=True, temp_point=temp_point)
            return replace(self, invalid=True, temp_point=temp_point)
        return replace(
            self,
            stations=(*self.stations, station),
            loop=False,
            temp_point=temp_point,
        )

    def station_indices(self, active_stations: Sequence[Any]) -> list[int] | None:
        if self.invalid:
            return None
        resolved: list[int] = []
        for station in self.stations:
            matches = [
                index
                for index, candidate in enumerate(active_stations)
                if candidate is station
            ]
            if len(matches) != 1:
                return None
            resolved.append(matches[0])
        return resolved

from __future__ import annotations

from typing import List

from entity.path import Path
from entity.station import Station
from graph.node import Node


class TravelPlan:
    def __init__(
        self,
        node_path: List[Node],
    ) -> None:
        self.next_path: Path | None = None
        self.next_station: Station | None = None
        self.node_path = node_path

    def get_next_station(self) -> Station | None:
        if self.node_path is not None and len(self.node_path) > 0:
            next_node = self.node_path.pop(0)
            next_station = next_node.station
            self.next_station = next_station
            return next_station
        else:
            return None

    def __repr__(self) -> str:
        return (
            f"TravelPlan = get on {self.next_path}, then get off at {self.next_station}"
        )

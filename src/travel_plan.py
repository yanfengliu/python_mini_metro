from __future__ import annotations

from typing import List

from entity.path import Path
from entity.airport import airport
from graph.node import Node

# determines what trains passengers need to go on -- does BFS essentially 
class TravelPlan:
    def __init__(
        self,
        node_path: List[Node],
    ) -> None:
        self.next_path: Path | None = None
        self.next_airport: airport | None = None
        self.node_path = node_path
        self.next_airport_idx = 0

    def get_next_airport(self) -> airport | None:
        if self.node_path is not None and len(self.node_path) > 0:
            next_node = self.node_path[self.next_airport_idx]
            next_airport = next_node.airport
            self.next_airport = next_airport
            return next_airport
        else:
            return None

    def increment_next_airport(self) -> None:
        self.next_airport_idx += 1

    def __repr__(self) -> str:
        return (
            f"TravelPlan = get on {self.next_path}, then get off at {self.next_airport}"
        )

from __future__ import annotations

from typing import Set

from shortuuid import uuid  # type: ignore

from entity.station import Station


class Node:
    def __init__(self, station: Station) -> None:
        self.id = f"Node-{uuid()}"
        self.station = station
        self.neighbors: Set[Node] = set()

    def __eq__(self, other: Node) -> bool:
        return self.station == other.station

    def __hash__(self) -> int:
        return hash(self.id)

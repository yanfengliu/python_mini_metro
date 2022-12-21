from __future__ import annotations

from typing import Set

from shortuuid import uuid  # type: ignore

from entity.path import Path
from entity.station import Station


class Node:
    def __init__(self, station: Station) -> None:
        self.id = f"Node-{uuid()}"
        self.station = station
        self.neighbors: Set[Node] = set()
        self.paths: Set[Path] = set()

    def __eq__(self, other: Node) -> bool:
        return self.station == other.station

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Node-{self.station.__repr__()}"

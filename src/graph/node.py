from __future__ import annotations

from typing import Set

from shortuuid import uuid  # type: ignore

from entity.path import Path
from entity.airport import airport


class Node:
    def __init__(self, airport: airport) -> None:
        self.id = f"Node-{uuid()}"
        self.airport = airport
        self.neighbors: Set[Node] = set()
        self.paths: Set[Path] = set()

    def __eq__(self, other: Node) -> bool:
        return self.airport == other.airport

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Node-{self.airport.__repr__()}"

from __future__ import annotations

from collections.abc import Iterator, MutableSet

from shortuuid import uuid  # type: ignore

from entity.path import Path
from entity.station import Station


class Node:
    def __init__(self, station: Station) -> None:
        self.id = f"Node-{uuid()}"
        self.station = station
        self.neighbors: MutableSet[Node] = _OrderedNodeSet()
        self.paths: set[Path] = set()

    def __eq__(self, other: Node) -> bool:
        return self.station == other.station

    def __hash__(self) -> int:
        return hash(self.station)

    def __repr__(self) -> str:
        return f"Node-{self.station.__repr__()}"


class _OrderedNodeSet(MutableSet[Node]):
    def __init__(self) -> None:
        self._nodes: dict[Node, None] = {}

    def __contains__(self, node: object) -> bool:
        return node in self._nodes

    def __iter__(self) -> Iterator[Node]:
        return iter(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)

    def add(self, node: Node) -> None:
        self._nodes[node] = None

    def discard(self, node: Node) -> None:
        self._nodes.pop(node, None)

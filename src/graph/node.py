from __future__ import annotations

from collections.abc import Iterator, MutableSet

from shortuuid import uuid  # type: ignore

from entity.path import Path
from entity.station import Station


class Node:
    def __init__(self, station: Station) -> None:
        self.station = station
        self.neighbors: MutableSet[Node] = _OrderedNodeSet()
        self.paths: set[Path] = set()
        self._id: str | None = None

    @property
    def id(self) -> str:
        """Generated on first read, because almost nothing ever reads it.

        The routing graph is rebuilt from scratch about 24 times per simulation
        step, so at ten stations this was ~240 uuid generations per step --
        measured at 1.98 of 25.6 seconds in a profiled episode, near 8% of the
        whole simulation. Nothing on that path needs it: equality and hashing
        use `station`, and so does the repr.
        """
        if self._id is None:
            self._id = f"Node-{uuid()}"
        return self._id

    @id.setter
    def id(self, value: str) -> None:
        """Kept writable. It was a plain attribute before becoming lazy, and
        every sibling entity (Path, Station, Metro, Carriage) is assigned one by
        `save_load`; making Node the sole read-only exception would bite exactly
        when Node first enters the save schema.
        """
        self._id = value

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

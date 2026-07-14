from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar


@dataclass(frozen=True)
class FakeShape:
    type: str


@dataclass(eq=False)
class FakeStation:
    name: str
    shape_type: str
    passengers: list[FakePassenger] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.shape = FakeShape(self.shape_type)


@dataclass(eq=False)
class FakePath:
    id: str
    stations: list[FakeStation]
    is_being_created: bool = False


@dataclass(eq=False)
class FakeNode:
    station: FakeStation
    paths: set[FakePath] = field(default_factory=set)


@dataclass(eq=False)
class FakePassenger:
    name: str
    destination_type: str
    is_at_destination: bool = False

    def __post_init__(self) -> None:
        self.destination_shape = FakeShape(self.destination_type)


class FakeTravelPlan:
    def __init__(self, node_path: list[FakeNode]) -> None:
        self.next_path: FakePath | None = None
        self.next_station: FakeStation | None = None
        self.node_path = node_path
        self.next_station_idx = 0
        self.get_next_station_calls = 0

    def get_next_station(self) -> FakeStation | None:
        self.get_next_station_calls += 1
        if not self.node_path:
            return None
        self.next_station = self.node_path[self.next_station_idx].station
        return self.next_station


Key = TypeVar("Key")
Value = TypeVar("Value")


class LoggingMapping(dict[Key, Value], Generic[Key, Value]):
    def __init__(self, values: dict[Key, Value]) -> None:
        super().__init__(values)
        self.accesses: list[Key] = []

    def __getitem__(self, key: Key) -> Value:
        self.accesses.append(key)
        return super().__getitem__(key)


def station(name: str, shape_type: str = "circle") -> FakeStation:
    return FakeStation(name, shape_type)


def node(value: FakeStation, *paths: FakePath) -> FakeNode:
    return FakeNode(value, set(paths))


def path(path_id: str, *stations: FakeStation) -> FakePath:
    return FakePath(path_id, list(stations))

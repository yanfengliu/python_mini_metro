"""Public pure state and hit API for selected-route edit handles."""

from __future__ import annotations

import math
import weakref
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any

if __package__ == "src":
    from . import config as cfg
    from .path_handle_geometry import HandleKind, PathHandle, Position
    from .path_handle_geometry import (
        build_path_handles_for_state as build_path_handles_for_state,
    )
else:
    import config as cfg
    from path_handle_geometry import HandleKind, PathHandle, Position
    from path_handle_geometry import (
        build_path_handles_for_state as build_path_handles_for_state,
    )


@dataclass(frozen=True, slots=True)
class PathHandleHit:
    handle: PathHandle | None
    ambiguous: bool = False


@dataclass(frozen=True, slots=True)
class PathHandlePreviewSpec:
    stations: tuple[Any, ...]
    loop: bool
    temp_point: Position | None
    temp_insertion_index: int | None
    invalid: bool
    removal_segment: tuple[Position, ...] = ()


class PathEditSelection:
    """Weak selection that resolves only one exact active identity."""

    __slots__ = ("path_ref",)

    def __init__(self, path: Any) -> None:
        self.path_ref: weakref.ReferenceType[Any] = weakref.ref(path)

    def resolve(self, paths: Iterable[Any]) -> Any | None:
        path = self.path_ref()
        try:
            matches = [] if path is None else [item for item in paths if item is path]
        except TypeError:
            return None
        return path if len(matches) == 1 else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _position(value: Any) -> Position | None:
    try:
        raw = (value.left, value.top) if hasattr(value, "left") else value[:2]
        left, top = _number(raw[0]), _number(raw[1])
    except (AttributeError, IndexError, KeyError, TypeError):
        return None
    return None if left is None or top is None else (left, top)


def _identity_unique(values: Sequence[Any]) -> bool:
    return len(values) == len({id(value) for value in values})


def _same_identities(value: Any, expected: Sequence[Any]) -> bool:
    try:
        actual = tuple(value)
    except TypeError:
        return False
    return len(actual) == len(expected) and all(
        left is right for left, right in zip(actual, expected)
    )


def _valid_edge(stations: Sequence[Any], edge: tuple[int, int]) -> bool:
    points = tuple(
        _position(getattr(stations[index], "position", None)) for index in edge
    )
    return None not in points and math.dist(*points) > 0  # type: ignore[arg-type]


def hit_test_path_handles(handles: Iterable[PathHandle], point: Any) -> PathHandleHit:
    """Resolve only a unique nearest visible hit envelope."""

    target = _position(point)
    if target is None:
        return PathHandleHit(None)
    try:
        values = tuple(handles)
    except TypeError:
        return PathHandleHit(None)
    hits = []
    for handle in values:
        if not isinstance(handle, PathHandle):
            continue
        center, radius = _position(handle.center), _number(handle.hit_radius)
        if center is not None and radius is not None and radius > 0:
            distance = math.dist(target, center)
            if distance <= radius:
                hits.append((distance, handle))
    if not hits:
        return PathHandleHit(None)
    nearest = min(distance for distance, _ in hits)
    winners = [
        handle
        for distance, handle in hits
        if math.isclose(distance, nearest, rel_tol=0.0, abs_tol=1e-9)
    ]
    return PathHandleHit(winners[0]) if len(winners) == 1 else PathHandleHit(None, True)


@dataclass(frozen=True, slots=True)
class PathHandleEdit:
    """Immutable off-live edit retaining its exact source while active."""

    path: Any
    source_stations: tuple[Any, ...]
    source_loop: bool
    kind: HandleKind
    slot: int
    path_id: str
    point: Position | None = None
    station: Any | None = None

    @classmethod
    def begin(cls, path: Any, handle: Any) -> PathHandleEdit | None:
        if not isinstance(handle, PathHandle):
            return None
        try:
            stations = tuple(path.stations)
        except (AttributeError, TypeError):
            return None
        path_id, loop = getattr(path, "id", None), getattr(path, "is_looped", None)
        if (
            not isinstance(path_id, str)
            or not path_id
            or path_id != handle.path_id
            or type(loop) is not bool
            or len(stations) < 2
            or not _identity_unique(stations)
            or not cls._valid_handle(stations, loop, handle)
        ):
            return None
        return cls(path, stations, loop, handle.kind, handle.slot, path_id)

    @staticmethod
    def _valid_handle(stations: Sequence[Any], loop: bool, handle: PathHandle) -> bool:
        if (
            type(handle.slot) is not int
            or _position(handle.anchor) is None
            or _position(handle.center) is None
            or _number(handle.hit_radius) != float(cfg.path_handle_hit_radius)
        ):
            return False
        count = len(stations)
        if handle.kind == "start":
            valid, edge = not loop and handle.slot == 0, (0, 1)
        elif handle.kind == "end":
            valid, edge = not loop and handle.slot == count, (count - 2, count - 1)
        elif handle.kind == "insert":
            slots = {1} if loop and count == 2 else set(range(1, count + int(loop)))
            valid, edge = handle.slot in slots, (handle.slot - 1, handle.slot % count)
        else:
            return False
        return valid and _valid_edge(stations, edge)

    def move_to(self, point: Any, station: Any | None = None) -> PathHandleEdit:
        return replace(self, point=_position(point), station=station)

    def _candidate(self, target: Any) -> tuple[tuple[Any, ...], bool, bool]:
        matches = [
            index for index, value in enumerate(self.source_stations) if value is target
        ]
        if self.kind == "insert":
            values = list(self.source_stations)
            if matches:
                return (self.source_stations, self.source_loop, True)
            values.insert(self.slot, target)
            return (tuple(values), self.source_loop, False)
        endpoint = 0 if self.kind == "start" else len(self.source_stations) - 1
        adjacent = 1 if self.kind == "start" else len(self.source_stations) - 2
        if matches == [endpoint]:
            return (self.source_stations, False, False)
        if matches == [adjacent]:
            values = (
                self.source_stations[1:]
                if self.kind == "start"
                else self.source_stations[:-1]
            )
            return (values, False, len(values) < 2)
        if matches:
            return (self.source_stations, False, True)
        values = list(self.source_stations)
        values.insert(0 if self.kind == "start" else len(values), target)
        return (tuple(values), False, False)

    @property
    def preview_spec(self) -> PathHandlePreviewSpec:
        insertion = 0 if self.kind == "start" else self.slot
        if self.station is None:
            return PathHandlePreviewSpec(
                self.source_stations,
                self.source_loop,
                self.point,
                insertion,
                self.point is None,
            )
        stations, loop, invalid = self._candidate(self.station)
        source_match = any(value is self.station for value in self.source_stations)
        removal: tuple[Position, ...] = ()
        if not invalid and source_match and stations != self.source_stations:
            pair = (
                self.source_stations[:2]
                if self.kind == "start"
                else tuple(reversed(self.source_stations[-2:]))
            )
            points = tuple(_position(value.position) for value in pair)
            if None not in points:
                removal = points  # type: ignore[assignment]
        neutral = stations == self.source_stations and source_match and not invalid
        return PathHandlePreviewSpec(
            stations,
            loop,
            self.point if invalid else None,
            None if neutral or removal else insertion,
            invalid,
            removal,
        )

    def result(
        self,
        paths: Iterable[Any],
        stations: Sequence[Any],
        release_station: Any,
    ) -> tuple[Any, list[int], bool] | None:
        try:
            active_paths, active_stations = tuple(paths), tuple(stations)
        except TypeError:
            return None
        stale = (
            sum(value is self.path for value in active_paths) != 1
            or getattr(self.path, "id", None) != self.path_id
            or getattr(self.path, "is_looped", None) is not self.source_loop
            or not _same_identities(
                getattr(self.path, "stations", None), self.source_stations
            )
            or sum(value is release_station for value in active_stations) != 1
        )
        if stale:
            return None
        candidate, loop, invalid = self._candidate(release_station)
        if invalid or candidate == self.source_stations:
            return None
        resolved = []
        for station in candidate:
            matches = [
                index for index, value in enumerate(active_stations) if value is station
            ]
            if len(matches) != 1:
                return None
            resolved.append(matches[0])
        return (self.path, resolved, loop)

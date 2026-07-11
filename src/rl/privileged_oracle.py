"""Explicitly privileged inspection for tests and scripted curricula.

This module is intentionally separate from ``PlayerPixelEnv``. Training policies must
not receive these snapshots; they exist to validate and bootstrap the pixel task.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class _PlayerEnvInternals(Protocol):
    _mediator: Any


@dataclass(frozen=True, slots=True)
class PrivilegedSnapshot:
    station_positions: tuple[tuple[int, int], ...]
    path_station_indices: tuple[tuple[int | None, ...], ...]
    deliveries: int
    display_score: int
    simulation_time_ms: int
    is_paused: bool


def capture_privileged_snapshot(env: _PlayerEnvInternals) -> PrivilegedSnapshot:
    """Capture immutable hidden state for validation, never policy observations."""

    mediator = getattr(env, "_mediator", None)
    if mediator is None:
        raise RuntimeError("environment must be reset before privileged inspection")
    station_indices = {
        id(station): index for index, station in enumerate(mediator.stations)
    }
    return PrivilegedSnapshot(
        station_positions=tuple(
            (
                int(round(float(station.position.left))),
                int(round(float(station.position.top))),
            )
            for station in mediator.stations
        ),
        path_station_indices=tuple(
            tuple(station_indices.get(id(station)) for station in path.stations)
            for path in mediator.paths
        ),
        deliveries=int(mediator.total_travels_handled),
        display_score=int(mediator.score),
        simulation_time_ms=int(mediator.time_ms),
        is_paused=bool(mediator.is_paused),
    )

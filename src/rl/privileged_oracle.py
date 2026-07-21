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
    fleet_control_positions: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    deliveries: int
    line_credits: int
    simulation_time_ms: int
    is_paused: bool

    @property
    def display_score(self) -> int:
        """Legacy alias for the spendable line-credit balance."""

        return self.line_credits


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
        fleet_control_positions=_fleet_control_positions(mediator),
        deliveries=int(
            getattr(
                mediator,
                "deliveries",
                getattr(mediator, "total_travels_handled", 0),
            )
        ),
        line_credits=int(
            getattr(
                mediator,
                "line_credits",
                getattr(mediator, "score", 0),
            )
        ),
        simulation_time_ms=int(mediator.time_ms),
        is_paused=bool(mediator.is_paused),
    )


def _fleet_control_positions(
    mediator: Any,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    paths = tuple(getattr(mediator, "paths", ()))
    if not paths:
        return ()
    path_buttons = tuple(getattr(mediator, "path_buttons", ()))
    fleet_buttons = tuple(getattr(mediator, "fleet_buttons", ()))
    positions = []
    for path in paths:
        owners = tuple(
            button for button in path_buttons if getattr(button, "path", None) is path
        )
        if len(owners) != 1:
            continue
        controls = tuple(
            control
            for control in fleet_buttons
            if getattr(control, "path_button", None) is owners[0]
        )
        by_operation = {
            getattr(control, "operation", None): control for control in controls
        }
        if set(by_operation) != {"assign", "unassign"}:
            continue
        pair = []
        for operation in ("assign", "unassign"):
            position = by_operation[operation].position
            pair.append(
                (
                    int(round(float(position.left))),
                    int(round(float(position.top))),
                )
            )
        positions.append((pair[0], pair[1]))
    return tuple(positions)

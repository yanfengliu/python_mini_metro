"""Deterministic low-level demonstrations for curriculum and smoke testing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np
import numpy.typing as npt

from rl.privileged_oracle import capture_privileged_snapshot
from rl.protocol import ActionKind, TaskSpec, canonical_to_action_coordinate

DEMONSTRATION_SEED = 0
VERIFIED_DELIVERY_MAX_DECISIONS = 122

ActionArray = npt.NDArray[np.int64]


class DemonstrationEnv(Protocol):
    """Narrow environment surface needed by the privileged demonstrator."""

    task_spec: TaskSpec

    def reset(
        self, *, seed: int | None = None
    ) -> tuple[npt.NDArray[np.uint8], dict[str, Any]]: ...

    def step(
        self, action: ActionArray
    ) -> tuple[npt.NDArray[np.uint8], float, bool, bool, dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class DemonstrationResult:
    """Executed player actions and metrics exposed by the public environment API."""

    actions: tuple[ActionArray, ...]
    metrics: dict[str, Any]


def _action(kind: ActionKind, x: int = 0, y: int = 0) -> ActionArray:
    return np.asarray([kind.value, x, y], dtype=np.int64)


def pause_resume_action() -> ActionArray:
    """Return the player's SPACE key-up action, which toggles pause state."""

    return _action(ActionKind.SPACE)


def speed_action(multiplier: int) -> ActionArray:
    """Return the number-key action for the requested player speed."""

    if isinstance(multiplier, bool) or not isinstance(multiplier, int):
        raise TypeError("speed multiplier must be an integer")
    try:
        kind = {
            1: ActionKind.KEY_1,
            2: ActionKind.KEY_2,
            4: ActionKind.KEY_3,
        }[multiplier]
    except KeyError as error:
        raise ValueError("speed multiplier must be 1, 2, or 4") from error
    return _action(kind)


def _station_action_coordinate(
    env: DemonstrationEnv, station_index: int
) -> tuple[int, int]:
    position = capture_privileged_snapshot(env).station_positions[station_index]
    return canonical_to_action_coordinate(
        position[0],
        position[1],
        env.task_spec.render_profile,
    )


def drag_route_actions(
    env: DemonstrationEnv,
    station_indices: Sequence[int],
    loop: bool = False,
) -> tuple[ActionArray, ...]:
    """Build a player drag across visible stations without applying it.

    This curriculum helper is intentionally privileged: it reads station centers from
    the mediator, quantizes them into the agent's coordinate grid, and returns only
    low-level DOWN/MOTION/UP actions. Callers still apply every action through
    ``env.step``.
    """

    if type(loop) is not bool:
        raise TypeError("loop must be a boolean")
    if isinstance(station_indices, (str, bytes)) or not isinstance(
        station_indices, Sequence
    ):
        raise TypeError("station_indices must be a sequence of integers")
    indices = tuple(station_indices)
    if len(indices) < 2:
        raise ValueError("a route requires at least two stations")
    if any(isinstance(index, bool) or not isinstance(index, int) for index in indices):
        raise TypeError("station indices must be integers")
    if len(set(indices)) != len(indices):
        raise ValueError("station indices must be distinct")
    station_count = len(capture_privileged_snapshot(env).station_positions)
    if any(index < 0 or index >= station_count for index in indices):
        raise IndexError(f"station index is outside [0, {station_count - 1}]")

    coordinates = tuple(
        _station_action_coordinate(env, station_index) for station_index in indices
    )
    actions = [_action(ActionKind.DOWN, *coordinates[0])]
    actions.extend(
        _action(ActionKind.MOTION, *position) for position in coordinates[1:]
    )
    release_position = coordinates[-1]
    if loop:
        release_position = coordinates[0]
        actions.append(_action(ActionKind.MOTION, *release_position))
    actions.append(_action(ActionKind.UP, *release_position))
    return tuple(actions)


def _validate_max_decisions(max_decisions: int) -> int:
    if isinstance(max_decisions, bool) or not isinstance(max_decisions, int):
        raise TypeError("max_decisions must be an integer")
    if max_decisions <= 0:
        raise ValueError("max_decisions must be positive")
    return max_decisions


def _assign_locomotive_actions(env: DemonstrationEnv) -> tuple[ActionArray, ...]:
    controls = capture_privileged_snapshot(env).fleet_control_positions
    if not controls:
        raise RuntimeError("completed route did not expose a fleet assignment control")
    position = controls[0][0]
    coordinate = canonical_to_action_coordinate(
        position[0], position[1], env.task_spec.render_profile
    )
    return (
        _action(ActionKind.DOWN, *coordinate),
        _action(ActionKind.UP, *coordinate),
    )


def _attach_carriage_actions(env: DemonstrationEnv) -> tuple[ActionArray, ...]:
    controls = capture_privileged_snapshot(env).carriage_control_positions
    if not controls:
        raise RuntimeError("completed route did not expose a carriage control")
    position = controls[0][0]
    coordinate = canonical_to_action_coordinate(
        position[0], position[1], env.task_spec.render_profile
    )
    return (
        _action(ActionKind.DOWN, *coordinate),
        _action(ActionKind.UP, *coordinate),
    )


def run_delivery_demonstration(
    env: DemonstrationEnv,
    max_decisions: int,
) -> DemonstrationResult:
    """Reset seed 0, connect all initial stations, and wait for one delivery.

    Seed 0 is verified to deliver within 120 decisions under protocol version 1. The
    target selection may inspect the mediator as an explicit curriculum oracle; all
    state-changing inputs are executed through ``env.step``.
    """

    decision_limit = _validate_max_decisions(max_decisions)
    _, reset_info = env.reset(seed=DEMONSTRATION_SEED)
    station_indices = tuple(
        range(len(capture_privileged_snapshot(env).station_positions))
    )
    route_actions = drag_route_actions(env, station_indices)
    minimum_decisions = len(route_actions) + 4
    if decision_limit < minimum_decisions:
        raise ValueError(
            f"max_decisions must be at least {minimum_decisions} for route and fleet"
        )

    executed: list[ActionArray] = []
    final_info = reset_info
    terminated = False
    truncated = False
    total_reward = 0.0

    pending_actions: list[ActionArray] = list(route_actions)
    fleet_actions_pending = True
    carriage_actions_pending = True
    expected_carriage_counts: tuple[int, int] | None = None
    while len(executed) < decision_limit and not (terminated or truncated):
        if not pending_actions and fleet_actions_pending:
            pending_actions.extend(_assign_locomotive_actions(env))
            fleet_actions_pending = False
        elif not pending_actions and carriage_actions_pending:
            before = capture_privileged_snapshot(env)
            pending_actions.extend(_attach_carriage_actions(env))
            carriage_actions_pending = False
            expected_carriage_counts = (
                before.carriages_assigned + 1,
                before.carriages_available - 1,
            )
        action = pending_actions.pop(0) if pending_actions else _action(ActionKind.NOOP)
        _, reward, terminated, truncated, final_info = env.step(action)
        executed.append(action.copy())
        total_reward += float(reward)
        if expected_carriage_counts is not None and not pending_actions:
            attached = capture_privileged_snapshot(env)
            actual = (attached.carriages_assigned, attached.carriages_available)
            if actual != expected_carriage_counts:
                raise RuntimeError("demonstration carriage attachment did not commit")
            expected_carriage_counts = None
        setup_complete = (
            not fleet_actions_pending
            and not carriage_actions_pending
            and expected_carriage_counts is None
            and not pending_actions
        )
        if setup_complete and capture_privileged_snapshot(env).deliveries >= 1:
            break

    snapshot = capture_privileged_snapshot(env)
    deliveries = snapshot.deliveries
    metrics = {
        "protocol_fingerprint": final_info.get("protocol_fingerprint"),
        "task_fingerprint": final_info.get("task_fingerprint"),
        "seed": DEMONSTRATION_SEED,
        "max_decisions": decision_limit,
        "decisions": len(executed),
        "route_station_indices": station_indices,
        "deliveries": deliveries,
        "display_score": snapshot.display_score,
        "simulation_time_ms": snapshot.simulation_time_ms,
        "total_reward": total_reward,
        "completed_delivery": deliveries >= 1,
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "termination_reason": final_info.get("termination_reason"),
    }
    return DemonstrationResult(tuple(executed), metrics)

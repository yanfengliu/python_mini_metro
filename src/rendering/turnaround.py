"""Pure terminal-turnaround detection and common-pivot geometry."""

from __future__ import annotations

import math
from typing import Any, Iterable

from .layout import Position

_TAU = 2.0 * math.pi
_ANGLE_EPSILON = 1e-12
_DISTANCE_EPSILON = 1e-9
_PROJECTION_TOLERANCE = 1e-12
_CLEARANCE_TOLERANCE = 1e-6
_MAX_PROJECTION_CYCLES = 4096
_SCALE_BISECTION_STEPS = 64
_SCALE_MARGIN = 1e-10


def is_terminal_turnaround(path: Any, previous: Any, current: Any) -> bool:
    """Return whether two snapshots straddle one nonloop terminal reversal."""

    if (
        bool(getattr(path, "is_looped", False))
        or previous.path_id != current.path_id
        or previous.segment is not current.segment
        or previous.segment_index != current.segment_index
        or previous.is_forward == current.is_forward
        or current.station is None
        or (previous.station is not None and previous.station is not current.station)
    ):
        return False
    try:
        segments = tuple(path.segments)
    except (AttributeError, TypeError):
        return False
    index = current.segment_index
    if not segments or not 0 <= index < len(segments):
        return False
    if segments[index] is not current.segment:
        return False

    if current.is_forward:
        if index != 0:
            return False
        terminal = getattr(current.segment, "start_station", None)
    else:
        if index != len(segments) - 1:
            return False
        terminal = getattr(current.segment, "end_station", None)
    if terminal is None or current.station is not terminal:
        return False
    try:
        terminal_position = (
            float(terminal.position.left),
            float(terminal.position.top),
        )
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False
    return current.position == terminal_position


def _polar(position: Position, pivot: Position) -> tuple[float, float]:
    offset_x = position[0] - pivot[0]
    offset_y = position[1] - pivot[1]
    return math.hypot(offset_x, offset_y), math.atan2(offset_y, offset_x)


def _directed_delta(start: float, end: float, direction: float) -> float:
    positive = (end - start) % _TAU
    if direction > 0.0:
        return positive
    if positive <= _ANGLE_EPSILON or _TAU - positive <= _ANGLE_EPSILON:
        return 0.0
    return positive - _TAU


def _required_separation_angle(
    previous_radius: float,
    current_radius: float,
    clearance: float,
) -> float | None:
    denominator = 2.0 * previous_radius * current_radius
    if denominator <= _DISTANCE_EPSILON:
        return None
    cosine = (
        previous_radius * previous_radius
        + current_radius * current_radius
        - clearance * clearance
    ) / denominator
    return math.acos(max(-1.0, min(1.0, cosine)))


def _position_at(pivot: Position, radius: float, angle: float) -> Position:
    return (
        pivot[0] + radius * math.cos(angle),
        pivot[1] + radius * math.sin(angle),
    )


def _circular_branches(
    start_polar: tuple[tuple[float, float], ...],
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    normalized = sorted(
        (angle % _TAU, index) for index, (_, angle) in enumerate(start_polar)
    )
    if not normalized:
        return (), ()
    gaps = []
    for index, (angle, _) in enumerate(normalized):
        following = normalized[(index + 1) % len(normalized)][0]
        if index == len(normalized) - 1:
            following += _TAU
        gaps.append(following - angle)
    cut = max(range(len(gaps)), key=lambda index: (gaps[index], index))
    ordered = tuple(
        normalized[(cut + 1 + offset) % len(normalized)]
        for offset in range(len(normalized))
    )
    anchor = ordered[0][0]
    branches = [0.0] * len(normalized)
    order = []
    for angle, index in ordered:
        if angle < anchor:
            angle += _TAU
        branches[index] = angle
        order.append(index)
    offsets = tuple(
        branches[index] - start_polar[index][1] for index in range(len(branches))
    )
    return tuple(order), offsets


def _pair_clearance(
    first: int,
    second: int,
    previous_values: tuple[Position, ...],
    current_values: tuple[Position, ...],
    body_clearance: float,
) -> float:
    return min(
        body_clearance,
        math.dist(previous_values[first], previous_values[second]),
        math.dist(current_values[first], current_values[second]),
    )


def _pair_clearances(
    count: int,
    previous_values: tuple[Position, ...],
    current_values: tuple[Position, ...],
    body_clearance: float,
) -> dict[tuple[int, int], float]:
    return {
        (first, second): _pair_clearance(
            first,
            second,
            previous_values,
            current_values,
            body_clearance,
        )
        for first in range(count)
        for second in range(first + 1, count)
    }


def _angular_constraints(
    radii: tuple[float, ...],
    order: tuple[int, ...],
    clearances: dict[tuple[int, int], float],
) -> tuple[tuple[int, int, float, float], ...]:
    constraints = []
    for rank, index in enumerate(order):
        for prior in order[:rank]:
            pair = (min(prior, index), max(prior, index))
            required = _required_separation_angle(
                radii[prior],
                radii[index],
                clearances[pair],
            )
            gap = 0.0 if required is None else required
            constraints.append((prior, index, -1.0, -gap))
            constraints.append((prior, index, 1.0, _TAU - gap))
    return tuple(constraints)


def _difference_constraints_are_feasible(
    constraints: tuple[tuple[int, int, float, float], ...],
    count: int,
) -> bool:
    if count <= 1:
        return True
    distances = [0.0] * count
    for _ in range(count):
        changed = False
        for first, second, sign, bound in constraints:
            source, target = (first, second) if sign > 0.0 else (second, first)
            candidate = distances[source] + bound
            if candidate < distances[target] - _PROJECTION_TOLERANCE:
                distances[target] = candidate
                changed = True
        if not changed:
            return True
    return False


def _radii_are_feasible(
    radii: tuple[float, ...],
    order: tuple[int, ...],
    clearances: dict[tuple[int, int], float],
) -> tuple[bool, tuple[tuple[int, int, float, float], ...]]:
    constraints = _angular_constraints(radii, order, clearances)
    has_reach = all(
        radii[first] + radii[second] >= clearance - _DISTANCE_EPSILON
        for (first, second), clearance in clearances.items()
    )
    return (
        has_reach and _difference_constraints_are_feasible(constraints, len(radii)),
        constraints,
    )


def _feasible_radii(
    radii: tuple[float, ...],
    order: tuple[int, ...],
    clearances: dict[tuple[int, int], float],
) -> tuple[tuple[float, ...], tuple[tuple[int, int, float, float], ...]]:
    feasible, constraints = _radii_are_feasible(radii, order, clearances)
    if feasible:
        return radii, constraints
    if any(
        radii[first] + radii[second] <= _DISTANCE_EPSILON
        and clearance > _CLEARANCE_TOLERANCE
        for (first, second), clearance in clearances.items()
    ):
        raise ValueError("turnaround clearance is impossible at zero radius")

    lower = 1.0
    upper = 2.0
    while True:
        scaled = tuple(radius * upper for radius in radii)
        feasible, constraints = _radii_are_feasible(scaled, order, clearances)
        if feasible:
            break
        lower = upper
        upper *= 2.0
        if not math.isfinite(upper):
            raise ValueError("turnaround clearance has no finite radial solution")

    for _ in range(_SCALE_BISECTION_STEPS):
        middle = (lower + upper) / 2.0
        scaled = tuple(radius * middle for radius in radii)
        feasible, _ = _radii_are_feasible(scaled, order, clearances)
        if feasible:
            upper = middle
        else:
            lower = middle

    scale = upper + max(1.0, upper) * _SCALE_MARGIN
    scaled = tuple(radius * scale for radius in radii)
    feasible, constraints = _radii_are_feasible(scaled, order, clearances)
    if not feasible:
        raise RuntimeError("turnaround radial feasibility search did not converge")
    return scaled, constraints


def _solve_angles(
    preferred: tuple[float, ...],
    constraints: tuple[tuple[int, int, float, float], ...],
) -> tuple[float, ...]:
    if all(
        sign * (preferred[second] - preferred[first]) <= bound + _PROJECTION_TOLERANCE
        for first, second, sign, bound in constraints
    ):
        return preferred

    solved = list(preferred)
    for _ in range(_MAX_PROJECTION_CYCLES):
        before = tuple(solved)
        for first, second, sign, bound in constraints:
            violation = sign * (solved[second] - solved[first]) - bound
            if violation > 0.0:
                adjustment = violation / 2.0
                solved[first] += sign * adjustment
                solved[second] -= sign * adjustment
        maximum_violation = max(
            sign * (solved[second] - solved[first]) - bound
            for first, second, sign, bound in constraints
        )
        maximum_change = max(
            abs(value - old_value) for value, old_value in zip(solved, before)
        )
        if (
            maximum_violation <= _PROJECTION_TOLERANCE
            and maximum_change <= _PROJECTION_TOLERANCE
        ):
            return tuple(solved)
    raise RuntimeError("turnaround angular projection did not converge")


def _positions_have_clearance(
    positions: tuple[Position, ...],
    clearances: dict[tuple[int, int], float],
) -> bool:
    return all(
        math.dist(positions[first], positions[second])
        >= clearance - _CLEARANCE_TOLERANCE
        for (first, second), clearance in clearances.items()
    )


def turnaround_positions(
    previous_head: Position,
    current_head: Position,
    interpolated_head: Position,
    previous: Iterable[Position],
    current: Iterable[Position],
    alpha: float,
    heading_delta_degrees: float,
    body_clearance: float,
) -> tuple[Position, ...]:
    """Interpolate every body around one pivot toward its own endpoint ray."""

    amount = max(0.0, min(1.0, float(alpha)))
    direction = -1.0 if heading_delta_degrees < 0.0 else 1.0
    previous_values = tuple(previous)
    current_values = tuple(current)
    if amount <= 0.0:
        return previous_values
    if amount >= 1.0:
        return current_values
    start_polar = tuple(_polar(position, previous_head) for position in previous_values)
    end_polar = tuple(_polar(position, current_head) for position in current_values)
    order, offsets = _circular_branches(start_polar)
    radii = tuple(
        start_radius + (end_radius - start_radius) * amount
        for (start_radius, _), (end_radius, _) in zip(start_polar, end_polar)
    )
    preferred = tuple(
        (
            start_angle
            + _directed_delta(
                start_angle,
                end_angle,
                direction,
            )
            * amount
            + offsets[index]
        )
        for index, ((_, start_angle), (_, end_angle)) in enumerate(
            zip(start_polar, end_polar)
        )
    )
    clearances = _pair_clearances(
        len(radii),
        previous_values,
        current_values,
        body_clearance,
    )
    radii, constraints = _feasible_radii(
        radii,
        order,
        clearances,
    )
    angles = _solve_angles(preferred, constraints)
    positions = tuple(
        _position_at(interpolated_head, radius, angle)
        for radius, angle in zip(radii, angles)
    )
    if not _positions_have_clearance(positions, clearances):
        raise RuntimeError("turnaround projection violated body clearance")
    return positions


__all__ = ["is_terminal_turnaround", "turnaround_positions"]

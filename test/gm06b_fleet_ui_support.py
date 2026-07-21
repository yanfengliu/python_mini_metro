from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np
import pygame

from entity.metro import Metro
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.point import Point
from mediator import Mediator
from rl.protocol import ActionKind

_ASSIGN_NAMES = frozenset(("+", "add", "assign", "assign_locomotive", "plus"))
_UNASSIGN_NAMES = frozenset(("-", "minus", "remove", "unassign", "unassign_locomotive"))


def action(kind: ActionKind, coordinate: tuple[int, int] = (0, 0)) -> np.ndarray:
    return np.asarray([kind.value, *coordinate], dtype=np.int64)


def dispatch_mouse(mediator: Mediator, event_type: MouseEventType, target: Any) -> None:
    position = point(target)
    mediator.react_mouse_event(MouseEvent(event_type, position))


def point(value: Any) -> Point:
    position = getattr(value, "position", value)
    if isinstance(position, Point):
        return Point(position.left, position.top)
    if hasattr(position, "left") and hasattr(position, "top"):
        return Point(position.left, position.top)
    left, top = position
    return Point(left, top)


def operation(control: Any) -> str:
    for attribute in ("operation", "fleet_action", "action", "kind"):
        value = getattr(control, attribute, None)
        if hasattr(value, "value"):
            value = value.value
        if not isinstance(value, str):
            continue
        normalized = value.strip().lower()
        if normalized in _ASSIGN_NAMES:
            return "assign"
        if normalized in _UNASSIGN_NAMES:
            return "unassign"
    raise AssertionError("FleetButton must expose an assign/unassign operation label")


def fleet_controls(mediator: Mediator) -> tuple[Any, ...]:
    established = {id(button) for button in mediator.path_buttons}
    established.update(id(button) for button in mediator.speed_buttons)
    controls = tuple(
        button for button in mediator.buttons if id(button) not in established
    )
    expected_count = 2 * len(mediator.path_buttons)
    if len(controls) != expected_count:
        raise AssertionError(
            f"expected {expected_count} FleetButtons in Mediator.buttons, got "
            f"{len(controls)}"
        )
    if len({id(control) for control in controls}) != len(controls):
        raise AssertionError("FleetButtons must occur exactly once in Mediator.buttons")
    return controls


def control_pair(mediator: Mediator, path_button: Any) -> tuple[Any, Any]:
    controls = tuple(
        control
        for control in fleet_controls(mediator)
        if getattr(control, "path_button", None) is path_button
    )
    if len(controls) != 2:
        raise AssertionError("each PathButton must own exactly two FleetButtons")
    by_operation = {operation(control): control for control in controls}
    if set(by_operation) != {"assign", "unassign"}:
        raise AssertionError(
            "each PathButton needs one assign and one unassign control"
        )
    return by_operation["assign"], by_operation["unassign"]


def create_path(mediator: Mediator, indices: list[int] | None = None):
    selected = [0, 1, 2] if indices is None else indices
    path = mediator.create_path_from_station_indices(selected)
    if path is None:
        raise AssertionError(f"could not create path for stations {selected!r}")
    return path


def ensure_one_empty_metro(mediator: Mediator, path: Any) -> Metro:
    for metro in path.metros:
        if not metro.passengers and metro in mediator.metros:
            return metro
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return metro


def fresh_mediator(seed: int = 6200) -> Mediator:
    mediator = Mediator(seed=seed)
    mediator.unlocked_num_paths = min(3, len(mediator.path_buttons))
    mediator.update_path_button_lock_states()
    return mediator


def empty_point(mediator: Mediator) -> Point:
    for top in range(240, 841, 80):
        for left in range(240, 1681, 80):
            candidate = Point(left, top)
            if mediator.get_containing_entity(candidate) is None:
                return candidate
    raise AssertionError("canonical viewport has no empty test point")


def assert_hover_clear(testcase: Any, buttons: Iterable[Any]) -> None:
    for button in buttons:
        if hasattr(button, "show_cross"):
            testcase.assertFalse(button.show_cross)
        if hasattr(button, "is_hovered"):
            testcase.assertFalse(button.is_hovered)


def shape_radius(control: Any) -> float:
    shape = control.shape
    radius = getattr(shape, "radius", None)
    if isinstance(radius, (int, float)):
        return float(radius)
    width = float(getattr(shape, "width"))
    height = float(getattr(shape, "height"))
    return (width * width + height * height) ** 0.5 / 2


def crop_bytes(
    surface: pygame.Surface,
    center: Any,
    *,
    half_width: int = 42,
    half_height: int = 42,
) -> bytes:
    target = point(center)
    rect = pygame.Rect(
        round(target.left) - half_width,
        round(target.top) - half_height,
        2 * half_width + 1,
        2 * half_height + 1,
    ).clip(surface.get_rect())
    return pygame.image.tobytes(surface.subsurface(rect), "RGBA")

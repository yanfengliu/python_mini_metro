from __future__ import annotations

import importlib
import math
import os
import sys
from collections.abc import Iterable
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np
import pygame

import config
from config import station_color, station_size
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from graph.node import Node
from mediator import Mediator
from rl.protocol import ActionKind
from travel_plan import TravelPlan


def product_symbol(testcase: Any, module_name: str, symbol_name: str) -> Any:
    """Resolve a planned product symbol without turning red into collection errors."""

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        testcase.fail(f"GM-06c product module is missing: {module_name} ({error})")
    value = getattr(module, symbol_name, None)
    testcase.assertIsNotNone(
        value,
        f"GM-06c product symbol is missing: {module_name}.{symbol_name}",
    )
    return value


def require_attribute(testcase: Any, value: Any, name: str) -> Any:
    testcase.assertTrue(
        hasattr(value, name),
        f"GM-06c product attribute is missing: {type(value).__name__}.{name}",
    )
    return getattr(value, name)


def carriage_spacing(testcase: Any) -> float:
    """Derive spacing only from config-owned carriage geometry and its gap."""

    gap = require_attribute(testcase, config, "carriage_gap")
    testcase.assertGreaterEqual(gap, 0)
    for name in ("carriage_body_length", "carriage_width", "carriage_length"):
        if hasattr(config, name):
            body_length = getattr(config, name)
            break
    else:
        size = require_attribute(testcase, config, "carriage_size")
        body_length = 2 * size
    testcase.assertGreater(body_length, 0)
    return float(body_length + gap)


def make_two_station_game(
    *,
    seed: int = 6300,
    distance: float = 400.0,
) -> tuple[Mediator, Station, Station, Path, Metro]:
    mediator = Mediator(seed=seed)
    start = Station(
        Rect(station_color, 2 * station_size, 2 * station_size),
        Point(100, 200),
    )
    end = Station(
        Circle(station_color, station_size),
        Point(100 + distance, 200),
    )
    mediator.stations = [start, end]
    mediator.all_stations = [start, end]
    path = Path((20, 80, 140))
    path.add_station(start)
    path.add_station(end)
    metro = Metro()
    path.add_metro(metro)
    metro.current_station = start
    metro.position = start.position
    mediator.paths = [path]
    mediator.metros = [metro]
    mediator.path_to_color = {path: path.color}
    mediator.is_passenger_spawn_time = lambda: False
    return mediator, start, end, path, metro


def passenger_for(destination: Station, *, name: str | None = None) -> Passenger:
    passenger = Passenger(destination.shape)
    if name is not None:
        passenger.id = name
    return passenger


def boardable_passenger(
    mediator: Mediator,
    station: Station,
    destination: Station,
    path: Path,
    *,
    name: str,
) -> Passenger:
    passenger = passenger_for(destination, name=name)
    station.add_passenger(passenger)
    mediator.passengers.append(passenger)
    plan = TravelPlan([Node(destination)])
    plan.next_path = path
    mediator.travel_plans[passenger] = plan
    return passenger


def onboard_passenger(
    mediator: Mediator,
    metro: Metro,
    destination: Station,
    *,
    name: str,
    next_station: Station | None = None,
) -> Passenger:
    passenger = passenger_for(destination, name=name)
    metro.add_passenger(passenger)
    mediator.passengers.append(passenger)
    if next_station is not None:
        mediator.travel_plans[passenger] = TravelPlan([Node(next_station)])
    return passenger


def action(kind: ActionKind, coordinate: tuple[int, int] = (0, 0)) -> np.ndarray:
    return np.asarray([kind.value, *coordinate], dtype=np.int64)


def point(value: Any) -> Point:
    position = getattr(value, "position", value)
    if isinstance(position, Point):
        return Point(position.left, position.top)
    if hasattr(position, "left") and hasattr(position, "top"):
        return Point(position.left, position.top)
    left, top = position
    return Point(left, top)


def dispatch_mouse(mediator: Mediator, event_type: MouseEventType, target: Any) -> None:
    mediator.react_mouse_event(MouseEvent(event_type, point(target)))


def control_operation(control: Any) -> str:
    aliases = {
        "assign": "assign_locomotive",
        "assign_locomotive": "assign_locomotive",
        "unassign": "unassign_locomotive",
        "unassign_locomotive": "unassign_locomotive",
        "attach": "attach_carriage",
        "attach_carriage": "attach_carriage",
        "detach": "detach_carriage",
        "detach_carriage": "detach_carriage",
    }
    for attribute in ("operation", "fleet_action", "action", "kind"):
        value = getattr(control, attribute, None)
        if hasattr(value, "value"):
            value = value.value
        if isinstance(value, str) and value.strip().lower() in aliases:
            return aliases[value.strip().lower()]
    raise AssertionError(f"resource control has no recognized operation: {control!r}")


def resource_controls(mediator: Mediator) -> tuple[Any, ...]:
    excluded = {id(button) for button in mediator.path_buttons}
    excluded.update(id(button) for button in mediator.speed_buttons)
    controls = tuple(
        button for button in mediator.buttons if id(button) not in excluded
    )
    expected = 4 * len(mediator.path_buttons)
    if len(controls) != expected:
        raise AssertionError(
            f"expected {expected} resource controls in state.buttons, got "
            f"{len(controls)}"
        )
    if len({id(control) for control in controls}) != len(controls):
        raise AssertionError(
            "resource controls must occur exactly once in state.buttons"
        )
    return controls


def control_group(mediator: Mediator, path_button: Any) -> dict[str, Any]:
    controls = tuple(
        control
        for control in resource_controls(mediator)
        if getattr(control, "path_button", None) is path_button
    )
    if len(controls) != 4:
        raise AssertionError("every PathButton must own exactly four resource controls")
    by_operation = {control_operation(control): control for control in controls}
    expected = {
        "assign_locomotive",
        "unassign_locomotive",
        "attach_carriage",
        "detach_carriage",
    }
    if set(by_operation) != expected:
        raise AssertionError(
            f"resource group operations were {sorted(by_operation)}, expected "
            f"{sorted(expected)}"
        )
    return by_operation


def center_tuple(value: Any) -> tuple[int, int]:
    value = getattr(value, "position", value)
    if hasattr(value, "to_tuple"):
        value = value.to_tuple()
    if hasattr(value, "left") and hasattr(value, "top"):
        value = (value.left, value.top)
    return tuple(int(round(float(part))) for part in value)


def shape_radius(value: Any) -> float:
    shape = value.shape
    radius = getattr(shape, "radius", None)
    if isinstance(radius, (int, float)):
        return float(radius)
    width = float(getattr(shape, "width"))
    height = float(getattr(shape, "height"))
    return math.hypot(width, height) / 2


def assert_pairwise_disjoint(testcase: Any, controls: Iterable[Any]) -> None:
    values = tuple(controls)
    for index, first in enumerate(values):
        first_point = point(first)
        for second in values[index + 1 :]:
            second_point = point(second)
            distance = math.hypot(
                first_point.left - second_point.left,
                first_point.top - second_point.top,
            )
            testcase.assertGreater(
                distance,
                shape_radius(first) + shape_radius(second),
                f"controls overlap: {first!r}, {second!r}",
            )


def surface_bytes(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGBA")

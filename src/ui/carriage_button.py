from __future__ import annotations

from typing import Any, Literal

import pygame

from config import (
    button_size,
    carriage_button_border_color,
    carriage_button_border_width,
    carriage_button_disabled_color,
    carriage_button_disabled_icon_color,
    carriage_button_enabled_color,
    carriage_button_hover_color,
    carriage_button_icon_color,
    carriage_button_icon_width,
    carriage_button_radius,
    fleet_button_radius,
    num_paths,
    path_button_buffer,
    path_button_buy_text_bottom_gap,
    path_button_dist_to_bottom,
    path_handle_quantization_margin,
    resource_control_horizontal_offsets,
    resource_control_vertical_offset,
    speed_button_buffer,
    speed_button_dist_to_bottom,
    speed_button_height,
    speed_button_left_padding,
    speed_button_width,
    station_size,
)
from geometry.circle import Circle
from geometry.point import Point
from ui.button import Button
from ui.path_button import PathButton

CarriageOperation = Literal["attach", "detach"]


class CarriageButton(Button):
    """A carriage action bound only to one stable PathButton slot."""

    def __init__(
        self,
        path_button: PathButton,
        operation: CarriageOperation,
    ) -> None:
        super().__init__(Circle(carriage_button_enabled_color, carriage_button_radius))
        self.position = Point(0, 0)
        self.shape.position = self.position
        self.path_button = path_button
        self.operation = operation
        self.is_hovered = False

    def on_hover(self) -> None:
        self.is_hovered = True

    def on_exit(self) -> None:
        self.is_hovered = False

    def on_click(self) -> None:
        return

    def _active_path(self, state: Any) -> Any | None:
        path = self.path_button.path
        paths = getattr(state, "paths", ())
        if (
            path is None
            or self.path_button.is_locked
            or sum(candidate is path for candidate in paths) != 1
        ):
            return None
        return path

    def _is_enabled(self, state: Any, path: Any | None) -> bool:
        if path is None:
            return False
        method_name = (
            "can_attach_carriage"
            if self.operation == "attach"
            else "can_detach_carriage"
        )
        method = getattr(state, method_name, None)
        try:
            return bool(method(path)) if callable(method) else False
        except Exception:
            return False

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        state: Any | None = None,
        resources: Any | None = None,
    ) -> None:
        del current_time_ms, resources
        path = self._active_path(state) if state is not None else None
        enabled = self._is_enabled(state, path) if state is not None else False
        fill = (
            carriage_button_enabled_color if enabled else carriage_button_disabled_color
        )
        if enabled and self.is_hovered:
            fill = carriage_button_hover_color
        center = (round(self.position.left), round(self.position.top))
        pygame.draw.circle(surface, fill, center, carriage_button_radius)
        pygame.draw.circle(
            surface,
            carriage_button_border_color,
            center,
            carriage_button_radius,
            carriage_button_border_width,
        )
        icon_color = (
            carriage_button_icon_color
            if enabled
            else carriage_button_disabled_icon_color
        )
        extent = carriage_button_radius // 2
        pygame.draw.line(
            surface,
            icon_color,
            (center[0] - extent, center[1]),
            (center[0] + extent, center[1]),
            carriage_button_icon_width,
        )
        if self.operation == "attach":
            pygame.draw.line(
                surface,
                icon_color,
                (center[0], center[1] - extent),
                (center[0], center[1] + extent),
                carriage_button_icon_width,
            )


def get_carriage_buttons(path_buttons: list[PathButton]) -> list[CarriageButton]:
    return [
        CarriageButton(path_button, operation)
        for path_button in path_buttons
        for operation in ("attach", "detach")
    ]


def update_carriage_button_positions(
    carriage_buttons: list[CarriageButton],
    surface_width: int | None = None,
    surface_height: int | None = None,
) -> None:
    del surface_width, surface_height
    for button in carriage_buttons:
        offset_index = 2 if button.operation == "attach" else 3
        button.position = Point(
            button.path_button.position.left
            + resource_control_horizontal_offsets[offset_index],
            button.path_button.position.top - resource_control_vertical_offset,
        )
        button.shape.position = button.position


def validate_resource_control_layout(surface_width: int, surface_height: int) -> None:
    """Fail before mutation when the reserved resource band cannot be safe."""

    width = float(surface_width)
    height = float(surface_height)
    if width <= 0 or height <= 0:
        raise ValueError("surface dimensions must be positive")

    path_step = path_button_buffer + 2 * button_size
    first_path_x = (surface_width - path_step * (num_paths - 1)) // 2
    path_y = surface_height - path_button_dist_to_bottom
    path_centers = tuple(
        (first_path_x + index * path_step, path_y) for index in range(num_paths)
    )
    control_y = path_y - resource_control_vertical_offset
    control_radii = (
        fleet_button_radius,
        fleet_button_radius,
        carriage_button_radius,
        carriage_button_radius,
    )
    controls = tuple(
        (path_x + offset, control_y, radius)
        for path_x, _ in path_centers
        for offset, radius in zip(resource_control_horizontal_offsets, control_radii)
    )
    station_safe_bottom = height * 0.9 + station_size + path_handle_quantization_margin
    locked_text_bottom = path_y - button_size - path_button_buy_text_bottom_gap

    def separated(
        first: tuple[float, float, float], second: tuple[float, float, float]
    ) -> bool:
        x_delta = first[0] - second[0]
        y_delta = first[1] - second[1]
        radius_sum = first[2] + second[2]
        return x_delta * x_delta + y_delta * y_delta > radius_sum * radius_sum

    if any(
        x - radius < 0
        or x + radius > width
        or y - radius <= station_safe_bottom
        or y - radius <= locked_text_bottom
        or y + radius > height
        for x, y, radius in controls
    ):
        raise ValueError("surface cannot fit the reserved resource-control band")
    if any(
        not separated(first, second)
        for index, first in enumerate(controls)
        for second in controls[index + 1 :]
    ):
        raise ValueError("surface cannot keep resource controls disjoint")
    path_circles = tuple((x, y, button_size) for x, y in path_centers)
    if any(
        not separated(control, path_circle)
        for control in controls
        for path_circle in path_circles
    ):
        raise ValueError("surface cannot separate resource and path controls")

    speed_y = surface_height - speed_button_dist_to_bottom
    speed_step = speed_button_width + speed_button_buffer
    speed_centers = tuple(
        (
            speed_button_left_padding + speed_button_width // 2 + index * speed_step,
            speed_y,
        )
        for index in range(4)
    )
    if any(
        speed_x - speed_button_width / 2 < 0
        or speed_x + speed_button_width / 2 > width
        or speed_y - speed_button_height / 2 < 0
        or speed_y + speed_button_height / 2 > height
        for speed_x, speed_y in speed_centers
    ) or any(
        abs(control_x - speed_x) <= radius + speed_button_width / 2
        for control_x, _control_y, radius in controls
        for speed_x, _speed_y in speed_centers
    ):
        raise ValueError("surface cannot separate resource and speed controls")


__all__ = [
    "CarriageButton",
    "CarriageOperation",
    "get_carriage_buttons",
    "update_carriage_button_positions",
    "validate_resource_control_layout",
]

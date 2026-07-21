from __future__ import annotations

from typing import Any, Literal

import pygame

from config import (
    fleet_button_badge_color,
    fleet_button_badge_font_size,
    fleet_button_badge_radius,
    fleet_button_badge_text_color,
    fleet_button_border_color,
    fleet_button_border_width,
    fleet_button_disabled_color,
    fleet_button_disabled_icon_color,
    fleet_button_enabled_color,
    fleet_button_hover_color,
    fleet_button_icon_color,
    fleet_button_icon_width,
    fleet_button_radius,
    resource_control_horizontal_offsets,
    resource_control_vertical_offset,
)
from geometry.circle import Circle
from geometry.point import Point
from ui.button import Button
from ui.path_button import PathButton

FleetOperation = Literal["assign", "unassign"]


class FleetButton(Button):
    """A compact fleet action bound to a stable PathButton slot."""

    def __init__(self, path_button: PathButton, operation: FleetOperation) -> None:
        super().__init__(Circle(fleet_button_enabled_color, fleet_button_radius))
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
            "can_assign_locomotive"
            if self.operation == "assign"
            else "can_queue_locomotive_unassignment"
        )
        method = getattr(state, method_name, None)
        try:
            return bool(method(path)) if callable(method) else False
        except Exception:
            return False

    @staticmethod
    def _queued_count(state: Any, path: Any | None) -> int:
        if path is None:
            return 0
        path_metros = tuple(getattr(path, "metros", ()))
        global_metros = tuple(getattr(state, "metros", ()))
        return sum(
            getattr(metro, "is_unassignment_queued", None) is True
            and sum(candidate is metro for candidate in path_metros) == 1
            and sum(candidate is metro for candidate in global_metros) == 1
            for metro in path_metros
        )

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        state: Any | None = None,
        resources: Any | None = None,
    ) -> None:
        del current_time_ms
        path = self._active_path(state) if state is not None else None
        enabled = self._is_enabled(state, path) if state is not None else False
        fill = fleet_button_enabled_color if enabled else fleet_button_disabled_color
        if enabled and self.is_hovered:
            fill = fleet_button_hover_color
        center = (round(self.position.left), round(self.position.top))
        pygame.draw.circle(surface, fill, center, fleet_button_radius)
        pygame.draw.circle(
            surface,
            fleet_button_border_color,
            center,
            fleet_button_radius,
            fleet_button_border_width,
        )
        icon_color = (
            fleet_button_icon_color if enabled else fleet_button_disabled_icon_color
        )
        extent = fleet_button_radius // 2
        pygame.draw.line(
            surface,
            icon_color,
            (center[0] - extent, center[1]),
            (center[0] + extent, center[1]),
            fleet_button_icon_width,
        )
        if self.operation == "assign":
            pygame.draw.line(
                surface,
                icon_color,
                (center[0], center[1] - extent),
                (center[0], center[1] + extent),
                fleet_button_icon_width,
            )
            return
        queued_count = self._queued_count(state, path)
        if queued_count:
            badge_center = (
                center[0] + fleet_button_radius - 2,
                center[1] - fleet_button_radius + 2,
            )
            pygame.draw.circle(
                surface,
                fleet_button_badge_color,
                badge_center,
                fleet_button_badge_radius,
            )
            font = (
                resources.font(None, fleet_button_badge_font_size)
                if resources is not None
                else pygame.font.Font(None, fleet_button_badge_font_size)
            )
            text = font.render(str(queued_count), True, fleet_button_badge_text_color)
            surface.blit(text, text.get_rect(center=badge_center))


def get_fleet_buttons(path_buttons: list[PathButton]) -> list[FleetButton]:
    return [
        FleetButton(path_button, operation)
        for path_button in path_buttons
        for operation in ("assign", "unassign")
    ]


def update_fleet_button_positions(
    fleet_buttons: list[FleetButton],
    surface_width: int | None = None,
    surface_height: int | None = None,
) -> None:
    del surface_width, surface_height
    for button in fleet_buttons:
        offset_index = 0 if button.operation == "assign" else 1
        button.position = Point(
            button.path_button.position.left
            + resource_control_horizontal_offsets[offset_index],
            button.path_button.position.top - resource_control_vertical_offset,
        )
        button.shape.position = button.position

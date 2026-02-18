from __future__ import annotations

from typing import List, Literal

import pygame
from config import (
    speed_button_active_color,
    speed_button_border_color,
    speed_button_buffer,
    speed_button_dist_to_bottom,
    speed_button_height,
    speed_button_hover_color,
    speed_button_left_padding,
    speed_button_width,
)
from geometry.point import Point
from geometry.rect import Rect
from ui.button import Button

SpeedAction = Literal["pause", "speed_1", "speed_2", "speed_4"]


class SpeedButton(Button):
    def __init__(self, action: SpeedAction) -> None:
        super().__init__(Rect(speed_button_border_color, speed_button_width, speed_button_height))
        self.position = Point(0, 0)
        self.action = action
        self.is_hovered = False

    def on_hover(self) -> None:
        self.is_hovered = True

    def on_exit(self) -> None:
        self.is_hovered = False

    def on_click(self) -> None:
        return

    def draw_pause_icon(self, surface: pygame.surface.Surface, rect: pygame.Rect) -> None:
        bar_width = 6
        bar_height = 18
        gap = 6
        left_bar_left = rect.centerx - gap // 2 - bar_width
        top = rect.centery - bar_height // 2
        right_bar_left = rect.centerx + gap // 2
        left_bar = pygame.Rect(left_bar_left, top, bar_width, bar_height)
        right_bar = pygame.Rect(right_bar_left, top, bar_width, bar_height)
        pygame.draw.rect(surface, speed_button_border_color, left_bar, border_radius=2)
        pygame.draw.rect(surface, speed_button_border_color, right_bar, border_radius=2)

    def draw_play_icon(
        self, surface: pygame.surface.Surface, center_x: int, center_y: int
    ) -> None:
        half_width = 5
        half_height = 7
        left = center_x - half_width
        top = center_y - half_height
        bottom = center_y + half_height
        points = [(left, top), (left, bottom), (left + 2 * half_width, center_y)]
        pygame.draw.polygon(surface, speed_button_border_color, points)

    def draw_play_icons(
        self, surface: pygame.surface.Surface, rect: pygame.Rect, count: int
    ) -> None:
        icon_spacing = 3
        icon_width = 10
        total_width = count * icon_width + (count - 1) * icon_spacing
        start_x = rect.centerx - total_width // 2 + icon_width // 2
        for idx in range(count):
            center_x = start_x + idx * (icon_width + icon_spacing)
            self.draw_play_icon(surface, center_x, rect.centery)

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        is_active: bool = False,
    ) -> None:
        del current_time_ms  # Unused, kept for Button compatibility.
        left = int(self.position.left - speed_button_width / 2)
        top = int(self.position.top - speed_button_height / 2)
        rect = pygame.Rect(left, top, speed_button_width, speed_button_height)
        fill_color = (255, 255, 255)
        if is_active:
            fill_color = speed_button_active_color
        elif self.is_hovered:
            fill_color = speed_button_hover_color
        pygame.draw.rect(surface, fill_color, rect, border_radius=6)
        pygame.draw.rect(surface, speed_button_border_color, rect, 2, border_radius=6)
        if self.action == "pause":
            self.draw_pause_icon(surface, rect)
        elif self.action == "speed_1":
            self.draw_play_icons(surface, rect, 1)
        elif self.action == "speed_2":
            self.draw_play_icons(surface, rect, 2)
        elif self.action == "speed_4":
            self.draw_play_icons(surface, rect, 4)
        # Keep shape position in sync so shape.contains() stays correct.
        self.shape.position = self.position


def update_speed_button_positions(
    speed_buttons: List[SpeedButton], surface_width: int, surface_height: int
) -> None:
    del surface_width
    y = surface_height - speed_button_dist_to_bottom
    x = speed_button_left_padding + speed_button_width // 2
    step = speed_button_width + speed_button_buffer
    for idx, button in enumerate(speed_buttons):
        button.position = Point(x + idx * step, y)
        button.shape.position = button.position


def get_speed_buttons() -> List[SpeedButton]:
    return [
        SpeedButton("pause"),
        SpeedButton("speed_1"),
        SpeedButton("speed_2"),
        SpeedButton("speed_4"),
    ]

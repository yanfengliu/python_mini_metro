from typing import List

import pygame
from config import (
    button_color,
    button_size,
    path_button_buffer,
    path_button_buy_text_color,
    path_button_buy_text_disabled_color,
    path_button_buy_text_font_size,
    path_button_cross_size,
    path_button_cross_width,
    path_button_dist_to_bottom,
    path_button_locked_ring_width,
    unlock_blink_count,
    unlock_blink_duration_ms,
)
from entity.path import Path
from geometry.circle import Circle
from geometry.cross import Cross
from geometry.point import Point
from geometry.shape import Shape
from ui.button import Button


class PathButton(Button):
    def __init__(self, shape: Shape, position: Point) -> None:
        super().__init__(shape)
        self.position = position
        self.path: Path | None = None
        self.cross: Cross | None = None
        self.show_cross = False
        self.is_locked = False
        self.unlock_blink_start_time_ms: int | None = None
        self.buy_text_font: pygame.font.Font | None = None

    def remove_path(self) -> None:
        self.cross = None
        self.path = None
        if not self.is_locked:
            self.shape.color = button_color

    def assign_path(self, path: Path) -> None:
        self.cross = Cross((0, 0, 0), path_button_cross_size, path_button_cross_width)
        self.cross.set_degrees(45)
        self.path = path
        self.shape.color = path.color

    def on_hover(self) -> None:
        self.show_cross = True

    def on_exit(self) -> None:
        self.show_cross = False

    def on_click(self) -> None:
        self.remove_path()

    def set_locked(self, locked: bool) -> None:
        self.is_locked = locked
        if locked:
            self.cross = None
            self.path = None
            self.shape.color = button_color
        elif self.path:
            self.shape.color = self.path.color
        else:
            self.shape.color = button_color

    def start_unlock_blink(self, current_time_ms: int) -> None:
        self.unlock_blink_start_time_ms = current_time_ms

    def is_unlock_blink_active(self, current_time_ms: int) -> bool:
        if self.unlock_blink_start_time_ms is None:
            return False
        return (
            current_time_ms - self.unlock_blink_start_time_ms
            < unlock_blink_duration_ms
        )

    def is_unlock_blink_visible(self, current_time_ms: int) -> bool:
        if not self.is_unlock_blink_active(current_time_ms):
            return True
        assert self.unlock_blink_start_time_ms is not None
        elapsed_ms = current_time_ms - self.unlock_blink_start_time_ms
        phase_duration_ms = unlock_blink_duration_ms / (unlock_blink_count * 2)
        phase_index = int(elapsed_ms / phase_duration_ms)
        return phase_index % 2 == 0

    def draw(
        self,
        surface: pygame.surface.Surface,
        current_time_ms: int | None = None,
        locked_purchase_price: int | None = None,
        locked_purchase_affordable: bool = False,
    ) -> None:
        if (
            current_time_ms is not None
            and not self.is_unlock_blink_visible(current_time_ms)
        ):
            return
        if self.is_locked and isinstance(self.shape, Circle):
            self.shape.position = self.position
            pygame.draw.circle(
                surface,
                self.shape.color,
                self.position.to_tuple(),
                self.shape.radius,
                path_button_locked_ring_width,
            )
            if self.show_cross and locked_purchase_price is not None:
                if self.buy_text_font is None:
                    self.buy_text_font = pygame.font.SysFont(
                        "arial", path_button_buy_text_font_size
                    )
                text_color = (
                    path_button_buy_text_color
                    if locked_purchase_affordable
                    else path_button_buy_text_disabled_color
                )
                buy_surface = self.buy_text_font.render("Buy", True, text_color)
                price_surface = self.buy_text_font.render(
                    str(locked_purchase_price), True, text_color
                )
                line_spacing = 4
                total_text_height = (
                    buy_surface.get_height()
                    + price_surface.get_height()
                    + line_spacing
                )
                top = (
                    self.position.top
                    - self.shape.radius
                    - 8
                    - total_text_height
                )
                buy_rect = buy_surface.get_rect(center=(self.position.left, top))
                buy_rect.top = top
                price_rect = price_surface.get_rect(
                    center=(
                        self.position.left,
                        buy_rect.bottom + line_spacing + price_surface.get_height() // 2,
                    )
                )
                surface.blit(buy_surface, buy_rect)
                surface.blit(price_surface, price_rect)
        else:
            super().draw(surface)
        if self.cross and self.show_cross and self.path:
            self.cross.draw(surface, self.position)


def update_path_button_positions(
    path_buttons: List[PathButton], surface_width: int, surface_height: int
) -> None:
    if not path_buttons:
        return
    step = path_button_buffer + 2 * button_size
    first_x = (surface_width - step * (len(path_buttons) - 1)) // 2
    y = surface_height - path_button_dist_to_bottom
    for idx, button in enumerate(path_buttons):
        button.position = Point(first_x + idx * step, y)


def get_path_buttons(
    num: int, surface_width: int | None = None, surface_height: int | None = None
) -> List[PathButton]:
    path_buttons = []
    for i in range(num):
        position = Point(0, 0)
        path_buttons.append(PathButton(Circle(button_color, button_size), position))
    if surface_width is not None and surface_height is not None:
        update_path_button_positions(path_buttons, surface_width, surface_height)
    return path_buttons

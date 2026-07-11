"""Player-facing pygame rendering isolated from simulation updates."""

from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any

import pygame

from .interpolation import MetroInterpolator
from .layout import MetroPose
from .network_renderer import NetworkRenderer


def _config() -> Any:
    import config

    return config


class LazyRenderResources:
    """Lazily initialize and retain renderer-owned pygame resources."""

    def __init__(self) -> None:
        self._fonts: dict[tuple[str | None, int], pygame.font.Font] = {}

    @property
    def font_count(self) -> int:
        return len(self._fonts)

    def font(self, name: str | None, size: int) -> pygame.font.Font:
        del name  # Text uses pygame's bundled font for portable headless rendering.
        key = (None, int(size))
        font = self._fonts.get(key)
        if font is not None:
            return font
        if not pygame.font.get_init():
            pygame.font.init()
        font = pygame.font.Font(None, int(size))
        self._fonts[key] = font
        return font


@lru_cache(maxsize=128)
def _supported_keyword_names(method: Any) -> frozenset[str] | None:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return frozenset()
    if any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return None
    return frozenset(signature.parameters)


def _supported_kwargs(method: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    target = getattr(method, "__func__", method)
    try:
        supported = _supported_keyword_names(target)
    except TypeError:
        supported = frozenset(inspect.signature(method).parameters)
    if supported is None:
        return kwargs
    return {name: value for name, value in kwargs.items() if name in supported}


def _call_flexibly(method: Any, *args: Any, **kwargs: Any) -> Any:
    return method(*args, **_supported_kwargs(method, kwargs))


class GameRenderer:
    """Compose the full game frame in a stable painter's order."""

    def __init__(
        self,
        network_renderer: Any | None = None,
        resources: LazyRenderResources | None = None,
        interpolator: MetroInterpolator | None = None,
    ) -> None:
        self.network_renderer = network_renderer or NetworkRenderer()
        self.resources = resources or LazyRenderResources()
        self.interpolator = interpolator or MetroInterpolator()

    def before_step(self, state: Any) -> None:
        self.interpolator.before_step(state)

    def after_step(self, state: Any) -> None:
        self.interpolator.after_step(state)

    def clear_interpolation(self) -> None:
        self.interpolator.clear()

    def draw(
        self,
        surface: pygame.Surface,
        state: Any,
        alpha: float = 1.0,
    ) -> None:
        """Draw network, entities, controls, text, then modal overlay."""

        paths = tuple(getattr(state, "paths", ()))
        layouts = self.network_renderer.draw(surface, paths)
        layouts_by_path_id = {layout.path_id: layout for layout in layouts}
        paths_by_id = {str(getattr(path, "id", id(path))): path for path in paths}
        current_time_ms = int(getattr(state, "time_ms", 0))
        max_wait_ms = getattr(state, "passenger_max_wait_time_ms", None)

        for station in getattr(state, "stations", ()):
            _call_flexibly(
                station.draw,
                surface,
                current_time_ms=current_time_ms,
                passenger_max_wait_time_ms=max_wait_ms,
                resources=self.resources,
            )

        for metro in getattr(state, "metros", ()):
            path_id = str(getattr(metro, "path_id", ""))
            path = paths_by_id.get(path_id)
            layout = layouts_by_path_id.get(path_id)
            if path is None or layout is None:
                _call_flexibly(
                    metro.draw,
                    surface,
                    current_time_ms=current_time_ms,
                    passenger_max_wait_time_ms=max_wait_ms,
                    resources=self.resources,
                )
                continue
            pose = self.interpolator.pose_for(path, metro, layout, alpha)
            self._draw_metro(surface, metro, pose, current_time_ms, max_wait_ms)

        self._draw_buttons(surface, state, current_time_ms)
        self._draw_score(surface, state)
        if bool(getattr(state, "is_game_over", False)):
            self._draw_game_over(surface, state)

    def _draw_metro(
        self,
        surface: pygame.Surface,
        metro: Any,
        pose: MetroPose,
        current_time_ms: int,
        max_wait_ms: int | None,
    ) -> None:
        draw = metro.draw
        _call_flexibly(
            draw,
            surface,
            display_position=pose.position,
            rotation_degrees=pose.heading_degrees,
            current_time_ms=current_time_ms,
            passenger_max_wait_time_ms=max_wait_ms,
            resources=self.resources,
        )

    def _draw_buttons(
        self, surface: pygame.Surface, state: Any, current_time_ms: int
    ) -> None:
        path_buttons = tuple(getattr(state, "path_buttons", ()))
        path_button_indexes = {
            id(button): index for index, button in enumerate(path_buttons)
        }
        speed_buttons = {id(button) for button in getattr(state, "speed_buttons", ())}
        for button in getattr(state, "buttons", ()):
            kwargs: dict[str, Any] = {
                "current_time_ms": current_time_ms,
                "resources": self.resources,
            }
            path_button_index = path_button_indexes.get(id(button))
            if path_button_index is not None:
                price_method = getattr(
                    state, "get_purchase_price_for_path_button_idx", None
                )
                affordable_method = getattr(state, "can_purchase_path_button_idx", None)
                kwargs["locked_purchase_price"] = (
                    price_method(path_button_index) if callable(price_method) else None
                )
                kwargs["locked_purchase_affordable"] = bool(
                    affordable_method(path_button_index)
                    if callable(affordable_method)
                    else False
                )
                if (
                    bool(getattr(button, "is_locked", False))
                    and bool(getattr(button, "show_cross", False))
                    and kwargs["locked_purchase_price"] is not None
                ):
                    kwargs["buy_text_font"] = self.resources.font(
                        None, _config().path_button_buy_text_font_size
                    )
            elif id(button) in speed_buttons:
                active_method = getattr(state, "is_speed_button_active", None)
                kwargs["is_active"] = bool(
                    active_method(button.action) if callable(active_method) else False
                )
            _call_flexibly(button.draw, surface, **kwargs)

    def _draw_score(self, surface: pygame.Surface, state: Any) -> None:
        config = _config()
        font = self.resources.font(config.font_name, config.score_font_size)
        text_surface = font.render(
            f"Score: {getattr(state, 'score', 0)}", True, (0, 0, 0)
        )
        surface.blit(text_surface, config.score_display_coords)

    def _draw_game_over(self, surface: pygame.Surface, state: Any) -> None:
        config = _config()
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        overlay.fill(config.game_over_overlay_color)
        surface.blit(overlay, (0, 0))

        score_font = self.resources.font(config.font_name, config.score_font_size)
        title_font = self.resources.font(config.font_name, config.game_over_font_size)
        hint_font = self.resources.font(
            config.font_name, config.game_over_hint_font_size
        )
        title_surface = title_font.render(
            "Game Over", True, config.game_over_text_color
        )
        title_rect = title_surface.get_rect(
            center=(width // 2, height // 2 - config.game_over_font_size // 3)
        )
        surface.blit(title_surface, title_rect)

        score_surface = score_font.render(
            f"Final Score: {getattr(state, 'score', 0)}",
            True,
            config.game_over_text_color,
        )
        score_rect = score_surface.get_rect(
            center=(width // 2, height // 2 + config.game_over_font_size // 3)
        )
        surface.blit(score_surface, score_rect)

        buttons = (
            (
                hint_font.render("Restart (R)", True, config.game_over_text_color),
                getattr(state, "game_over_restart_rect", None),
            ),
            (
                hint_font.render("Exit (Esc)", True, config.game_over_text_color),
                getattr(state, "game_over_exit_rect", None),
            ),
        )
        for text, prepared_rect in buttons:
            if not isinstance(prepared_rect, pygame.Rect):
                continue
            rect = prepared_rect.copy()
            pygame.draw.rect(
                surface, config.game_over_button_color, rect, border_radius=8
            )
            pygame.draw.rect(
                surface,
                config.game_over_button_border_color,
                rect,
                config.game_over_button_border_width,
                border_radius=8,
            )
            surface.blit(text, text.get_rect(center=rect.center))

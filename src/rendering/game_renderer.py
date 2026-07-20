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
        self._draw_redraw_preview(surface, state, paths, layouts)

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
        self._draw_hud(surface, state)
        if bool(getattr(state, "is_game_over", False)):
            self._draw_game_over(surface, state)

    def _draw_redraw_preview(
        self,
        surface: pygame.Surface,
        state: Any,
        paths: tuple[Any, ...],
        layouts: tuple[Any, ...],
    ) -> None:
        redraw = getattr(state, "path_redraw", None)
        target = getattr(redraw, "path", None)
        clear_preview = getattr(self.network_renderer, "clear_preview_cache", None)
        if redraw is None or target is None:
            if callable(clear_preview):
                clear_preview()
            return
        selected_layout = next(
            (layout for path, layout in zip(paths, layouts) if path is target),
            None,
        )
        draw_preview = getattr(self.network_renderer, "draw_preview", None)
        if selected_layout is None or not callable(draw_preview):
            if callable(clear_preview):
                clear_preview()
            return
        draw_preview(
            surface,
            path_id=selected_layout.path_id,
            color=selected_layout.color,
            stations=getattr(redraw, "stations", ()),
            order=selected_layout.order,
            loop=bool(getattr(redraw, "loop", False)),
            temp_point=getattr(redraw, "temp_point", None),
            invalid=bool(getattr(redraw, "invalid", False)),
        )

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
        redraw = getattr(state, "path_redraw", None)
        selected_path = getattr(redraw, "path", None)
        redraw_invalid = bool(getattr(redraw, "invalid", False))
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
                is_selected = (
                    selected_path is not None
                    and getattr(button, "path", None) is selected_path
                )
                kwargs["is_selected"] = is_selected
                kwargs["is_invalid"] = bool(is_selected and redraw_invalid)
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

    @staticmethod
    def _metric(state: Any, canonical_name: str, legacy_name: str) -> Any:
        if hasattr(state, canonical_name):
            return getattr(state, canonical_name)
        return getattr(state, legacy_name, 0)

    def _draw_hud(self, surface: pygame.Surface, state: Any) -> None:
        config = _config()
        font = self.resources.font(config.font_name, config.hud_font_size)
        deliveries = self._metric(state, "deliveries", "total_travels_handled")
        line_credits = self._metric(state, "line_credits", "score")
        x, y = config.hud_display_coords
        delivery_surface = font.render(
            f"Passengers Delivered: {deliveries}", True, (0, 0, 0)
        )
        credit_surface = font.render(f"Line Credits: {line_credits}", True, (0, 0, 0))
        surface.blit(delivery_surface, (x, y))
        surface.blit(credit_surface, (x, y + config.hud_line_spacing))

    def _draw_score(self, surface: pygame.Surface, state: Any) -> None:
        """Deprecated private compatibility wrapper for the canonical HUD."""

        self._draw_hud(surface, state)

    def _draw_game_over(self, surface: pygame.Surface, state: Any) -> None:
        config = _config()
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        overlay.fill(config.game_over_overlay_color)
        surface.blit(overlay, (0, 0))

        metric_font = self.resources.font(config.font_name, config.hud_font_size)
        title_font = self.resources.font(config.font_name, config.game_over_font_size)
        hint_font = self.resources.font(
            config.font_name, config.game_over_hint_font_size
        )
        title_surface = title_font.render(
            "Game Over", True, config.game_over_text_color
        )
        deliveries = self._metric(state, "deliveries", "total_travels_handled")
        line_credits = self._metric(state, "line_credits", "score")
        delivery_surface = metric_font.render(
            f"Passengers Delivered: {deliveries}",
            True,
            config.game_over_text_color,
        )
        credit_surface = metric_font.render(
            f"Line Credits Remaining: {line_credits}",
            True,
            config.game_over_text_color,
        )

        restart_rect = getattr(state, "game_over_restart_rect", None)
        button_top = (
            restart_rect.top if isinstance(restart_rect, pygame.Rect) else height
        )
        content_height = (
            title_surface.get_height()
            + config.game_over_title_metric_spacing
            + delivery_surface.get_height()
            + config.game_over_metric_spacing
            + credit_surface.get_height()
        )
        content_bottom = button_top - config.game_over_content_button_gap
        content_top = max(
            config.game_over_content_top_margin,
            content_bottom - content_height,
        )
        title_rect = title_surface.get_rect(midtop=(width // 2, content_top))
        delivery_rect = delivery_surface.get_rect(
            midtop=(
                width // 2,
                title_rect.bottom + config.game_over_title_metric_spacing,
            )
        )
        credit_rect = credit_surface.get_rect(
            midtop=(
                width // 2,
                delivery_rect.bottom + config.game_over_metric_spacing,
            )
        )
        surface.blit(title_surface, title_rect)
        surface.blit(delivery_surface, delivery_rect)
        surface.blit(credit_surface, credit_rect)

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

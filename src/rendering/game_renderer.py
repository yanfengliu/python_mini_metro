from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any

import pygame

from .consist_layout import consist_passenger_slices
from .interpolation import MetroInterpolator
from .layout import MetroPose
from .network_renderer import NetworkRenderer
from .path_handle_renderer import PathHandleRenderer, removal_on_layout


def _config() -> Any:
    import config

    return config


@lru_cache(maxsize=1)
def _path_handle_api() -> tuple[Any, Any]:
    if __package__ == "src.rendering":
        from ..path_handles import PathHandleEdit, build_path_handles_for_state
    else:
        from path_handles import PathHandleEdit, build_path_handles_for_state

    return PathHandleEdit, build_path_handles_for_state


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
        path_handle_renderer: Any | None = None,
    ) -> None:
        self.network_renderer = network_renderer or NetworkRenderer()
        self.resources = resources or LazyRenderResources()
        self.interpolator = interpolator or MetroInterpolator()
        self.path_handle_renderer = path_handle_renderer or PathHandleRenderer()

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
        handles, selected_handle, handle_invalid = self._path_handle_frame(
            state, paths, surface.get_size()
        )
        if handles:
            self.path_handle_renderer.draw_leaders(surface, handles)

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
            carriage_poses = self.interpolator.poses_for_consist(
                path,
                metro,
                layout,
                alpha,
            )
            self._draw_metro(
                surface,
                metro,
                pose,
                carriage_poses,
                current_time_ms,
                max_wait_ms,
            )

        if handles:
            self.path_handle_renderer.draw_markers(
                surface,
                handles,
                selected=selected_handle,
                invalid=handle_invalid,
            )
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
        edit = getattr(redraw, "handle_edit", None)
        preview = getattr(edit, "preview_spec", None)
        preview_stations = (
            getattr(preview, "stations", ())
            if preview is not None
            else getattr(redraw, "stations", ())
        )
        preview_loop = (
            bool(getattr(preview, "loop", False))
            if preview is not None
            else bool(getattr(redraw, "loop", False))
        )
        preview_point = (
            getattr(preview, "temp_point", None)
            if preview is not None
            else getattr(redraw, "temp_point", None)
        )
        preview_invalid = (
            bool(getattr(preview, "invalid", False))
            if preview is not None
            else bool(getattr(redraw, "invalid", False))
        )
        _call_flexibly(
            draw_preview,
            surface,
            path_id=selected_layout.path_id,
            color=selected_layout.color,
            stations=preview_stations,
            order=selected_layout.order,
            loop=preview_loop,
            temp_point=preview_point,
            temp_insertion_index=getattr(preview, "temp_insertion_index", None),
            invalid=preview_invalid,
        )
        removal = removal_on_layout(
            target,
            selected_layout,
            getattr(preview, "removal_segment", ()),
        )
        if removal is not None:
            self.path_handle_renderer.draw_shortening_removal(
                surface,
                removal,
                color=selected_layout.color,
                invalid=preview_invalid,
            )

    @staticmethod
    def _selected_path(state: Any, paths: tuple[Any, ...]) -> Any | None:
        path_handle_edit, _ = _path_handle_api()
        redraw = getattr(state, "path_redraw", None)
        edit = getattr(redraw, "handle_edit", None)
        if isinstance(edit, path_handle_edit):
            path = edit.path
            return path if sum(candidate is path for candidate in paths) == 1 else None
        selection = getattr(state, "path_edit_selection", None)
        resolve = getattr(selection, "resolve", None)
        if callable(resolve):
            return resolve(paths)
        path = getattr(redraw, "path", None)
        return path if sum(candidate is path for candidate in paths) == 1 else None

    def _path_handle_frame(
        self,
        state: Any,
        paths: tuple[Any, ...],
        viewport_size: tuple[int, int],
    ) -> tuple[tuple[Any, ...], Any | None, bool]:
        path_handle_edit, build_path_handles_for_state = _path_handle_api()
        redraw = getattr(state, "path_redraw", None)
        edit = getattr(redraw, "handle_edit", None)
        selection = getattr(state, "path_edit_selection", None)
        if not isinstance(edit, path_handle_edit) and not callable(
            getattr(selection, "resolve", None)
        ):
            return (), None, False
        path = self._selected_path(state, paths)
        if path is None:
            return (), None, False
        try:
            handles = tuple(
                build_path_handles_for_state(
                    state,
                    path,
                    viewport_size=viewport_size,
                )
            )
        except (AttributeError, IndexError, TypeError, ValueError):
            return (), None, False
        if not isinstance(edit, path_handle_edit):
            return handles, None, False
        selected = next(
            (
                handle
                for handle in handles
                if handle.kind == edit.kind and handle.slot == edit.slot
            ),
            None,
        )
        invalid = bool(getattr(getattr(edit, "preview_spec", None), "invalid", False))
        return handles, selected, invalid

    def _draw_metro(
        self,
        surface: pygame.Surface,
        metro: Any,
        pose: MetroPose,
        carriage_poses: tuple[MetroPose, ...],
        current_time_ms: int,
        max_wait_ms: int | None,
    ) -> None:
        queued = bool(getattr(metro, "is_unassignment_queued", False))
        poses = (pose, *carriage_poses)
        for (body, passengers), body_pose in zip(
            consist_passenger_slices(metro), poses
        ):
            _call_flexibly(
                body.draw,
                surface,
                passengers=passengers,
                display_position=body_pose.position,
                rotation_degrees=body_pose.heading_degrees,
                current_time_ms=current_time_ms,
                passenger_max_wait_time_ms=max_wait_ms,
                is_unassignment_queued=queued,
                resources=self.resources,
            )

    def _draw_buttons(
        self, surface: pygame.Surface, state: Any, current_time_ms: int
    ) -> None:
        redraw = getattr(state, "path_redraw", None)
        paths = tuple(getattr(state, "paths", ()))
        selected_path = self._selected_path(state, paths)
        preview = getattr(getattr(redraw, "handle_edit", None), "preview_spec", None)
        redraw_invalid = bool(
            getattr(preview, "invalid", False)
            if preview is not None
            else getattr(redraw, "invalid", False)
        )
        path_buttons = tuple(getattr(state, "path_buttons", ()))
        path_button_indexes = {
            id(button): index for index, button in enumerate(path_buttons)
        }
        speed_buttons = {id(button) for button in getattr(state, "speed_buttons", ())}
        for button in getattr(state, "buttons", ()):
            kwargs: dict[str, Any] = {
                "current_time_ms": current_time_ms,
                "resources": self.resources,
                "state": state,
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

    @staticmethod
    def _availability(state: Any, resource: str) -> Any:
        missing = object()
        available = getattr(state, f"available_{resource}", missing)
        if available is not missing:
            return available
        total_name = "num_metros" if resource == "locomotives" else "num_carriages"
        total = getattr(state, total_name, missing)
        metros = getattr(state, "metros", missing)
        if total is missing or metros is missing:
            return 0
        assigned = len(metros)
        if resource == "carriages":
            assigned = sum(len(getattr(metro, "carriages", ())) for metro in metros)
        return max(0, total - assigned)

    def _draw_hud(self, surface: pygame.Surface, state: Any) -> None:
        config = _config()
        font = self.resources.font(config.font_name, config.hud_font_size)
        x, y = config.hud_display_coords
        lines = (
            f"Passengers Delivered: {self._metric(state, 'deliveries', 'total_travels_handled')}",
            f"Line Credits: {self._metric(state, 'line_credits', 'score')}",
            f"Locomotives Available: {self._availability(state, 'locomotives')}",
            f"Carriages Available: {self._availability(state, 'carriages')}",
        )
        for row, text in enumerate(lines):
            surface.blit(
                font.render(text, True, (0, 0, 0)),
                (x, y + row * config.hud_line_spacing),
            )

    def _draw_score(self, surface: pygame.Surface, state: Any) -> None:
        self._draw_hud(surface, state)

    def _draw_game_over(self, surface: pygame.Surface, state: Any) -> None:
        config = _config()
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        overlay.fill(config.game_over_overlay_color)
        surface.blit(overlay, (0, 0))

        deliveries = self._metric(state, "deliveries", "total_travels_handled")
        line_credits = self._metric(state, "line_credits", "score")
        metric_font = self.resources.font(config.font_name, config.hud_font_size)
        content = (
            self.resources.font(config.font_name, config.game_over_font_size).render(
                "Game Over", True, config.game_over_text_color
            ),
            metric_font.render(
                f"Passengers Delivered: {deliveries}",
                True,
                config.game_over_text_color,
            ),
            metric_font.render(
                f"Line Credits Remaining: {line_credits}",
                True,
                config.game_over_text_color,
            ),
        )
        spacings = (
            config.game_over_title_metric_spacing,
            config.game_over_metric_spacing,
        )
        restart_rect = getattr(state, "game_over_restart_rect", None)
        content_height = sum(item.get_height() for item in content) + sum(spacings)
        top = max(
            config.game_over_content_top_margin,
            (restart_rect.top if isinstance(restart_rect, pygame.Rect) else height)
            - config.game_over_content_button_gap
            - content_height,
        )
        for index, item in enumerate(content):
            rect = item.get_rect(midtop=(width // 2, top))
            surface.blit(item, rect)
            if index < len(spacings):
                top = rect.bottom + spacings[index]

        hint_font = self.resources.font(
            config.font_name, config.game_over_hint_font_size
        )
        for label, attribute in (
            ("Restart (R)", "game_over_restart_rect"),
            ("Exit (Esc)", "game_over_exit_rect"),
        ):
            prepared_rect = getattr(state, attribute, None)
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
            text = hint_font.render(label, True, config.game_over_text_color)
            surface.blit(text, text.get_rect(center=rect.center))

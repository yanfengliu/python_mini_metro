"""Cached, antialiased software rendering for immutable network layouts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import pygame

from .layout import (
    Position,
    VisualPath,
    build_visual_path,
    centered_path_orders,
)

RGBA = tuple[int, int, int, int]


def _default_lane_spacing() -> float:
    from config import path_order_shift

    return path_order_shift


def _default_stroke_width() -> int:
    from config import path_width

    return path_width


def _default_halo_color() -> RGBA:
    from config import screen_color

    return (*screen_color, 255)


@dataclass(frozen=True, slots=True)
class NetworkStyle:
    """All values that affect static network pixels and layout."""

    lane_spacing: float = field(default_factory=_default_lane_spacing)
    stroke_width: int = field(default_factory=_default_stroke_width)
    halo_width: int = field(default_factory=lambda: _default_stroke_width() + 6)
    halo_color: RGBA = field(default_factory=_default_halo_color)
    supersample: int = 2

    def __post_init__(self) -> None:
        if self.lane_spacing < 0:
            raise ValueError("lane spacing cannot be negative")
        if self.stroke_width <= 0:
            raise ValueError("stroke width must be positive")
        if self.halo_width < self.stroke_width:
            raise ValueError("halo width cannot be narrower than the stroke")
        if self.supersample < 2:
            raise ValueError("supersample must be at least 2")
        if len(self.halo_color) != 4:
            raise ValueError("halo color must be RGBA")


def _position_signature(value: Any) -> Position:
    return (float(value.left), float(value.top))


def _station_signature(station: Any | None) -> tuple[Any, ...] | None:
    if station is None:
        return None
    return (
        str(getattr(station, "id", id(station))),
        _position_signature(station.position),
    )


def _segment_signature(segment: Any) -> tuple[Any, ...]:
    return (
        type(segment).__qualname__,
        _position_signature(segment.segment_start),
        _position_signature(segment.segment_end),
        _station_signature(getattr(segment, "start_station", None)),
        _station_signature(getattr(segment, "end_station", None)),
    )


def _path_signature(path: Any, order: float) -> tuple[Any, ...]:
    """Capture every route value that can affect cached network pixels."""

    return (
        str(getattr(path, "id", id(path))),
        tuple(int(channel) for channel in path.color),
        bool(getattr(path, "is_looped", False)),
        float(order),
        tuple(_station_signature(station) for station in getattr(path, "stations", ())),
        tuple(_segment_signature(segment) for segment in getattr(path, "segments", ())),
    )


def _scaled_point(point: Position, scale: int) -> tuple[int, int]:
    return (round(point[0] * scale), round(point[1] * scale))


def _draw_round_stroke(
    surface: pygame.Surface,
    start: Position,
    end: Position,
    color: tuple[int, ...],
    width: int,
    scale: int,
) -> None:
    scaled_start = _scaled_point(start, scale)
    scaled_end = _scaled_point(end, scale)
    scaled_width = max(1, round(width * scale))
    radius = max(1, math.ceil(scaled_width / 2))
    pygame.draw.line(surface, color, scaled_start, scaled_end, scaled_width)
    pygame.draw.circle(surface, color, scaled_start, radius)
    pygame.draw.circle(surface, color, scaled_end, radius)


def _render_static_surface(
    size: tuple[int, int],
    layouts: tuple[VisualPath, ...],
    style: NetworkStyle,
) -> pygame.Surface:
    scale = style.supersample
    high_resolution = pygame.Surface(
        (size[0] * scale, size[1] * scale), pygame.SRCALPHA, 32
    )
    for layout in layouts:
        for segment in layout.segments:
            _draw_round_stroke(
                high_resolution,
                segment.start,
                segment.end,
                style.halo_color,
                style.halo_width,
                scale,
            )
    for layout in layouts:
        color = (*layout.color, 255)
        for segment in layout.segments:
            _draw_round_stroke(
                high_resolution,
                segment.start,
                segment.end,
                color,
                style.stroke_width,
                scale,
            )
    return pygame.transform.smoothscale(high_resolution, size)


def _draw_dynamic_segment(
    surface: pygame.Surface,
    start: Position,
    end: Position,
    color: tuple[int, int, int],
    style: NetworkStyle,
) -> None:
    """Draw one antialiased segment through a small clipped scratch surface."""

    margin = math.ceil(style.halo_width / 2) + 2
    left = max(0, math.floor(min(start[0], end[0]) - margin))
    top = max(0, math.floor(min(start[1], end[1]) - margin))
    right = min(surface.get_width(), math.ceil(max(start[0], end[0]) + margin))
    bottom = min(surface.get_height(), math.ceil(max(start[1], end[1]) + margin))
    if right <= left or bottom <= top:
        return

    width, height = right - left, bottom - top
    scale = style.supersample
    scratch = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA, 32)
    local_start = (start[0] - left, start[1] - top)
    local_end = (end[0] - left, end[1] - top)
    _draw_round_stroke(
        scratch,
        local_start,
        local_end,
        style.halo_color,
        style.halo_width,
        scale,
    )
    _draw_round_stroke(
        scratch,
        local_start,
        local_end,
        (*color, 255),
        style.stroke_width,
        scale,
    )
    surface.blit(pygame.transform.smoothscale(scratch, (width, height)), (left, top))


class NetworkRenderer:
    """Render static routes from a bounded one-entry per-instance cache."""

    def __init__(self, style: NetworkStyle | None = None) -> None:
        self.style = style or NetworkStyle()
        self._cache_key: tuple[Any, ...] | None = None
        self._cache_surface: pygame.Surface | None = None
        self._cache_layouts: tuple[VisualPath, ...] = ()
        self.cache_rebuild_count = 0

    @property
    def cache_entry_count(self) -> int:
        return int(self._cache_surface is not None)

    def clear_cache(self) -> None:
        self._cache_key = None
        self._cache_surface = None
        self._cache_layouts = ()

    def draw(
        self,
        surface: pygame.Surface,
        paths: Sequence[Any],
        orders: Sequence[float] | None = None,
    ) -> tuple[VisualPath, ...]:
        """Draw routes and return the layouts used for metro projection."""

        path_values = tuple(paths)
        order_values = (
            centered_path_orders(len(path_values))
            if orders is None
            else tuple(float(order) for order in orders)
        )
        if len(order_values) != len(path_values):
            raise ValueError("orders must contain one value per path")

        size = surface.get_size()
        key = (
            size,
            self.style,
            tuple(
                _path_signature(path, order)
                for path, order in zip(path_values, order_values)
            ),
        )
        if key != self._cache_key:
            self._cache_layouts = tuple(
                build_visual_path(path, order, self.style.lane_spacing)
                for path, order in zip(path_values, order_values)
            )
            self._cache_surface = (
                _render_static_surface(size, self._cache_layouts, self.style)
                if any(layout.segments for layout in self._cache_layouts)
                else None
            )
            self._cache_key = key
            self.cache_rebuild_count += 1

        if self._cache_surface is not None:
            surface.blit(self._cache_surface, (0, 0))
        for path in path_values:
            temp_point = getattr(path, "temp_point", None)
            stations = tuple(getattr(path, "stations", ()))
            if temp_point is None or not stations:
                continue
            _draw_dynamic_segment(
                surface,
                _position_signature(stations[-1].position),
                _position_signature(temp_point),
                tuple(int(channel) for channel in path.color),
                self.style,
            )
        return self._cache_layouts

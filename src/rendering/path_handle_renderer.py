"""Cache-free rendering for primitive route-edit handle descriptors."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import pygame

Position = tuple[float, float]


def _config() -> Any:
    if __package__ == "src.rendering":
        from .. import config
    else:
        import config

    return config


def _point(value: Any) -> tuple[int, int]:
    return (round(float(value[0])), round(float(value[1])))


def _rgb(value: Any) -> tuple[int, int, int]:
    return tuple(int(channel) for channel in value)


def removal_on_layout(
    path: Any,
    layout: Any,
    removal: Any,
) -> tuple[Position, Position] | None:
    """Project a raw removal edge onto its selected production lane."""

    if not isinstance(removal, (tuple, list)) or len(removal) != 2:
        return None
    try:
        raw_removal = tuple((float(point[0]), float(point[1])) for point in removal)
    except (IndexError, TypeError, ValueError):
        return None
    stations_by_id = {
        str(getattr(station, "id", id(station))): (
            float(station.position.left),
            float(station.position.top),
        )
        for station in getattr(path, "stations", ())
    }
    for segment in getattr(layout, "segments", ()):
        if getattr(segment, "kind", None) != "path":
            continue
        raw_start = stations_by_id.get(getattr(segment, "start_station_id", None))
        raw_end = stations_by_id.get(getattr(segment, "end_station_id", None))
        if (raw_start, raw_end) == raw_removal:
            return (segment.start, segment.end)
        if (raw_end, raw_start) == raw_removal:
            return (segment.end, segment.start)
    return None


class PathHandleRenderer:
    """Draw transient handle affordances without retaining their inputs."""

    def draw_leaders(
        self,
        surface: pygame.Surface,
        handles: Sequence[Any],
    ) -> None:
        config = _config()
        color = _rgb(config.path_handle_color)
        width = int(config.path_handle_leader_width)
        for handle in handles:
            pygame.draw.line(
                surface,
                color,
                _point(handle.anchor),
                _point(handle.center),
                width,
            )

    def draw_markers(
        self,
        surface: pygame.Surface,
        handles: Sequence[Any],
        *,
        selected: Any | None = None,
        invalid: bool = False,
    ) -> None:
        config = _config()
        base_color = _rgb(config.path_handle_color)
        selected_color = _rgb(config.path_handle_selected_color)
        invalid_color = _rgb(config.path_handle_invalid_color)
        marker_radius = int(config.path_handle_marker_radius)
        ring_width = int(config.path_handle_ring_width)
        outline_width = int(config.path_handle_outline_width)

        for handle in handles:
            center = _point(handle.center)
            is_selected = selected is not None and handle == selected
            color = invalid_color if is_selected and invalid else base_color
            pygame.draw.circle(
                surface,
                color,
                center,
                round(float(handle.hit_radius)) + 1,
                ring_width,
            )
            marker_width = ring_width if handle.kind == "insert" else 0
            pygame.draw.circle(
                surface,
                color,
                center,
                marker_radius,
                marker_width,
            )
            if is_selected:
                outline_color = invalid_color if invalid else selected_color
                pygame.draw.circle(
                    surface,
                    outline_color,
                    center,
                    marker_radius + outline_width,
                    outline_width,
                )

    def draw_shortening_removal(
        self,
        surface: pygame.Surface,
        segment: tuple[Position, Position],
        *,
        color: Sequence[int],
        invalid: bool = False,
    ) -> None:
        """Overlay dashes, a midpoint strike, and the removed endpoint marker."""

        config = _config()
        start = (float(segment[0][0]), float(segment[0][1]))
        end = (float(segment[1][0]), float(segment[1][1]))
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        if not math.isfinite(length) or length <= 0:
            return

        overlay = _rgb(
            config.path_handle_invalid_color if invalid else config.path_handle_color
        )
        width = int(config.path_handle_removal_width)
        unit = (dx / length, dy / length)
        dash_length = 14.0
        dash_period = 24.0
        cursor = 0.0
        while cursor < length:
            dash_end = min(length, cursor + dash_length)
            dash_start_point = (
                start[0] + unit[0] * cursor,
                start[1] + unit[1] * cursor,
            )
            dash_end_point = (
                start[0] + unit[0] * dash_end,
                start[1] + unit[1] * dash_end,
            )
            pygame.draw.line(
                surface,
                overlay,
                _point(dash_start_point),
                _point(dash_end_point),
                width,
            )
            cursor += dash_period

        midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        normal = (-unit[1], unit[0])
        strike_radius = float(config.path_handle_marker_radius)
        pygame.draw.line(
            surface,
            overlay,
            _point(
                (
                    midpoint[0] - normal[0] * strike_radius,
                    midpoint[1] - normal[1] * strike_radius,
                )
            ),
            _point(
                (
                    midpoint[0] + normal[0] * strike_radius,
                    midpoint[1] + normal[1] * strike_radius,
                )
            ),
            width,
        )
        pygame.draw.circle(
            surface,
            _rgb(color),
            _point(start),
            int(config.path_handle_marker_radius),
            int(config.path_handle_outline_width),
        )

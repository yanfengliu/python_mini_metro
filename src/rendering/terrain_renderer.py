"""GM-09b terrain rendering (D-034).

Paints a map's river obstacle bands UNDER the network, called once at the top of
``GameRenderer.draw`` so every consumer — the human loop, the RL pixel
observation, the compat render path, and tests — sees the same terrain. The module
is deterministic (consumes no RNG) and self-contained: a map with no rivers
(CLASSIC) paints nothing, keeping the CLASSIC frame byte-identical. The water color
lives here, not in the balance ``config``, since it is a per-map render concern.
"""

from __future__ import annotations

import pygame

# Light steel-blue water; a per-map render concern kept out of the balance config.
RIVER_COLOR = (176, 196, 222)
# A tunnel/bridge portal marker where a line crosses the river.
CROSSING_MARKER_COLOR = (40, 40, 60)
CROSSING_MARKER_RADIUS = 9


def draw_terrain(surface: pygame.Surface, map_definition) -> None:
    """Fill each of the map's river bands. A definition with no ``rivers``
    (CLASSIC, or an attr-less render state) paints nothing."""
    rivers = getattr(map_definition, "rivers", ()) or ()
    for band in rivers:
        left, top, right, bottom = band
        pygame.draw.rect(
            surface,
            RIVER_COLOR,
            pygame.Rect(
                round(left), round(top), round(right - left), round(bottom - top)
            ),
        )


def draw_crossings(surface: pygame.Surface, map_definition, paths) -> None:
    """Draw a tunnel-portal marker where each line crosses the river, ON TOP of the
    network (unlike the terrain band, which sits under it). A map with no rivers
    (CLASSIC) draws nothing (GM-09c)."""
    rivers = getattr(map_definition, "rivers", ()) or ()
    if not rivers:
        return
    # Lazy import: a rendering module reaches a src-level sibling inside the
    # function (as network_renderer does with config) so the package stays
    # importable both as ``rendering`` and as ``src.rendering`` during discovery.
    from crossings import path_crossings

    for path in paths:
        positions = [station.position for station in getattr(path, "stations", ())]
        for point in path_crossings(
            positions, getattr(path, "is_looped", False), rivers
        ):
            pygame.draw.circle(
                surface,
                CROSSING_MARKER_COLOR,
                (round(point.left), round(point.top)),
                CROSSING_MARKER_RADIUS,
            )

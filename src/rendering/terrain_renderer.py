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

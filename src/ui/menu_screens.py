"""Deterministic title and pause-menu chrome for the human app shell.

Layout functions expose the exact hit-test rects the controller uses; draw
functions paint byte-stable chrome onto the surface they are given and never
touch gameplay state or game RNG.
"""

from __future__ import annotations

import pygame

from config import (
    font_name,
    game_over_button_border_color,
    game_over_button_border_width,
    game_over_button_color,
    game_over_button_height,
    game_over_button_spacing,
    game_over_button_width,
    game_over_hint_font_size,
    game_over_text_color,
)

_TITLE_HEADING = "MINI METRO"
_PAUSE_HEADING = "PAUSED"
_HEADING_FONT_SIZE = 96
_HEADING_GAP = 60


def _font(name: str | None, size: int) -> pygame.font.Font:
    """Return a deterministic font built from pygame's bundled default.

    A fresh font per call keeps byte-stable rendering while staying valid across
    the ``pygame.quit()``/``init()`` cycles that per-class test fixtures drive; a
    retained module-level cache would hand back fonts a prior quit had voided.
    """

    del name  # Text uses pygame's bundled font for portable headless rendering.
    if not pygame.font.get_init():
        pygame.font.init()
    return pygame.font.Font(None, int(size))


def _stacked_buttons(
    width: int, keys: tuple[str, ...], top: int
) -> dict[str, pygame.Rect]:
    layout: dict[str, pygame.Rect] = {}
    for key in keys:
        rect = pygame.Rect(0, 0, game_over_button_width, game_over_button_height)
        rect.centerx = width // 2
        rect.top = top
        layout[key] = rect
        top = rect.bottom + game_over_button_spacing
    return layout


def title_layout(width: int, height: int) -> dict[str, pygame.Rect]:
    """Deterministic, disjoint hit-test rects for the title-screen controls."""

    # Three stacked buttons (New Game / Continue / Exit) centered on the middle
    # slot, so all three stay on-screen and pairwise-disjoint; the heading stays
    # anchored to the first key.
    return _stacked_buttons(
        width,
        ("new_game", "continue", "exit"),
        height // 2 - game_over_button_height - game_over_button_spacing,
    )


def pause_menu_layout(width: int, height: int) -> dict[str, pygame.Rect]:
    """Deterministic, disjoint hit-test rects for the pause-menu controls."""

    return _stacked_buttons(
        width,
        ("resume", "restart", "exit_to_title"),
        height // 2 - game_over_button_height - game_over_button_spacing,
    )


def _draw_button(surface: pygame.Surface, rect: pygame.Rect, label: str) -> None:
    # Every text blit sits on an opaque fill painted in the same call, so
    # repeated draws over existing chrome stay byte-identical.
    pygame.draw.rect(surface, game_over_button_color, rect, border_radius=8)
    pygame.draw.rect(
        surface,
        game_over_button_border_color,
        rect,
        game_over_button_border_width,
        border_radius=8,
    )
    text = _font(font_name, game_over_hint_font_size).render(
        label, True, game_over_text_color
    )
    surface.blit(text, text.get_rect(center=rect.center))


def _draw_heading(surface: pygame.Surface, width: int, bottom: int, label: str) -> None:
    text = _font(font_name, _HEADING_FONT_SIZE).render(
        label, True, game_over_text_color
    )
    banner = text.get_rect(midbottom=(width // 2, bottom)).inflate(80, 40)
    pygame.draw.rect(surface, game_over_button_color, banner, border_radius=12)
    pygame.draw.rect(
        surface,
        game_over_button_border_color,
        banner,
        game_over_button_border_width,
        border_radius=12,
    )
    surface.blit(text, text.get_rect(center=banner.center))


def draw_title_screen(
    surface: pygame.Surface, continue_available: bool = False
) -> None:
    """Paint deterministic title chrome; draw Continue only when available."""

    width, height = surface.get_size()
    layout = title_layout(width, height)
    _draw_heading(surface, width, layout["new_game"].top - _HEADING_GAP, _TITLE_HEADING)
    _draw_button(surface, layout["new_game"], "New Game")
    if continue_available:
        _draw_button(surface, layout["continue"], "Continue")
    _draw_button(surface, layout["exit"], "Exit")


def draw_notice(surface: pygame.Surface, message: str) -> None:
    """Paint a byte-stable opaque failure banner above the title controls."""

    width, height = surface.get_size()
    text = _font(font_name, game_over_hint_font_size).render(
        message, True, game_over_text_color
    )
    # An opaque banner painted in the same call keeps repeated draws identical.
    banner = text.get_rect(center=(width // 2, height // 6)).inflate(60, 30)
    pygame.draw.rect(surface, game_over_button_color, banner, border_radius=8)
    pygame.draw.rect(
        surface,
        game_over_button_border_color,
        banner,
        game_over_button_border_width,
        border_radius=8,
    )
    surface.blit(text, text.get_rect(center=banner.center))


def draw_pause_menu(surface: pygame.Surface) -> None:
    """Paint deterministic pause-menu chrome onto the given surface only."""

    width, height = surface.get_size()
    layout = pause_menu_layout(width, height)
    _draw_heading(surface, width, layout["resume"].top - _HEADING_GAP, _PAUSE_HEADING)
    for key, label in (
        ("resume", "Resume"),
        ("restart", "Restart"),
        ("exit_to_title", "Exit to Title"),
    ):
        _draw_button(surface, layout[key], label)

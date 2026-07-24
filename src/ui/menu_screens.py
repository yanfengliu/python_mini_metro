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
_SETTINGS_HEADING = "SETTINGS"
_BEST_INDICATOR_TEXT = "NEW BEST"
_HEADING_FONT_SIZE = 96
_TUTORIAL_SUBLINE_FONT_SIZE = 26
_HEADING_GAP = 60
# Settings rows carry value labels ("Reduced Motion: On"), so they use a wider
# button than the menu stacks; centering is on the screen midline regardless.
_SETTINGS_BUTTON_WIDTH = 620
_SETTINGS_KEYS = (
    "fullscreen",
    "master_volume",
    "music_volume",
    "sfx_volume",
    "reduced_motion",
    "back",
)


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
    width: int,
    keys: tuple[str, ...],
    top: int,
    button_width: int = game_over_button_width,
) -> dict[str, pygame.Rect]:
    layout: dict[str, pygame.Rect] = {}
    for key in keys:
        rect = pygame.Rect(0, 0, button_width, game_over_button_height)
        rect.centerx = width // 2
        rect.top = top
        layout[key] = rect
        top = rect.bottom + game_over_button_spacing
    return layout


def title_layout(width: int, height: int) -> dict[str, pygame.Rect]:
    """Deterministic, disjoint hit-test rects for the title-screen controls."""

    # Stacked buttons anchored to the middle slot; each new control is APPENDED
    # (Settings after GM-07c, Tutorial after GM-08c, map picker after GM-09f3) so
    # the prior rects stay byte identical, and the heading stays anchored to the
    # first key.
    return _stacked_buttons(
        width,
        ("new_game", "continue", "exit", "settings", "tutorial", "map"),
        height // 2 - game_over_button_height - game_over_button_spacing,
    )


def pause_menu_layout(width: int, height: int) -> dict[str, pygame.Rect]:
    """Deterministic, disjoint hit-test rects for the pause-menu controls."""

    # Settings is appended after Exit to Title, so the prior three rects are
    # unchanged from GM-07c.
    return _stacked_buttons(
        width,
        ("resume", "restart", "exit_to_title", "settings"),
        height // 2 - game_over_button_height - game_over_button_spacing,
    )


def settings_menu_layout(width: int, height: int) -> dict[str, pygame.Rect]:
    """Deterministic, disjoint hit-test rects for the settings-screen controls."""

    # Six wider rows (fullscreen, three volumes, reduced motion, back) centered
    # vertically so the whole stack stays on-screen.
    count = len(_SETTINGS_KEYS)
    stack_height = (
        count * game_over_button_height + (count - 1) * game_over_button_spacing
    )
    return _stacked_buttons(
        width,
        _SETTINGS_KEYS,
        height // 2 - stack_height // 2,
        button_width=_SETTINGS_BUTTON_WIDTH,
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
    surface: pygame.Surface,
    continue_available: bool = False,
    current_map_id: str = "classic",
) -> None:
    """Paint deterministic title chrome; draw Continue only when available.

    GM-09f3 (D-040): the appended map-picker button shows the map a New Game will
    build (``current_map_id``); clicking it cycles the choice.
    """

    width, height = surface.get_size()
    layout = title_layout(width, height)
    _draw_heading(surface, width, layout["new_game"].top - _HEADING_GAP, _TITLE_HEADING)
    _draw_button(surface, layout["new_game"], "New Game")
    if continue_available:
        _draw_button(surface, layout["continue"], "Continue")
    _draw_button(surface, layout["exit"], "Exit")
    _draw_button(surface, layout["settings"], "Settings")
    _draw_button(surface, layout["tutorial"], "Tutorial")
    _draw_button(surface, layout["map"], f"Map: {current_map_id.title()}")


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


def draw_tutorial_overlay(
    surface: pygame.Surface, prompt: str, ordinal: int, total: int, done: bool
) -> None:
    """Paint a byte-stable coaching banner near the bottom of the game frame.

    Two lines on an opaque banner (the prompt plus a progress/skip subline), the
    fill repainted before the text every call so repeated draws stay identical.
    """

    width, height = surface.get_size()
    subline = (
        "Press Esc to return" if done else f"Step {ordinal}/{total}    Esc to skip"
    )
    prompt_text = _font(font_name, game_over_hint_font_size).render(
        prompt, True, game_over_text_color
    )
    sub_text = _font(font_name, _TUTORIAL_SUBLINE_FONT_SIZE).render(
        subline, True, game_over_text_color
    )
    center_y = height - height // 6
    prompt_rect = prompt_text.get_rect(center=(width // 2, center_y - 20))
    sub_rect = sub_text.get_rect(center=(width // 2, center_y + 22))
    banner = prompt_rect.union(sub_rect).inflate(80, 44)
    pygame.draw.rect(surface, game_over_button_color, banner, border_radius=10)
    pygame.draw.rect(
        surface,
        game_over_button_border_color,
        banner,
        game_over_button_border_width,
        border_radius=10,
    )
    surface.blit(prompt_text, prompt_rect)
    surface.blit(sub_text, sub_rect)


def draw_best_indicator(surface: pygame.Surface, result: object) -> None:
    """Paint a byte-stable "new best" banner, but only for an is_best result.

    A ``None`` or non-best result leaves the surface untouched, so ``main`` can
    call this unconditionally after the game-over frame (D-028). The opaque fill
    is repainted before the text every call, so redraws stay byte-identical.
    """

    if result is None or not result.is_best:
        return
    width, height = surface.get_size()
    text = _font(font_name, game_over_hint_font_size).render(
        _BEST_INDICATOR_TEXT, True, game_over_text_color
    )
    banner = text.get_rect(center=(width // 2, height // 4)).inflate(60, 30)
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
        ("settings", "Settings"),
    ):
        _draw_button(surface, layout[key], label)


def _on_off(value: bool) -> str:
    return "On" if value else "Off"


def draw_settings_menu(surface: pygame.Surface, settings: object) -> None:
    """Paint deterministic settings chrome reflecting the current ``settings``.

    Byte-stable for a given ``settings`` value: every label sits on an opaque
    fill painted in the same call, so redraws over existing chrome are
    identical. Volumes read as integer percents; the toggles read On/Off.
    """

    width, height = surface.get_size()
    layout = settings_menu_layout(width, height)
    _draw_heading(
        surface, width, layout["fullscreen"].top - _HEADING_GAP, _SETTINGS_HEADING
    )
    # Volumes are stored only until the GM-08b audio backend consumes them, so
    # the rows say so and set no expectation of an audible effect yet.
    rows = (
        ("fullscreen", f"Fullscreen: {_on_off(settings.fullscreen)}"),
        ("master_volume", f"Master Volume: {settings.master_volume}% (stored)"),
        ("music_volume", f"Music Volume: {settings.music_volume}% (stored)"),
        ("sfx_volume", f"SFX Volume: {settings.sfx_volume}% (stored)"),
        ("reduced_motion", f"Reduced Motion: {_on_off(settings.reduced_motion)}"),
        ("back", "Back"),
    )
    for key, label in rows:
        _draw_button(surface, layout[key], label)

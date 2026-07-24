"""GM-08a red contract: the AppController SETTINGS screen and settings seam (D-029).

The controller gains an ``AppScreen.SETTINGS`` state reachable from TITLE and
PAUSE_MENU through an appended ``settings`` menu entry, an optional inert
``settings`` seam (``load() -> Settings``, ``save(Settings)``), a public
``current_settings``, and a ``back`` control that returns to the origin screen.
Entering settings from the pause menu keeps the ``menu`` pause hold. Each
control edits ``current_settings`` in memory and persists through the seam
exactly once; a seam-less controller updates in memory but never persists.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from app_controller import AppController, AppScreen
from config import screen_height, screen_width
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from settings import DEFAULT_SETTINGS, Settings
from ui.menu_screens import pause_menu_layout, settings_menu_layout, title_layout


class _FakeMediator:
    def __init__(self) -> None:
        self.is_game_over = False
        self.held: list[str] = []

    def hold_pause_reason(self, reason: str) -> None:
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason: str) -> None:
        if reason in self.held:
            self.held.remove(reason)


class _FakeSession:
    def dispatch(self, event: object) -> None:
        pass


def _factory():
    def build(map_id="classic"):
        return (_FakeMediator(), object(), _FakeSession())

    return build


class _FakeSettingsSeam:
    def __init__(self, loaded: Settings | None = None) -> None:
        self._loaded = loaded if loaded is not None else DEFAULT_SETTINGS
        self.saved: list[Settings] = []

    def load(self) -> Settings:
        return self._loaded

    def save(self, settings: Settings) -> None:
        self.saved.append(settings)


def _center(layout, key: str) -> Point:
    rect = layout(screen_width, screen_height)[key]
    return Point(int(rect.centerx), int(rect.centery))


def _controller(seam=None, start_state=AppScreen.TITLE):
    return AppController(_factory(), start_state=start_state, settings=seam)


def _up(controller, point: Point) -> None:
    controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, point))


def _down(controller, point: Point) -> None:
    controller.handle_event(MouseEvent(MouseEventType.MOUSE_DOWN, point))


class TestGM08aSettingsSeam(unittest.TestCase):
    def test_current_settings_loads_from_the_seam_at_construction(self):
        loaded = Settings(fullscreen=True, master_volume=25, reduced_motion=True)
        controller = _controller(_FakeSettingsSeam(loaded))
        self.assertEqual(controller.current_settings, loaded)

    def test_seamless_controller_uses_defaults(self):
        controller = _controller(seam=None)
        self.assertEqual(controller.current_settings, DEFAULT_SETTINGS)

    def test_settings_is_an_optional_kwarg_backward_compatible(self):
        # A controller built with no settings seam is behaviorally the GM-07d
        # baseline: only the four prior screens exist in its normal flow.
        controller = AppController(_factory(), start_state=AppScreen.PLAYING)
        self.assertEqual(controller.current_settings, DEFAULT_SETTINGS)


class TestGM08aSettingsNavigation(unittest.TestCase):
    def test_title_to_settings_and_back(self):
        controller = _controller(_FakeSettingsSeam())
        _up(controller, _center(title_layout, "settings"))
        self.assertEqual(controller.state, AppScreen.SETTINGS)
        _up(controller, _center(settings_menu_layout, "back"))
        self.assertEqual(controller.state, AppScreen.TITLE)

    def test_pause_to_settings_keeps_the_menu_hold_and_back_returns_to_pause(self):
        controller = _controller(_FakeSettingsSeam(), start_state=AppScreen.PLAYING)
        controller.handle_event(
            KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_ESCAPE)
        )
        self.assertEqual(controller.state, AppScreen.PAUSE_MENU)
        self.assertIn("menu", controller.mediator.held)
        # Arm-on-press then release inside the pause "settings" control.
        _down(controller, _center(pause_menu_layout, "settings"))
        _up(controller, _center(pause_menu_layout, "settings"))
        self.assertEqual(controller.state, AppScreen.SETTINGS)
        self.assertIn(
            "menu", controller.mediator.held, "entering settings keeps the pause hold"
        )
        _up(controller, _center(settings_menu_layout, "back"))
        self.assertEqual(controller.state, AppScreen.PAUSE_MENU)
        self.assertIn("menu", controller.mediator.held, "back keeps the pause hold")


class TestGM08aSettingsControls(unittest.TestCase):
    def _enter_settings(self, seam):
        controller = _controller(seam)
        _up(controller, _center(title_layout, "settings"))
        return controller

    def test_toggle_fullscreen_updates_and_persists_once(self):
        seam = _FakeSettingsSeam()
        controller = self._enter_settings(seam)
        _up(controller, _center(settings_menu_layout, "fullscreen"))
        self.assertIs(controller.current_settings.fullscreen, True)
        self.assertEqual(seam.saved, [controller.current_settings])
        _up(controller, _center(settings_menu_layout, "fullscreen"))
        self.assertIs(controller.current_settings.fullscreen, False)
        self.assertEqual(len(seam.saved), 2, "each toggle persists exactly once")

    def test_toggle_reduced_motion_updates_and_persists(self):
        seam = _FakeSettingsSeam()
        controller = self._enter_settings(seam)
        _up(controller, _center(settings_menu_layout, "reduced_motion"))
        self.assertIs(controller.current_settings.reduced_motion, True)
        self.assertEqual(seam.saved[-1].reduced_motion, True)

    def test_volume_cycles_on_the_grid_and_persists(self):
        seam = _FakeSettingsSeam()
        controller = self._enter_settings(seam)  # master starts at 100
        _up(controller, _center(settings_menu_layout, "master_volume"))
        self.assertEqual(controller.current_settings.master_volume, 0, "100 wraps to 0")
        _up(controller, _center(settings_menu_layout, "master_volume"))
        self.assertEqual(controller.current_settings.master_volume, 25)
        self.assertEqual(len(seam.saved), 2)
        # other volumes are untouched
        self.assertEqual(controller.current_settings.music_volume, 100)
        self.assertEqual(controller.current_settings.sfx_volume, 100)

    def test_seamless_edit_updates_memory_but_never_persists(self):
        controller = self._enter_settings(seam=None)
        _up(controller, _center(settings_menu_layout, "fullscreen"))
        self.assertIs(
            controller.current_settings.fullscreen,
            True,
            "a seam-less edit still updates current_settings in memory",
        )
        # No seam exists to persist to, and nothing raises.
        self.assertEqual(controller.state, AppScreen.SETTINGS)


if __name__ == "__main__":
    unittest.main()

"""GM-08a red contract: reduced-motion render gating and the settings chrome (D-029).

Reduced motion holds the passenger-warning and unlock blinks VISIBLE (steady,
not flashing) and SUPPRESSES the one-shot station snap blips; every default
(``reduced_motion=False``) path is byte-identical to pre-GM-08a output, which
the rest of the render suite already pins. ``draw_settings_menu`` paints
byte-stable chrome reflecting the current settings value.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import (
    passenger_blink_interval_ms,
    station_size,
    station_snap_blip_duration_ms,
    unlock_blink_duration_ms,
)
from entity.carriage import Carriage
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from rendering.flexible_draw import _call_flexibly
from settings import DEFAULT_SETTINGS, Settings
from ui.menu_screens import draw_settings_menu

_SRC_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "src")
_RUNTIME_SURFACES = (
    "env.py",
    "agent_play.py",
    "recursive_playtest.py",
    "recursive_checkpoint.py",
)

_BG = (0, 0, 0)


def _surface(size=(120, 120)) -> pygame.Surface:
    surface = pygame.Surface(size)
    surface.fill(_BG)
    return surface


def _bytes(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGB")


def _blank(size=(120, 120)) -> bytes:
    return _bytes(_surface(size))


class TestGM08aReducedMotionPassenger(unittest.TestCase):
    def _blinking_passenger(self):
        passenger = Passenger(Circle((255, 0, 0), 10))
        passenger.position = Point(60, 60)
        passenger.wait_ms = 500  # waiting too long -> should_blink_for_wait True
        return passenger

    def test_warning_blink_off_phase_is_held_visible_under_reduced_motion(self):
        passenger = self._blinking_passenger()
        # A time whose blink phase is odd -> is_warning_blink_visible is False.
        off_time = passenger_blink_interval_ms
        self.assertFalse(passenger.is_warning_blink_visible(off_time))

        normal = _surface()
        passenger.draw(
            normal,
            current_time_ms=off_time,
            max_wait_time_ms=100,
            display_position=Point(60, 60),
            reduced_motion=False,
        )
        self.assertEqual(_bytes(normal), _blank(), "blink-off skips the draw normally")

        reduced = _surface()
        passenger.draw(
            reduced,
            current_time_ms=off_time,
            max_wait_time_ms=100,
            display_position=Point(60, 60),
            reduced_motion=True,
        )
        self.assertNotEqual(
            _bytes(reduced), _blank(), "reduced motion holds the passenger visible"
        )

    def test_default_matches_the_no_argument_call(self):
        passenger = self._blinking_passenger()
        # A blink-OFF phase exercises the SKIP branch: default False and the
        # historical no-kwarg call must both skip and stay blank (codex).
        off_time = passenger_blink_interval_ms
        explicit = _surface()
        implicit = _surface()
        passenger.draw(
            explicit,
            current_time_ms=off_time,
            max_wait_time_ms=100,
            display_position=Point(60, 60),
            reduced_motion=False,
        )
        passenger.draw(
            implicit,
            current_time_ms=off_time,
            max_wait_time_ms=100,
            display_position=Point(60, 60),
        )
        self.assertEqual(
            _bytes(explicit), _blank(), "explicit False skips at off phase"
        )
        self.assertEqual(
            _bytes(explicit), _bytes(implicit), "default is byte-identical to no-kwarg"
        )


class TestGM08aReducedMotionStation(unittest.TestCase):
    def _station(self):
        station = Station(Circle((0, 255, 0), station_size), Point(60, 60))
        return station

    def test_unlock_blink_off_phase_is_held_visible_under_reduced_motion(self):
        station = self._station()
        station.start_unlock_blink(0)
        # A time inside the blink window whose phase is off (not visible).
        off_time = next(
            t
            for t in range(0, unlock_blink_duration_ms, 5)
            if station.is_unlock_blink_active(t)
            and not station.is_unlock_blink_visible(t)
        )
        normal = _surface()
        station.draw(normal, current_time_ms=off_time, reduced_motion=False)
        reduced = _surface()
        station.draw(reduced, current_time_ms=off_time, reduced_motion=True)
        self.assertEqual(_bytes(normal), _blank(), "the off phase hides the station")
        self.assertNotEqual(
            _bytes(reduced), _blank(), "reduced motion holds the station visible"
        )

    def test_snap_blip_is_suppressed_under_reduced_motion(self):
        # With the unlock blink inactive both draw the station; the difference is
        # the one-shot snap blip ring, which reduced motion suppresses.
        # Mid-blip, the expanding ring has grown past the station radius.
        blip_time = station_snap_blip_duration_ms // 2
        base = self._station()
        base.start_snap_blip(0, (0, 0, 255))
        with_blip = _surface()
        base.draw(with_blip, current_time_ms=blip_time, reduced_motion=False)

        other = self._station()
        other.start_snap_blip(0, (0, 0, 255))
        without_blip = _surface()
        other.draw(without_blip, current_time_ms=blip_time, reduced_motion=True)

        self.assertNotEqual(
            _bytes(with_blip),
            _bytes(without_blip),
            "the snap blip is drawn normally but suppressed under reduced motion",
        )


class TestGM08aReducedMotionPathButton(unittest.TestCase):
    def test_unlock_blink_off_phase_is_held_visible_under_reduced_motion(self):
        from ui.path_button import PathButton

        button = PathButton(Circle((0, 200, 200), 24), Point(60, 60))
        button.is_locked = True
        button.start_unlock_blink(0)
        off_time = next(
            t
            for t in range(0, unlock_blink_duration_ms, 5)
            if button.is_unlock_blink_active(t)
            and not button.is_unlock_blink_visible(t)
        )
        normal = _surface()
        button.draw(normal, current_time_ms=off_time, reduced_motion=False)
        reduced = _surface()
        button.draw(reduced, current_time_ms=off_time, reduced_motion=True)
        self.assertEqual(_bytes(normal), _blank(), "the off phase hides the button")
        self.assertNotEqual(
            _bytes(reduced), _blank(), "reduced motion holds the path button visible"
        )


class TestGM08aReducedMotionCarriage(unittest.TestCase):
    def test_carriage_riders_are_held_visible_under_reduced_motion(self):
        # Regression for the carriage-rider gap (codex MAJOR): a metro carriage
        # holds passengers, and reduced motion must reach them too. The renderer
        # dispatches every consist body through _call_flexibly, so route the
        # carriage draw the same way to prove reduced_motion is not filtered out.
        carriage = Carriage()
        carriage.position = Point(100, 100)
        passenger = Passenger(Circle((255, 0, 0), 8))
        passenger.wait_ms = 500  # waiting too long -> should_blink_for_wait True
        off_time = passenger_blink_interval_ms  # blink-off phase

        normal = _surface((200, 200))
        _call_flexibly(
            carriage.draw,
            normal,
            passengers=[passenger],
            current_time_ms=off_time,
            passenger_max_wait_time_ms=100,
            reduced_motion=False,
        )
        reduced = _surface((200, 200))
        _call_flexibly(
            carriage.draw,
            reduced,
            passengers=[passenger],
            current_time_ms=off_time,
            passenger_max_wait_time_ms=100,
            reduced_motion=True,
        )
        self.assertNotEqual(
            _bytes(reduced),
            _bytes(normal),
            "reduced motion must hold carriage riders visible, not just metro riders",
        )


class TestGM08aSettingsIsolation(unittest.TestCase):
    def test_runtime_surfaces_import_no_settings_module(self):
        # Settings and the GM-08b audio backend are main-only seams; headless/RL
        # surfaces must never import either (codex MINOR: pin the membership from
        # GM-08a/GM-08b here, not only via GM-07b).
        import ast

        forbidden = {"settings", "audio", "tutorial"}

        targets: list[str] = list(_RUNTIME_SURFACES)
        rl_dir = os.path.join(_SRC_ROOT, "rl")
        targets.extend(
            os.path.join("rl", name)
            for name in os.listdir(rl_dir)
            if name.endswith(".py")
        )
        self.assertGreater(len(targets), 4)
        for relative in targets:
            path = os.path.join(_SRC_ROOT, relative)
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    self.assertNotIn(
                        name.split(".")[0],
                        forbidden,
                        f"{relative} imports a main-only module: {name}",
                    )


class TestGM08aSettingsMenuChrome(unittest.TestCase):
    def test_draw_settings_menu_is_byte_stable(self):
        surface_a = pygame.Surface((1280, 720))
        surface_a.fill(_BG)
        surface_b = surface_a.copy()
        draw_settings_menu(surface_a, DEFAULT_SETTINGS)
        draw_settings_menu(surface_b, DEFAULT_SETTINGS)
        self.assertEqual(
            _bytes(surface_a), _bytes(surface_b), "same value -> same bytes"
        )

    def test_draw_settings_menu_reflects_the_value(self):
        base = pygame.Surface((1280, 720))
        base.fill(_BG)
        default_surface = base.copy()
        toggled_surface = base.copy()
        draw_settings_menu(default_surface, DEFAULT_SETTINGS)
        draw_settings_menu(toggled_surface, Settings(fullscreen=True, master_volume=25))
        self.assertNotEqual(
            _bytes(default_surface),
            _bytes(toggled_surface),
            "a different settings value paints different chrome",
        )


if __name__ == "__main__":
    unittest.main()

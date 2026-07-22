"""GM-07a implementation-review F2 regression: pause-menu controls arm on press.

A pause-menu control fires only when a MOUSE_DOWN inside its rect while the
menu is open is followed by a MOUSE_UP inside the same control's rect. A bare
release -- e.g. a gameplay drag released over Restart after Escape opened the
menu mid-drag -- is a no-op, and arming clears on every release and on leaving
the menu state, so a stray press can never fire on a later menu visit.
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
from ui.menu_screens import pause_menu_layout


def _center(key: str) -> Point:
    rect = pause_menu_layout(screen_width, screen_height)[key]
    return Point(int(rect.centerx), int(rect.centery))


class _FakeMediator:
    def __init__(self, name: str) -> None:
        self.name = name
        self.is_game_over = False
        self.held: list[str] = []

    def hold_pause_reason(self, reason: str) -> None:
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason: str) -> None:
        if reason in self.held:
            self.held.remove(reason)


class _FakeSession:
    def __init__(self, log: list, name: str) -> None:
        self.log = log
        self.name = name

    def dispatch(self, event: object) -> None:
        self.log.append((self.name, "dispatch", event))


def _factory(log: list):
    triples: list[tuple[_FakeMediator, object, _FakeSession]] = []

    def build():
        index = len(triples)
        triple = (
            _FakeMediator(f"mediator-{index}"),
            object(),
            _FakeSession(log, f"session-{index}"),
        )
        triples.append(triple)
        return triple

    build.triples = triples
    return build


class TestGM07aPauseMenuArming(unittest.TestCase):
    def setUp(self) -> None:
        self.log: list = []
        self.build = _factory(self.log)
        self.controller = AppController(self.build, start_state=AppScreen.PLAYING)
        self.outside = Point(12, 540)
        for key, rect in pause_menu_layout(screen_width, screen_height).items():
            self.assertFalse(
                rect.collidepoint((self.outside.left, self.outside.top)),
                f"the outside probe point overlaps the {key!r} control",
            )

    def _down(self, point: Point) -> None:
        self.controller.handle_event(MouseEvent(MouseEventType.MOUSE_DOWN, point))

    def _up(self, point: Point) -> None:
        self.controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, point))

    def _escape(self) -> None:
        self.controller.handle_event(
            KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_ESCAPE)
        )

    def _open_menu_mid_drag(self) -> None:
        # Arm a gameplay drag, then open the menu with the button still held.
        self._down(self.outside)
        self._escape()
        self.assertEqual(self.controller.state, AppScreen.PAUSE_MENU)
        self.assertEqual(self.build.triples[0][0].held, ["menu"])

    def _assert_menu_untouched(self) -> None:
        self.assertEqual(self.controller.state, AppScreen.PAUSE_MENU)
        self.assertEqual(len(self.build.triples), 1)
        self.assertEqual(self.build.triples[0][0].held, ["menu"])

    def test_mid_drag_release_over_restart_is_a_no_op_until_armed(self):
        self._open_menu_mid_drag()
        quiet_from = len(self.log)
        restart = _center("restart")
        self._up(restart)  # the released drag: no press armed Restart
        self._assert_menu_untouched()
        self._down(restart)  # a deliberate press arms but must not fire yet
        self._assert_menu_untouched()
        self._up(restart)  # press-and-release on the same control fires
        self.assertEqual(self.controller.state, AppScreen.PLAYING)
        self.assertEqual(len(self.build.triples), 2, "restart must reconstruct")
        self.assertEqual(self.build.triples[0][0].held, [])
        self.assertEqual(
            self.log[quiet_from:], [], "menu mouse traffic must never dispatch"
        )

    def test_release_fires_only_the_control_its_own_press_armed(self):
        self._open_menu_mid_drag()
        resume = _center("resume")
        restart = _center("restart")
        self._down(restart)
        self._up(self.outside)  # press on Restart, release elsewhere: disarmed
        self._assert_menu_untouched()
        self._up(restart)  # the previous release already cleared the arming
        self._assert_menu_untouched()
        self._down(self.outside)
        self._up(restart)  # press outside every control, release on Restart
        self._assert_menu_untouched()
        self._down(resume)
        self._up(restart)  # press and release on different controls
        self._assert_menu_untouched()
        self._down(resume)
        self._up(resume)
        self.assertEqual(self.controller.state, AppScreen.PLAYING)
        self.assertEqual(len(self.build.triples), 1, "resume must not reconstruct")
        self.assertEqual(self.build.triples[0][0].held, [])

    def test_arming_clears_when_the_menu_state_exits(self):
        self._open_menu_mid_drag()
        restart = _center("restart")
        self._down(restart)  # armed...
        self._escape()  # ...but Escape closes the menu (state exit clears it)
        self.assertEqual(self.controller.state, AppScreen.PLAYING)
        self._escape()  # reopen the menu
        self.assertEqual(self.controller.state, AppScreen.PAUSE_MENU)
        self._up(restart)  # a stale press from the last visit must not fire
        self._assert_menu_untouched()


if __name__ == "__main__":
    unittest.main()

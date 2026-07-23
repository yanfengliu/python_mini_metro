"""GM-08c red contract: the AppController TUTORIAL wiring (D-031).

A menu-launched coached tutorial: a `build_tutorial` seam starts a seeded game in
a new `AppScreen.TUTORIAL`; real controls dispatch to the live session; a
per-frame `advance_tutorial` advances the step machine; Escape returns to the
title (with the letterbox-cancel); and the tutorial never autosaves or records a
high score. A seam-less controller keeps the Tutorial entry inert.
"""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

import pygame

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from app_controller import AppController, AppScreen  # noqa: E402
from config import screen_height, screen_width  # noqa: E402
from event.keyboard import KeyboardEvent  # noqa: E402
from event.mouse import MouseEvent  # noqa: E402
from event.type import KeyboardEventType, MouseEventType  # noqa: E402
from geometry.point import Point  # noqa: E402
from ui.menu_screens import title_layout  # noqa: E402


def _fake_mediator(**over):
    base = dict(
        paths=[],
        metros=[],
        deliveries=0,
        is_paused=False,
        game_speed_multiplier=1,
        stations=[],
        is_game_over=False,
    )
    base.update(over)
    return SimpleNamespace(**base)


class _FakeSession:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


def _triple(mediator=None):
    return (mediator or _fake_mediator(), SimpleNamespace(), _FakeSession())


def _controller(with_tutorial=True, autosave=None, highscores=None):
    play = _triple()
    tut = _triple()

    def build_game():
        return play

    def build_tutorial():
        return tut

    controller = AppController(
        build_game,
        start_state=AppScreen.TITLE,
        autosave=autosave,
        highscores=highscores,
        build_tutorial=build_tutorial if with_tutorial else None,
    )
    return controller, tut


def _click(controller, key):
    layout = title_layout(screen_width, screen_height)
    rect = layout[key]
    controller.handle_event(
        MouseEvent(MouseEventType.MOUSE_UP, Point(rect.centerx, rect.centery))
    )


class TestGM08cTutorialController(unittest.TestCase):
    def test_title_tutorial_entry_starts_a_seeded_game_in_tutorial(self):
        controller, tut = _controller()
        _click(controller, "tutorial")
        self.assertIs(controller.state, AppScreen.TUTORIAL)
        self.assertIs(controller.mediator, tut[0], "the tutorial's own triple is live")
        self.assertIsNotNone(controller.tutorial_overlay(), "a progress exists")

    def test_cold_start_in_tutorial_builds_the_tutorial(self):
        # Review MODERATE-3: run_game(start_state=TUTORIAL) must build the seeded
        # tutorial + progress, not leave the ordinary build_game triple (which
        # would game-over and freeze with no overlay).
        tut = _triple()
        controller = AppController(
            lambda: _triple(),
            start_state=AppScreen.TUTORIAL,
            build_tutorial=lambda: tut,
        )
        self.assertIs(controller.state, AppScreen.TUTORIAL)
        self.assertIs(controller.mediator, tut[0], "the tutorial triple is live")
        self.assertIsNotNone(controller.tutorial_overlay(), "progress is initialized")

    def test_seamless_tutorial_entry_is_inert(self):
        controller, _ = _controller(with_tutorial=False)
        _click(controller, "tutorial")
        self.assertIs(controller.state, AppScreen.TITLE, "no seam -> inert, no crash")
        self.assertIsNone(controller.tutorial_overlay())

    def test_escape_returns_to_title_with_letterbox_cancel(self):
        controller, tut = _controller()
        _click(controller, "tutorial")
        session = controller.session
        controller.handle_event(
            KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_ESCAPE)
        )
        self.assertIs(controller.state, AppScreen.TITLE)
        cancels = [
            e
            for e in session.dispatched
            if isinstance(e, MouseEvent)
            and e.event_type == MouseEventType.MOUSE_UP
            and (e.position.left, e.position.top) == (-1, -1)
        ]
        self.assertTrue(cancels, "Escape abandons an armed gesture before leaving")

    def test_real_controls_dispatch_to_the_session(self):
        controller, tut = _controller()
        _click(controller, "tutorial")
        event = MouseEvent(MouseEventType.MOUSE_DOWN, Point(100, 100))
        controller.handle_event(event)
        self.assertIn(event, controller.session.dispatched)

    def test_advance_tutorial_is_a_noop_off_tutorial(self):
        controller, _ = _controller()
        # Still on TITLE.
        before = controller.tutorial_overlay()
        controller.advance_tutorial(16)
        self.assertEqual(controller.tutorial_overlay(), before)

    def test_advance_tutorial_advances_on_the_real_signal(self):
        controller, tut = _controller()
        _click(controller, "tutorial")
        _prompt, ordinal, total, _done = controller.tutorial_overlay()
        self.assertEqual((ordinal, total), (1, 7))
        # The player draws a committed line on the tutorial mediator.
        controller.mediator.paths = [
            SimpleNamespace(
                id="A",
                stations=[SimpleNamespace(id="s1"), SimpleNamespace(id="s2")],
                is_looped=False,
                is_being_created=False,
            )
        ]
        controller.advance_tutorial(16)
        self.assertEqual(controller.tutorial_overlay()[1], 2, "draw advances to step 2")

    def test_tutorial_never_autosaves_or_records(self):
        autosave = SimpleNamespace(
            save=lambda m: self.fail("tutorial must not autosave"),
            delete=lambda: None,
            peek=lambda: False,
            load=lambda: None,
        )
        recorded = []
        highscores = SimpleNamespace(record=lambda d: recorded.append(d))
        controller, tut = _controller(autosave=autosave, highscores=highscores)
        _click(controller, "tutorial")
        controller.mediator.deliveries = 5
        controller.advance_tutorial(16)
        controller.handle_event(
            KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_ESCAPE)
        )
        self.assertEqual(recorded, [], "tutorial never records a high score")


if __name__ == "__main__":
    unittest.main()

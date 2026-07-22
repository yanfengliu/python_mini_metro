"""GM-07c red contract: AppController autosave/Continue seams (D-027).

Drives a real ``AppController`` with a spy autosave seam (recording
``save``/``delete``/``peek``/``load`` with the saved mediator identity) plus
injected ``build_game``/``build_from`` factories, pinning the exact wiring the
folded D-027 policy requires: save on menu entry and on ``exit_to_title``
before the menu release, delete at the game-over promotion and its exit sites,
never a save from a controller ``SystemExit`` site or ``GAME_OVER``/``TITLE``,
Continue gated on ``peek``, and a load-failure notice that keeps ``TITLE``.

Every missing product surface is turned into a clean FAILURE (not an
import/collection ERROR) through the ``require_attribute`` guards, mirroring
``test_gm07b_save_roundtrip``.
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from mediator import Mediator


def _module(testcase, name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-07c product module is missing: {name} ({error})")


def _symbol(testcase, module_name, name):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-07c product symbol is missing: {module_name}.{name}"
    )
    return value


def _screen(testcase, name):
    states = _symbol(testcase, "app_controller", "AppScreen")
    testcase.assertTrue(
        hasattr(states, name), f"GM-07c AppScreen member is missing: {name}"
    )
    return getattr(states, name)


def _require_seam_signature(testcase):
    controller_type = _symbol(testcase, "app_controller", "AppController")
    parameters = inspect.signature(controller_type).parameters
    for name in ("build_from", "autosave"):
        testcase.assertIn(
            name,
            parameters,
            f"GM-07c: AppController.__init__ must accept an optional {name!r} seam",
        )
    return controller_type


def _seam_controller(
    testcase, build_game, *, start_state, build_from=None, autosave=None
):
    controller_type = _require_seam_signature(testcase)
    return controller_type(
        build_game,
        start_state=start_state,
        build_from=build_from,
        autosave=autosave,
    )


def _rect_center(testcase, layout_name, key):
    layout_fn = _symbol(testcase, "ui.menu_screens", layout_name)
    layout = layout_fn(screen_width, screen_height)
    testcase.assertIn(key, layout, f"{layout_name} must expose the {key!r} rect")
    center = pygame.Rect(layout[key]).center
    return Point(int(center[0]), int(center[1]))


def _press(controller, key):
    controller.handle_event(KeyboardEvent(KeyboardEventType.KEY_UP, key))


def _click(controller, point):
    controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, point))


def _click_center(testcase, controller, layout_name, key):
    _click(controller, _rect_center(testcase, layout_name, key))


def _press_and_release(testcase, controller, layout_name, key):
    # Pause-menu controls arm on the DOWN and fire on the matching UP (GM-07a
    # review F2), so a menu selection is the paired down/up at the rect center.
    point = _rect_center(testcase, layout_name, key)
    controller.handle_event(MouseEvent(MouseEventType.MOUSE_DOWN, point))
    controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, point))


class _RecordingMediator:
    """Identity-bearing mediator stub exposing only the controller's surface."""

    def __init__(self, name):
        self.name = name
        self.is_game_over = False
        self.held = []
        self.game_over_result = None

    def hold_pause_reason(self, reason):
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason):
        if reason in self.held:
            self.held.remove(reason)

    def handle_game_over_click(self, position):
        return self.game_over_result


class _RecordingSession:
    def __init__(self, mediator, name):
        self.mediator = mediator
        self.name = name
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


def _factories():
    """Return (build_game, build_from) sharing a recorded triples list."""

    triples = []

    def _wrap(mediator):
        index = len(triples)
        renderer = SimpleNamespace(name=f"renderer-{index}")
        session = _RecordingSession(mediator, f"session-{index}")
        triples.append((mediator, renderer, session))
        return mediator, renderer, session

    def build_game():
        return _wrap(_RecordingMediator(f"mediator-{len(triples)}"))

    def build_from(loaded):
        return _wrap(loaded)

    build_game.triples = triples
    build_from.triples = triples
    return build_game, build_from


class _SpyAutosave:
    """Records every seam call; ``peek``/``load`` outcomes are configurable."""

    def __init__(self, *, peek=False, load_result=None, load_error=None):
        self.calls = []
        self._peek = peek
        self._load_result = load_result
        self._load_error = load_error

    def save(self, mediator):
        self.calls.append(("save", mediator, tuple(getattr(mediator, "held", ()))))

    def delete(self):
        self.calls.append(("delete",))

    def peek(self):
        self.calls.append(("peek",))
        return self._peek

    def load(self):
        self.calls.append(("load",))
        if self._load_error is not None:
            raise self._load_error
        return self._load_result

    def kinds(self):
        return [call[0] for call in self.calls]

    def saves(self):
        return [call for call in self.calls if call[0] == "save"]

    def deletes(self):
        return [call for call in self.calls if call[0] == "delete"]


class TestGM07cAutosaveSeamOptional(unittest.TestCase):
    def test_seams_optional_controller_behaves_like_baseline(self):
        # regression guard: green at baseline
        controller_type = _symbol(self, "app_controller", "AppController")
        build_game, _build_from = _factories()
        controller = controller_type(build_game, start_state=_screen(self, "PLAYING"))
        _press(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PAUSE_MENU"))
        _press(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        controller.mediator.is_game_over = True
        _press(controller, pygame.K_SPACE)
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))


class TestGM07cAutosaveSaveTriggers(unittest.TestCase):
    def _playing(self, autosave):
        build_game, build_from = _factories()
        controller = _seam_controller(
            self,
            build_game,
            start_state=_screen(self, "PLAYING"),
            build_from=build_from,
            autosave=autosave,
        )
        return controller

    def test_menu_entry_saves_once_with_menu_held_and_mediator_identity(self):
        spy = _SpyAutosave()
        controller = self._playing(spy)
        _press(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PAUSE_MENU"))
        saves = spy.saves()
        self.assertEqual(len(saves), 1, f"exactly one menu-entry save: {spy.calls}")
        _kind, saved_mediator, held_at_save = saves[0]
        self.assertIs(saved_mediator, controller.mediator)
        self.assertEqual(
            held_at_save, ("menu",), "the save must observe the held menu reason"
        )
        self.assertEqual(spy.deletes(), [])

    def test_exit_to_title_saves_before_releasing_the_menu_reason(self):
        spy = _SpyAutosave()
        controller = self._playing(spy)
        _press(controller, pygame.K_ESCAPE)
        _press_and_release(self, controller, "pause_menu_layout", "exit_to_title")
        self.assertEqual(controller.state, _screen(self, "TITLE"))
        saves = spy.saves()
        self.assertEqual(len(saves), 2, f"menu entry then exit both save: {spy.calls}")
        self.assertEqual(
            saves[1][2],
            ("menu",),
            "the exit_to_title save must run before the menu reason is released",
        )
        self.assertEqual(
            controller.mediator.held, [], "closing the menu still releases it"
        )

    def test_resume_and_restart_add_no_further_save(self):
        for selection in ("resume", "restart"):
            with self.subTest(selection=selection):
                spy = _SpyAutosave()
                controller = self._playing(spy)
                _press(controller, pygame.K_ESCAPE)
                _press_and_release(self, controller, "pause_menu_layout", selection)
                self.assertEqual(controller.state, _screen(self, "PLAYING"))
                self.assertEqual(
                    len(spy.saves()), 1, f"only the menu-entry save fires: {spy.calls}"
                )

    def test_title_new_game_and_exit_never_save(self):
        spy = _SpyAutosave()
        build_game, build_from = _factories()
        controller = _seam_controller(
            self,
            build_game,
            start_state=_screen(self, "TITLE"),
            build_from=build_from,
            autosave=spy,
        )
        _click_center(self, controller, "title_layout", "new_game")
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertEqual(spy.saves(), [])
        self.assertEqual(spy.deletes(), [])

        spy_exit = _SpyAutosave()
        build_game_exit, build_from_exit = _factories()
        exit_controller = _seam_controller(
            self,
            build_game_exit,
            start_state=_screen(self, "TITLE"),
            build_from=build_from_exit,
            autosave=spy_exit,
        )
        with self.assertRaises(SystemExit):
            _click_center(self, exit_controller, "title_layout", "exit")
        self.assertEqual(spy_exit.saves(), [], "the TITLE exit must not save")


class TestGM07cAutosaveDeleteTriggers(unittest.TestCase):
    def _game_over_ready(self, autosave):
        build_game, build_from = _factories()
        controller = _seam_controller(
            self,
            build_game,
            start_state=_screen(self, "PLAYING"),
            build_from=build_from,
            autosave=autosave,
        )
        controller.mediator.is_game_over = True
        return controller

    def test_promotion_deletes_the_autosave_without_saving(self):
        spy = _SpyAutosave()
        controller = self._game_over_ready(spy)
        _press(controller, pygame.K_SPACE)
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))
        self.assertEqual(len(spy.deletes()), 1, f"one promotion delete: {spy.calls}")
        self.assertEqual(spy.saves(), [], "the game-over promotion must not save")

    def test_game_over_escape_exit_deletes_again_and_never_saves(self):
        spy = _SpyAutosave()
        controller = self._game_over_ready(spy)
        _press(controller, pygame.K_SPACE)
        self.assertEqual(len(spy.deletes()), 1)
        with self.assertRaises(SystemExit):
            _press(controller, pygame.K_ESCAPE)
        self.assertEqual(len(spy.deletes()), 2, "the game-over exit deletes too")
        self.assertEqual(spy.saves(), [])

    def test_game_over_exit_click_deletes_again_and_never_saves(self):
        spy = _SpyAutosave()
        controller = self._game_over_ready(spy)
        mediator = controller.mediator
        _click(controller, Point(320, 200))
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))
        self.assertEqual(len(spy.deletes()), 1)
        mediator.game_over_result = "exit"
        with self.assertRaises(SystemExit):
            _click(controller, Point(320, 200))
        self.assertEqual(len(spy.deletes()), 2)
        self.assertEqual(spy.saves(), [])


class TestGM07cContinue(unittest.TestCase):
    def _title(self, autosave):
        build_game, build_from = _factories()
        controller = _seam_controller(
            self,
            build_game,
            start_state=_screen(self, "TITLE"),
            build_from=build_from,
            autosave=autosave,
        )
        return controller, build_game

    def test_continue_ignored_when_peek_reports_no_save(self):
        spy = _SpyAutosave(peek=False)
        controller, build_game = self._title(spy)
        _click_center(self, controller, "title_layout", "continue")
        self.assertEqual(controller.state, _screen(self, "TITLE"))
        self.assertIn("peek", spy.kinds(), "the click must consult peek()")
        self.assertNotIn("load", spy.kinds(), "an absent save must never be loaded")
        self.assertEqual(len(build_game.triples), 1, "no build_from without a save")

    def test_successful_continue_releases_only_menu_and_swaps_the_triple(self):
        loaded = Mediator(seed=9100)
        loaded.hold_pause_reason("menu")
        loaded.hold_pause_reason("user")
        spy = _SpyAutosave(peek=True, load_result=loaded)
        controller, build_game = self._title(spy)
        _click_center(self, controller, "title_layout", "continue")
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertIn("load", spy.kinds())
        self.assertIs(
            controller.mediator, loaded, "Continue must install the loaded mediator"
        )
        self.assertEqual(
            sorted(loaded._pause_reasons),
            ["user"],
            "Continue releases only the menu reason and honors a persisted user pause",
        )
        self.assertEqual(len(build_game.triples), 2, "build_from swaps in a new triple")

    def test_failed_continue_valueerror_shows_notice_and_stays_on_title(self):
        spy = _SpyAutosave(peek=True, load_error=ValueError("corrupt save"))
        controller, build_game = self._title(spy)
        _click_center(self, controller, "title_layout", "continue")
        self.assertEqual(controller.state, _screen(self, "TITLE"))
        notice = getattr(controller, "notice", None)
        self.assertIsInstance(notice, str)
        self.assertTrue(notice, "a corrupt save must surface a failure notice")
        self.assertEqual(len(build_game.triples), 1, "a failed load swaps nothing")
        _press(controller, pygame.K_RETURN)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertFalse(
            getattr(controller, "notice", None), "the notice clears on a state change"
        )

    def test_failed_continue_oserror_shows_notice_and_stays_on_title(self):
        spy = _SpyAutosave(peek=True, load_error=FileNotFoundError("missing save"))
        controller, build_game = self._title(spy)
        _click_center(self, controller, "title_layout", "continue")
        self.assertEqual(controller.state, _screen(self, "TITLE"))
        notice = getattr(controller, "notice", None)
        self.assertIsInstance(notice, str)
        self.assertTrue(notice, "an unreadable save must surface a failure notice")
        self.assertEqual(len(build_game.triples), 1)


if __name__ == "__main__":
    unittest.main()

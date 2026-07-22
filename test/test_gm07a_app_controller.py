"""GM-07a red contract: the AppController screen-state machine (D-010)."""

from __future__ import annotations

import contextlib
import importlib
import inspect
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import main
from config import screen_height, screen_width
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from game_session import GameSession
from geometry.point import Point
from mediator import Mediator
from rendering.game_renderer import GameRenderer


def _module_symbol(testcase, module_name, symbol):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        testcase.fail(f"GM-07a product module is missing: {module_name} ({error})")
    value = getattr(module, symbol, None)
    testcase.assertIsNotNone(
        value, f"GM-07a product symbol is missing: {module_name}.{symbol}"
    )
    return value


def _screen(testcase, name):
    states = _module_symbol(testcase, "app_controller", "AppScreen")
    testcase.assertTrue(
        hasattr(states, name), f"GM-07a AppScreen member is missing: {name}"
    )
    return getattr(states, name)


def _controller(testcase, factory, start_state):
    controller_type = _module_symbol(testcase, "app_controller", "AppController")
    return controller_type(factory, start_state=start_state)


def _handle(testcase, controller, event):
    handler = getattr(controller, "handle_event", None)
    testcase.assertIsNotNone(
        handler, "GM-07a product attribute is missing: AppController.handle_event"
    )
    handler(event)


def _layout(testcase, layout_name):
    layout_fn = _module_symbol(testcase, "ui.menu_screens", layout_name)
    return layout_fn(screen_width, screen_height)


def _menu_rect_center(testcase, layout_name, key):
    layout = _layout(testcase, layout_name)
    testcase.assertIn(key, layout, f"{layout_name} must expose the {key!r} rect")
    center = pygame.Rect(layout[key]).center
    return Point(int(center[0]), int(center[1]))


def _assert_probe_clear(testcase, layout_name, probe):
    for key, rect in _layout(testcase, layout_name).items():
        testcase.assertFalse(
            pygame.Rect(rect).collidepoint((probe.left, probe.top)),
            f"the gameplay probe point overlaps the {key!r} control",
        )


def _describe(event):
    position = getattr(event, "position", None)
    if position is not None:
        return (
            type(event).__name__,
            event.event_type,
            (float(position.left), float(position.top)),
        )
    return (type(event).__name__, event.event_type, event.key)


def _press(testcase, controller, key):
    _handle(testcase, controller, KeyboardEvent(KeyboardEventType.KEY_UP, key))


def _click(testcase, controller, target):
    point = Point(target.left, target.top)
    _handle(testcase, controller, MouseEvent(MouseEventType.MOUSE_UP, point))


def _press_and_release(testcase, controller, target):
    """Pause-menu controls arm on press (review F2): send the DOWN+UP pair."""

    point = Point(target.left, target.top)
    _handle(testcase, controller, MouseEvent(MouseEventType.MOUSE_DOWN, point))
    _handle(testcase, controller, MouseEvent(MouseEventType.MOUSE_UP, point))


_CANCEL = ("MouseEvent", MouseEventType.MOUSE_UP, (-1.0, -1.0))
_GAMEPLAY_KINDS = ("dispatch", "react", "set_paused", "is_paused=", "release")


class _RecordingMediator:
    def __init__(self, log, name):
        self.log = log
        self.name = name
        self.is_game_over = False
        self.held = []
        self.game_over_result = None

    @property
    def is_paused(self):
        return bool(self.held)

    @is_paused.setter
    def is_paused(self, value):
        self.log.append((self.name, "is_paused=", value))

    def set_paused(self, paused):
        self.log.append((self.name, "set_paused", paused))

    def hold_pause_reason(self, reason):
        self.log.append((self.name, "hold", reason))
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason):
        self.log.append((self.name, "release", reason))
        if reason in self.held:
            self.held.remove(reason)

    def handle_game_over_click(self, position):
        self.log.append(
            (self.name, "game_over_click", (float(position.left), float(position.top)))
        )
        return self.game_over_result

    def react(self, event):
        self.log.append((self.name, "react", _describe(event)))


class _RecordingSession:
    def __init__(self, log, mediator, name):
        self.log = log
        self.mediator = mediator
        self.name = name

    def dispatch(self, event):
        self.log.append((self.name, "dispatch", _describe(event)))

    def advance(self, elapsed_ms):
        self.log.append((self.name, "advance", elapsed_ms))
        return SimpleNamespace(alpha=1.0)


def _fake_factory(log):
    triples = []

    def build():
        index = len(triples)
        mediator = _RecordingMediator(log, f"mediator-{index}")
        renderer = SimpleNamespace(name=f"renderer-{index}")
        session = _RecordingSession(log, mediator, f"session-{index}")
        triples.append((mediator, renderer, session))
        log.append(("factory", index))
        return mediator, renderer, session

    build.triples = triples
    return build


def _entries(log, start, name, kinds=_GAMEPLAY_KINDS):
    return [entry for entry in log[start:] if entry[0] == name and entry[1] in kinds]


def _kind(log, start, kind):
    return [entry for entry in log[start:] if entry[1] == kind]


def _pause_writes(log, start):
    return [entry for entry in log[start:] if entry[1] in ("set_paused", "is_paused=")]


def _run_game_with_controller_spy(testcase, *, frames_events, call):
    with (
        patch("main.pygame") as pygame_mock,
        patch("main.Mediator"),
        patch("main.GameSession") as session_mock,
        patch("main.GameRenderer"),
        patch("main.AppController", create=True) as controller_mock,
    ):
        pygame_mock.QUIT = 12
        pygame_mock.MOUSEBUTTONDOWN = 13
        pygame_mock.MOUSEBUTTONUP = 14
        pygame_mock.MOUSEMOTION = 15
        window = MagicMock()
        window.get_size.return_value = (screen_width, screen_height)
        pygame_mock.display.set_mode.return_value = window
        game_surface = MagicMock()
        game_surface.get_size.return_value = (screen_width, screen_height)
        pygame_mock.Surface.return_value = game_surface
        clock = MagicMock()
        clock.tick.return_value = 17
        pygame_mock.time.Clock.return_value = clock
        pygame_mock.event.get.side_effect = frames_events
        session_mock.return_value.advance.return_value = SimpleNamespace(alpha=0.0)
        with contextlib.suppress(SystemExit):
            call()
        testcase.assertTrue(
            controller_mock.called,
            "run_game must construct the controller via the main.AppController seam",
        )
        first_call = controller_mock.call_args_list[0]
        return list(first_call.args) + list(first_call.kwargs.values())


class TestGM07aRunGameStartState(unittest.TestCase):
    def test_run_game_auto_starts_playing_when_max_frames_is_set(self):
        playing = _screen(self, "PLAYING")
        arguments = _run_game_with_controller_spy(
            self,
            frames_events=[[], [SimpleNamespace(type=12)]],
            call=lambda: main.run_game(max_frames=1),
        )
        self.assertIn(playing, arguments)

    def test_run_game_starts_at_title_without_max_frames(self):
        title = _screen(self, "TITLE")
        arguments = _run_game_with_controller_spy(
            self,
            frames_events=[[SimpleNamespace(type=12)], [SimpleNamespace(type=12)]],
            call=lambda: main.run_game(),
        )
        self.assertIn(title, arguments)

    def test_run_game_start_state_keyword_overrides_auto_selection(self):
        title = _screen(self, "TITLE")
        playing = _screen(self, "PLAYING")
        if "start_state" not in inspect.signature(main.run_game).parameters:
            self.fail("GM-07a: run_game must accept a start_state keyword override")
        arguments = _run_game_with_controller_spy(
            self,
            frames_events=[[], [SimpleNamespace(type=12)]],
            call=lambda: main.run_game(max_frames=1, start_state=title),
        )
        self.assertIn(title, arguments)
        self.assertNotIn(playing, arguments)


class TestGM07aControllerStateMachine(unittest.TestCase):
    def _build_controller(self, start_name):
        log = []
        build = _fake_factory(log)
        controller = _controller(self, build, _screen(self, start_name))
        return log, build, controller

    def _open_menu(self, controller):
        _press(self, controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PAUSE_MENU"))

    def _menu_click(self, controller, key):
        target = _menu_rect_center(self, "pause_menu_layout", key)
        _press_and_release(self, controller, target)

    def test_screen_states_are_distinct(self):
        names = ("TITLE", "PLAYING", "PAUSE_MENU", "GAME_OVER")
        self.assertEqual(len({_screen(self, name) for name in names}), 4)

    def test_controller_builds_the_triple_eagerly_via_the_supplied_factory(self):
        log, build, controller = self._build_controller("TITLE")
        self.assertEqual(len(build.triples), 1)
        mediator, renderer, session = build.triples[0]
        self.assertIs(controller.mediator, mediator)
        self.assertIs(controller.renderer, renderer)
        self.assertIs(controller.session, session)
        self.assertEqual(controller.state, _screen(self, "TITLE"))

    def test_escape_while_playing_cancels_the_gesture_before_holding_menu(self):
        log, build, controller = self._build_controller("PLAYING")
        self._open_menu(controller)
        cancel = ("session-0", "dispatch", _CANCEL)
        hold = ("mediator-0", "hold", "menu")
        cancels = [index for index, entry in enumerate(log) if entry == cancel]
        holds = [index for index, entry in enumerate(log) if entry == hold]
        self.assertEqual(len(cancels), 1, f"exactly one letterbox cancel: {log}")
        self.assertEqual(len(holds), 1, f"exactly one menu hold: {log}")
        self.assertLess(cancels[0], holds[0], "cancel must precede the menu hold")
        self.assertEqual(build.triples[0][0].held, ["menu"])

    def test_pause_menu_blocks_gameplay_dispatch_and_space_cannot_resume(self):
        log, build, controller = self._build_controller("PLAYING")
        probe = Point(12, 540)
        _assert_probe_clear(self, "pause_menu_layout", probe)
        self._open_menu(controller)
        start = len(log)
        for event in (
            MouseEvent(MouseEventType.MOUSE_DOWN, probe),
            MouseEvent(MouseEventType.MOUSE_MOTION, probe),
            MouseEvent(MouseEventType.MOUSE_UP, probe),
            KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_SPACE),
            KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_1),
        ):
            _handle(self, controller, event)
        self.assertEqual(controller.state, _screen(self, "PAUSE_MENU"))
        self.assertEqual(_entries(log, start, "mediator-0"), [])
        self.assertEqual(_entries(log, start, "session-0"), [])
        self.assertEqual(build.triples[0][0].held, ["menu"])

    def test_menu_resume_by_click_and_by_escape_releases_only_menu(self):
        log, build, controller = self._build_controller("PLAYING")
        menu_release = ("mediator-0", "release", "menu")
        self._open_menu(controller)
        start = len(log)
        self._menu_click(controller, "resume")
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertEqual(_kind(log, start, "release"), [menu_release])
        self.assertEqual(_pause_writes(log, start), [])
        self.assertEqual(_kind(log, start, "dispatch"), [])
        self._open_menu(controller)
        start = len(log)
        _press(self, controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertEqual(_kind(log, start, "release"), [menu_release])
        self.assertEqual(_pause_writes(log, start), [])
        self.assertEqual(build.triples[0][0].held, [])

    def test_menu_restart_reroutes_dispatch_and_draw_to_the_new_triple(self):
        log, build, controller = self._build_controller("PLAYING")
        probe = Point(12, 540)
        _assert_probe_clear(self, "pause_menu_layout", probe)
        self._open_menu(controller)
        self._menu_click(controller, "restart")
        self.assertEqual(len(build.triples), 2, "restart must go through the factory")
        new_mediator, new_renderer, new_session = build.triples[1]
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertIs(controller.mediator, new_mediator)
        self.assertIs(controller.renderer, new_renderer)
        self.assertIs(controller.session, new_session)
        self.assertEqual(new_mediator.held, [], "no inherited menu hold after restart")
        self.assertEqual(_entries(log, 0, "session-1"), [], "restart click leaked")
        start = len(log)
        _handle(self, controller, MouseEvent(MouseEventType.MOUSE_DOWN, probe))
        self.assertEqual(_entries(log, start, "session-0"), [])
        expected = ("MouseEvent", MouseEventType.MOUSE_DOWN, (12.0, 540.0))
        self.assertEqual(
            _kind(log, start, "dispatch"), [("session-1", "dispatch", expected)]
        )

    def test_menu_exit_to_title_then_new_game_reconstructs(self):
        log, build, controller = self._build_controller("PLAYING")
        self._open_menu(controller)
        self._menu_click(controller, "exit_to_title")
        self.assertEqual(controller.state, _screen(self, "TITLE"))
        self.assertEqual(len(build.triples), 1)
        self.assertEqual(build.triples[0][0].held, [], "closing the menu releases it")
        _press(self, controller, pygame.K_RETURN)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertEqual(len(build.triples), 2)
        self.assertIs(controller.session, build.triples[1][2])

    def test_title_new_game_click_and_exit_click_routing(self):
        log, build, controller = self._build_controller("TITLE")
        probe = Point(12, 540)
        _assert_probe_clear(self, "title_layout", probe)
        start = len(log)
        _press(self, controller, pygame.K_SPACE)
        _handle(self, controller, MouseEvent(MouseEventType.MOUSE_DOWN, probe))
        self.assertEqual(_kind(log, start, "dispatch"), [], "gameplay leak on title")
        self.assertEqual(controller.state, _screen(self, "TITLE"))
        _click(self, controller, _menu_rect_center(self, "title_layout", "new_game"))
        self.assertEqual(len(build.triples), 2)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertIs(controller.mediator, build.triples[1][0])
        exit_center = _menu_rect_center(self, "title_layout", "exit")
        _log, _build, exit_controller = self._build_controller("TITLE")
        with self.assertRaises(SystemExit):
            _click(self, exit_controller, exit_center)

    def test_game_over_routes_keys_and_clicks_with_restart_exit_parity(self):
        log, build, controller = self._build_controller("PLAYING")
        mediator = build.triples[0][0]
        mediator.is_game_over = True
        _click(self, controller, Point(320, 200))
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))
        self.assertIn(("mediator-0", "game_over_click", (320.0, 200.0)), log)
        self.assertEqual(_kind(log, 0, "dispatch"), [], "no dispatch at game over")
        mediator.game_over_result = "restart"
        _click(self, controller, Point(320, 200))
        self.assertEqual(len(build.triples), 2)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        self.assertIs(controller.mediator, build.triples[1][0])
        _log_r, build_r, controller_r = self._build_controller("PLAYING")
        build_r.triples[0][0].is_game_over = True
        _press(self, controller_r, pygame.K_r)
        self.assertEqual(len(build_r.triples), 2)
        self.assertEqual(controller_r.state, _screen(self, "PLAYING"))
        self.assertIs(controller_r.session, build_r.triples[1][2])
        _log_e, build_e, controller_e = self._build_controller("PLAYING")
        build_e.triples[0][0].is_game_over = True
        build_e.triples[0][0].game_over_result = "exit"
        with self.assertRaises(SystemExit):
            _click(self, controller_e, Point(5, 5))
        _log_k, build_k, controller_k = self._build_controller("PLAYING")
        build_k.triples[0][0].is_game_over = True
        with self.assertRaises(SystemExit):
            _press(self, controller_k, pygame.K_ESCAPE)


class TestGM07aMidDragMenuEntry(unittest.TestCase):
    def test_escape_mid_drag_cancels_cleanly_with_zero_release_actions(self):
        playing = _screen(self, "PLAYING")
        pause_menu = _screen(self, "PAUSE_MENU")
        resume = _menu_rect_center(self, "pause_menu_layout", "resume")
        mediator = Mediator(seed=7100)
        path = mediator.create_path_from_station_indices([0, 1])
        self.assertIsNotNone(path)
        renderer = GameRenderer()
        session = GameSession(mediator, step_observer=renderer)

        def build():
            return mediator, renderer, session

        controller = _controller(self, build, playing)
        button = mediator.path_to_button[path]
        self.assertIs(mediator.get_containing_entity(button.position), button)
        with (
            patch.object(
                mediator, "replace_path", wraps=mediator.replace_path
            ) as replace,
            patch.object(mediator, "remove_path", wraps=mediator.remove_path) as remove,
            patch.object(
                mediator,
                "try_purchase_path_button",
                wraps=mediator.try_purchase_path_button,
            ) as purchase,
            patch.object(
                mediator, "apply_speed_action", wraps=mediator.apply_speed_action
            ) as speed,
        ):
            down = MouseEvent(MouseEventType.MOUSE_DOWN, button.position)
            _handle(self, controller, down)
            self.assertTrue(mediator.is_mouse_down)
            self.assertIsNotNone(
                mediator.path_redraw, "the redraw gesture must arm through dispatch"
            )
            _press(self, controller, pygame.K_ESCAPE)
            self.assertEqual(controller.state, pause_menu)
            self.assertIs(mediator.is_paused, True)
            self.assertFalse(mediator.is_mouse_down)
            self.assertIsNone(
                mediator.path_redraw, "opening the menu must abandon the drag first"
            )
            _click(self, controller, resume)  # the drag's own release: unarmed no-op
            self.assertEqual(controller.state, pause_menu)
            self.assertIs(mediator.is_paused, True)
            _press_and_release(self, controller, resume)
        self.assertEqual(controller.state, playing)
        self.assertIs(mediator.is_paused, False)
        self.assertFalse(mediator.is_mouse_down)
        self.assertIsNone(mediator.path_redraw)
        self.assertIsNone(mediator.path_edit_selection)
        self.assertIn(path, mediator.paths)
        replace.assert_not_called()
        remove.assert_not_called()
        purchase.assert_not_called()
        speed.assert_not_called()


if __name__ == "__main__":
    unittest.main()

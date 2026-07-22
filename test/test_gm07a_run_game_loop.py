"""GM-07a implementation-review F1: pin run_game's new frame-composition branches.

These tests drive ``main.run_game`` with the real ``AppController`` (never
mocked) and recording fakes behind the ``main.Mediator`` / ``main.GameSession``
/ ``main.GameRenderer`` factory seam, mocking only the display per
``test_main.py`` idioms. Each event pump emits a frame marker, so the tests pin
the exact ``advance`` argument and draw selection of every frame: TITLE frames
advance by 0 and draw only title chrome; the frame that swaps the triple
(pause-menu Restart) routes dispatch, ``advance(0)``, and the draw to the new
session and renderer; pause-menu frames keep advancing the held session with
the real elapsed value (the menu pause reason is what freezes it) and
composite gameplay first, menu chrome second.
"""

from __future__ import annotations

import itertools
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import main
from app_controller import AppScreen
from config import screen_height, screen_width
from event.type import MouseEventType
from ui.menu_screens import pause_menu_layout

_ELAPSED_MS = 17


def _menu_center(key: str) -> tuple[int, int]:
    rect = pause_menu_layout(screen_width, screen_height)[key]
    return (int(rect.centerx), int(rect.centery))


def _key_up(key: int) -> SimpleNamespace:
    return SimpleNamespace(type=pygame.KEYUP, key=key)


def _mouse(event_type: int, position: tuple[int, int]) -> SimpleNamespace:
    return SimpleNamespace(type=event_type, pos=position, button=1)


def _describe(event: object):
    position = getattr(event, "position", None)
    if position is not None:
        return (
            type(event).__name__,
            event.event_type,
            (float(position.left), float(position.top)),
        )
    return (type(event).__name__, event.event_type, event.key)


class _RecordingMediator:
    def __init__(self, log: list, name: str) -> None:
        self.log = log
        self.name = name
        self.is_game_over = False
        self.held: list[str] = []

    def hold_pause_reason(self, reason: str) -> None:
        self.log.append((self.name, "hold", reason))
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason: str) -> None:
        self.log.append((self.name, "release", reason))
        if reason in self.held:
            self.held.remove(reason)


class _RecordingRenderer:
    def __init__(self, log: list, name: str) -> None:
        self.log = log
        self.name = name

    def draw(self, surface: object, mediator: _RecordingMediator, alpha: float) -> None:
        self.log.append((self.name, "draw", mediator.name, alpha))


class _RecordingSession:
    def __init__(
        self,
        log: list,
        mediator: _RecordingMediator,
        name: str,
        alpha: float,
        step_observer: object,
    ) -> None:
        self.log = log
        self.mediator = mediator
        self.name = name
        self.alpha = alpha
        self.step_observer = step_observer

    def prepare_layout(self, surface: object) -> None:
        self.log.append((self.name, "prepare_layout"))

    def dispatch(self, event: object) -> None:
        self.log.append((self.name, "dispatch", _describe(event)))

    def advance(self, elapsed_ms: int) -> SimpleNamespace:
        self.log.append((self.name, "advance", elapsed_ms))
        return SimpleNamespace(alpha=self.alpha)


def _run_loop(frames_events, **run_kwargs):
    """Run ``main.run_game`` over exactly ``len(frames_events)`` pumped frames.

    Returns ``(log, harness)``: the single ordered cross-object log (with a
    ``("frame", n)`` marker per event pump) and the recorded triples in
    construction order. Each session advances to a distinct alpha
    (``0.125 * (index + 1)``) so a draw pins which session's advance fed it.
    """

    log: list = []
    mediators: list[_RecordingMediator] = []
    renderers: list[_RecordingRenderer] = []
    sessions: list[_RecordingSession] = []

    def build_mediator() -> _RecordingMediator:
        mediator = _RecordingMediator(log, f"mediator-{len(mediators)}")
        mediators.append(mediator)
        return mediator

    def build_renderer() -> _RecordingRenderer:
        renderer = _RecordingRenderer(log, f"renderer-{len(renderers)}")
        renderers.append(renderer)
        return renderer

    def build_session(mediator: _RecordingMediator, **kwargs) -> _RecordingSession:
        index = len(sessions)
        session = _RecordingSession(
            log,
            mediator,
            f"session-{index}",
            alpha=0.125 * (index + 1),
            step_observer=kwargs.get("step_observer"),
        )
        sessions.append(session)
        return session

    batches = iter(frames_events)
    frame_counter = itertools.count()

    def pump() -> list:
        log.append(("frame", next(frame_counter)))
        return next(batches)

    with (
        patch("main.pygame") as pygame_mock,
        patch("main.Mediator", side_effect=build_mediator),
        patch("main.GameSession", side_effect=build_session),
        patch("main.GameRenderer", side_effect=build_renderer),
        patch(
            "main.draw_title_screen",
            side_effect=lambda surface: log.append(("chrome", "title")),
        ),
        patch(
            "main.draw_pause_menu",
            side_effect=lambda surface: log.append(("chrome", "pause_menu")),
        ),
    ):
        pygame_mock.QUIT = pygame.QUIT
        pygame_mock.MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
        pygame_mock.MOUSEBUTTONUP = pygame.MOUSEBUTTONUP
        pygame_mock.MOUSEMOTION = pygame.MOUSEMOTION
        window = MagicMock()
        window.get_size.return_value = (screen_width, screen_height)
        pygame_mock.display.set_mode.return_value = window
        game_surface = MagicMock()
        game_surface.get_size.return_value = (screen_width, screen_height)
        pygame_mock.Surface.return_value = game_surface
        clock = MagicMock()
        clock.tick.return_value = _ELAPSED_MS
        pygame_mock.time.Clock.return_value = clock
        pygame_mock.event.get.side_effect = pump
        main.run_game(**run_kwargs)
    return log, SimpleNamespace(
        mediators=mediators, renderers=renderers, sessions=sessions
    )


def _frames(log: list) -> list[list]:
    """Split the log into per-frame slices at the pump markers."""

    frames: list[list] = []
    current: list | None = None
    for entry in log:
        if entry[0] == "frame":
            current = []
            frames.append(current)
        elif current is not None:
            current.append(entry)
    return frames


def _advances(entries: list) -> list:
    return [entry for entry in entries if entry[1] == "advance"]


def _dispatches(entries: list) -> list:
    return [entry for entry in entries if entry[1] == "dispatch"]


def _draw_calls(entries: list) -> list:
    """Renderer draws and chrome draws, preserving their frame order."""

    return [entry for entry in entries if entry[1] == "draw" or entry[0] == "chrome"]


class TestGM07aRunGameLoopFrames(unittest.TestCase):
    def test_title_frames_advance_zero_and_draw_only_title_chrome(self):
        log, harness = _run_loop([[], []], max_frames=2, start_state=AppScreen.TITLE)
        frames = _frames(log)
        self.assertEqual(len(frames), 2)
        for index, frame in enumerate(frames):
            with self.subTest(frame=index):
                self.assertEqual(
                    _advances(frame),
                    [("session-0", "advance", 0)],
                    "a TITLE frame must advance by 0 even though the clock "
                    f"ticked {_ELAPSED_MS} ms",
                )
                self.assertEqual(_draw_calls(frame), [("chrome", "title")])
                self.assertEqual(_dispatches(frame), [])
        self.assertEqual(len(harness.sessions), 1)
        self.assertEqual(harness.mediators[0].held, [])

    def test_menu_restart_frame_routes_dispatch_advance_and_draw_to_new_triple(self):
        restart = _menu_center("restart")
        log, harness = _run_loop(
            [
                [_key_up(pygame.K_ESCAPE)],
                [
                    _mouse(pygame.MOUSEBUTTONDOWN, restart),
                    _mouse(pygame.MOUSEBUTTONUP, restart),
                    _mouse(pygame.MOUSEMOTION, (444, 555)),
                ],
            ],
            max_frames=2,
            start_state=AppScreen.PLAYING,
        )
        menu_frame, swap_frame = _frames(log)
        self.assertEqual(
            _dispatches(menu_frame),
            [
                (
                    "session-0",
                    "dispatch",
                    ("MouseEvent", MouseEventType.MOUSE_UP, (-1.0, -1.0)),
                )
            ],
            "opening the menu dispatches only the pinned letterbox cancel",
        )
        self.assertEqual(_advances(menu_frame), [("session-0", "advance", _ELAPSED_MS)])
        self.assertEqual(
            _draw_calls(menu_frame),
            [("renderer-0", "draw", "mediator-0", 0.125), ("chrome", "pause_menu")],
        )
        # The Restart frame: the same frame that rebuilds the triple must
        # route dispatch, advance(0), and the draw to the new session/renderer.
        self.assertIn(("session-1", "prepare_layout"), swap_frame)
        self.assertEqual(_advances(swap_frame), [("session-1", "advance", 0)])
        self.assertEqual(
            _dispatches(swap_frame),
            [
                (
                    "session-1",
                    "dispatch",
                    ("MouseEvent", MouseEventType.MOUSE_MOTION, (444.0, 555.0)),
                )
            ],
            "a trailing same-frame gameplay event must reach the new session "
            "and the swallowed menu DOWN/UP must reach neither session",
        )
        self.assertEqual(
            _draw_calls(swap_frame),
            [("renderer-1", "draw", "mediator-1", 0.25)],
            "the swap frame draws the new renderer with the new mediator and "
            "the new session's advance alpha, without menu chrome",
        )
        self.assertEqual(
            [entry for entry in swap_frame if entry[0] in ("session-0", "renderer-0")],
            [],
            "the old session and renderer must be idle on the swap frame",
        )
        self.assertIn(("mediator-0", "release", "menu"), swap_frame)
        self.assertEqual(harness.mediators[0].held, [])
        self.assertEqual(harness.mediators[1].held, [])
        self.assertIs(
            harness.sessions[1].step_observer,
            harness.renderers[1],
            "the rebuilt session must observe the renderer drawn this frame",
        )

    def test_pause_menu_frames_advance_real_elapsed_under_menu_hold_and_composite(
        self,
    ):
        log, harness = _run_loop(
            [[_key_up(pygame.K_ESCAPE)], [], []],
            max_frames=3,
            start_state=AppScreen.PLAYING,
        )
        frames = _frames(log)
        self.assertEqual(len(frames), 3)
        for index, frame in enumerate(frames):
            with self.subTest(frame=index):
                self.assertEqual(
                    _advances(frame),
                    [("session-0", "advance", _ELAPSED_MS)],
                    "menu frames keep passing the real elapsed value; the "
                    "held menu pause reason is what freezes the real session",
                )
                self.assertEqual(
                    _draw_calls(frame),
                    [
                        ("renderer-0", "draw", "mediator-0", 0.125),
                        ("chrome", "pause_menu"),
                    ],
                    "each menu frame draws gameplay first, menu chrome second",
                )
        self.assertNotIn(("chrome", "title"), log)
        self.assertEqual(len(harness.sessions), 1, "no reconstruction on menu frames")
        self.assertEqual(
            harness.mediators[0].held,
            ["menu"],
            "the controller-owned menu reason stays held through menu frames",
        )


if __name__ == "__main__":
    unittest.main()

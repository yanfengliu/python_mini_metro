"""GM-07c red contract: the window-close autosave gate in ``main.run_game``.

Drives the real ``main.run_game`` with recording fakes behind the
``main.Mediator``/``main.GameSession``/``main.GameRenderer`` seams (mirroring
``test_gm07a_run_game_loop``) and patches the module-level autosave path seam
so the suite can NEVER read, write, or delete a developer's real
``saves/autosave.json``. Pins the F1 gate: a ``pygame.QUIT`` saves when the
controller is in ``PAUSE_MENU`` or un-over ``PLAYING``, deletes when the
mediator is game over, does neither on ``TITLE``, and a save that raises still
exits (the mid-drag quiescence failure is swallowed).

Every autosave seam patch uses ``create=True`` so that, at baseline where the
product symbols do not yet exist, the assertions FAIL cleanly instead of
erroring.
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import main
from app_controller import AppScreen
from config import screen_height, screen_width


class _LoopMediator:
    def __init__(self, game_over: bool) -> None:
        self.is_game_over = game_over
        self.held: list[str] = []

    def hold_pause_reason(self, reason: str) -> None:
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason: str) -> None:
        if reason in self.held:
            self.held.remove(reason)


class _LoopSession:
    def __init__(self, mediator: _LoopMediator) -> None:
        self.mediator = mediator

    def prepare_layout(self, surface: object) -> None:
        pass

    def dispatch(self, event: object) -> None:
        pass

    def advance(self, elapsed_ms: int) -> SimpleNamespace:
        return SimpleNamespace(alpha=0.0)


class _LoopRenderer:
    def draw(self, surface: object, mediator: object, alpha: float) -> None:
        pass


def _drive_window_close(
    testcase,
    *,
    start_state: AppScreen,
    game_over: bool,
    write_spy: MagicMock | None,
    delete_spy: MagicMock | None,
    extra_patches=(),
):
    """Pump exactly one ``pygame.QUIT`` and assert it exits via ``SystemExit``.

    Returns the single built ``_LoopMediator`` so a caller can assert the exact
    mediator handed to the autosave seam.
    """

    mediators: list[_LoopMediator] = []

    def build_mediator() -> _LoopMediator:
        mediator = _LoopMediator(game_over)
        mediators.append(mediator)
        return mediator

    quit_event = SimpleNamespace(type=pygame.QUIT)
    with contextlib.ExitStack() as stack:
        pygame_mock = stack.enter_context(patch("main.pygame"))
        stack.enter_context(patch("main.Mediator", side_effect=build_mediator))
        stack.enter_context(
            patch("main.GameSession", side_effect=lambda m, **k: _LoopSession(m))
        )
        stack.enter_context(patch("main.GameRenderer", side_effect=_LoopRenderer))
        if write_spy is not None:
            stack.enter_context(patch("main.write_autosave", write_spy, create=True))
        if delete_spy is not None:
            stack.enter_context(patch("main.delete_autosave", delete_spy, create=True))
        for extra in extra_patches:
            stack.enter_context(extra)
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
        clock.tick.return_value = 17
        pygame_mock.time.Clock.return_value = clock
        pygame_mock.event.get.side_effect = [[quit_event]]
        with testcase.assertRaises(SystemExit):
            main.run_game(start_state=start_state)
    testcase.assertEqual(len(mediators), 1, "run_game builds exactly one game triple")
    return mediators[0]


class TestGM07cWindowCloseAutosaveGate(unittest.TestCase):
    def test_quit_in_pause_menu_saves_before_exit(self):
        write_spy = MagicMock()
        delete_spy = MagicMock()
        mediator = _drive_window_close(
            self,
            start_state=AppScreen.PAUSE_MENU,
            game_over=False,
            write_spy=write_spy,
            delete_spy=delete_spy,
        )
        write_spy.assert_called_once_with(mediator)
        delete_spy.assert_not_called()

    def test_quit_in_unover_playing_saves_before_exit(self):
        write_spy = MagicMock()
        delete_spy = MagicMock()
        mediator = _drive_window_close(
            self,
            start_state=AppScreen.PLAYING,
            game_over=False,
            write_spy=write_spy,
            delete_spy=delete_spy,
        )
        write_spy.assert_called_once_with(mediator)
        delete_spy.assert_not_called()

    def test_quit_when_game_over_deletes_and_never_saves(self):
        write_spy = MagicMock()
        delete_spy = MagicMock()
        _drive_window_close(
            self,
            start_state=AppScreen.PLAYING,
            game_over=True,
            write_spy=write_spy,
            delete_spy=delete_spy,
        )
        delete_spy.assert_called_once_with()
        write_spy.assert_not_called()

    def test_quit_on_title_neither_saves_nor_deletes(self):
        # regression guard: green at baseline
        write_spy = MagicMock()
        delete_spy = MagicMock()
        _drive_window_close(
            self,
            start_state=AppScreen.TITLE,
            game_over=False,
            write_spy=write_spy,
            delete_spy=delete_spy,
        )
        write_spy.assert_not_called()
        delete_spy.assert_not_called()

    def test_unsaveable_quit_still_exits_and_touches_no_real_file(self):
        # A mid-drag window close makes the boundary save raise ValueError; the
        # gate must swallow it, still exit, and leave no file behind.
        delete_spy = MagicMock()
        save_game_spy = MagicMock(side_effect=ValueError("mid-drag boundary"))
        with tempfile.TemporaryDirectory() as directory:
            autosave_path = Path(directory) / "autosave.json"
            _drive_window_close(
                self,
                start_state=AppScreen.PLAYING,
                game_over=False,
                write_spy=None,  # exercise the REAL write_autosave swallow
                delete_spy=delete_spy,
                extra_patches=[
                    patch("main.save_game", save_game_spy, create=True),
                    patch("main.AUTOSAVE_PATH", autosave_path, create=True),
                ],
            )
            save_game_spy.assert_called_once()
            self.assertFalse(
                autosave_path.exists(), "a failed boundary save must write nothing"
            )
        delete_spy.assert_not_called()


if __name__ == "__main__":
    unittest.main()

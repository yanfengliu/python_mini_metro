"""GM-07d red contract: the window-close high-score record in ``main.run_game``.

Drives the real ``main.run_game`` with recording fakes behind the
``main.Mediator``/``main.GameSession``/``main.GameRenderer`` seams (mirroring
``test_gm07c_run_game_loop``) and patches the module-level highscores path/record
seams so the suite can NEVER read or write a developer's real
``saves/highscores.json``. Pins the D-028 gate: a ``pygame.QUIT`` records once
when the mediator is game over and the controller is still in ``PLAYING`` or
``PAUSE_MENU`` (the frame-accurate race), records nothing on ``TITLE``,
un-over ``PLAYING``, or an already-promoted ``GAME_OVER`` (mutually exclusive
with the promotion path), and ``record_highscore`` swallows even a
``RecursionError`` without crashing while ``SystemExit`` still propagates.

Every highscores seam patch uses ``create=True`` so that, at baseline where the
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
        self.deliveries = 11
        # GM-09f2: the recorder reads the live map identity off the mediator; a real
        # Mediator always has map_definition (default CLASSIC). classic@1 here.
        self.map_definition = SimpleNamespace(
            map_id="classic", map_definition_version=1
        )
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
    record_spy: MagicMock | None = None,
    highscores_path: Path | None = None,
    extra_patches=(),
):
    """Pump exactly one ``pygame.QUIT`` and assert it exits via ``SystemExit``.

    Autosave seams are always neutralized so no real ``saves/autosave.json`` is
    touched; ``main.HIGHSCORES_PATH`` is redirected to the caller's path or a
    fresh temp dir. Returns the single built ``_LoopMediator``.
    """

    mediators: list[_LoopMediator] = []

    def build_mediator() -> _LoopMediator:
        mediator = _LoopMediator(game_over)
        mediators.append(mediator)
        return mediator

    quit_event = SimpleNamespace(type=pygame.QUIT)
    with contextlib.ExitStack() as stack:
        directory = stack.enter_context(tempfile.TemporaryDirectory())
        target = highscores_path or Path(directory) / "highscores.json"
        pygame_mock = stack.enter_context(patch("main.pygame"))
        stack.enter_context(patch("main.Mediator", side_effect=build_mediator))
        stack.enter_context(
            patch("main.GameSession", side_effect=lambda m, **k: _LoopSession(m))
        )
        stack.enter_context(patch("main.GameRenderer", side_effect=_LoopRenderer))
        stack.enter_context(patch("main.write_autosave", MagicMock()))
        stack.enter_context(patch("main.delete_autosave", MagicMock()))
        stack.enter_context(patch("main.HIGHSCORES_PATH", target, create=True))
        if record_spy is not None:
            stack.enter_context(patch("main.record_highscore", record_spy, create=True))
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


class TestGM07dWindowCloseRecordGate(unittest.TestCase):
    def test_quit_when_game_over_in_playing_records_once(self):
        record_spy = MagicMock()
        mediator = _drive_window_close(
            self,
            start_state=AppScreen.PLAYING,
            game_over=True,
            record_spy=record_spy,
        )
        record_spy.assert_called_once_with(mediator)

    def test_quit_when_game_over_in_pause_menu_records_once(self):
        record_spy = MagicMock()
        mediator = _drive_window_close(
            self,
            start_state=AppScreen.PAUSE_MENU,
            game_over=True,
            record_spy=record_spy,
        )
        record_spy.assert_called_once_with(mediator)

    def test_quit_in_unover_playing_does_not_record(self):
        # regression guard: green at baseline
        record_spy = MagicMock()
        _drive_window_close(
            self,
            start_state=AppScreen.PLAYING,
            game_over=False,
            record_spy=record_spy,
        )
        record_spy.assert_not_called()

    def test_quit_on_title_does_not_record(self):
        # regression guard: green at baseline
        record_spy = MagicMock()
        _drive_window_close(
            self,
            start_state=AppScreen.TITLE,
            game_over=False,
            record_spy=record_spy,
        )
        record_spy.assert_not_called()

    def test_quit_when_already_promoted_does_not_double_record(self):
        # regression guard: green at baseline -- a promotion-then-quit records
        # only through the controller seam; the window-close surface is skipped.
        record_spy = MagicMock()
        _drive_window_close(
            self,
            start_state=AppScreen.GAME_OVER,
            game_over=True,
            record_spy=record_spy,
        )
        record_spy.assert_not_called()


class TestGM07dRecordHighscoreSwallowsFailures(unittest.TestCase):
    def test_recursionerror_in_record_is_swallowed_and_exit_still_propagates(self):
        # The real record_highscore must swallow any Exception (RecursionError
        # is neither ValueError nor OSError -- MAJOR-2), so the deep-nested
        # leaderboard case never crashes the exit path.
        load_spy = MagicMock(side_effect=RecursionError("deep leaderboard"))
        with tempfile.TemporaryDirectory() as directory:
            hs_path = Path(directory) / "highscores.json"
            _drive_window_close(
                self,
                start_state=AppScreen.PLAYING,
                game_over=True,
                record_spy=None,  # exercise the REAL main.record_highscore swallow
                highscores_path=hs_path,
                extra_patches=[patch("main.load_highscores", load_spy, create=True)],
            )
            load_spy.assert_called_once()
            self.assertFalse(hs_path.exists(), "a swallowed record must write nothing")


class TestGM07dRecordHighscoreIsReadOnly(unittest.TestCase):
    def test_record_highscore_reads_deliveries_and_map_and_mutates_no_mediator_state(
        self,
    ):
        # PLAN.md / codex MINOR-5a: the single recorder both game-over surfaces call
        # READS the objective AND the live map identity (GM-09f2) off the mediator
        # and mutates nothing, so the checkpoint it never touches stays identical.
        mediator = SimpleNamespace(
            deliveries=7,
            map_definition=SimpleNamespace(map_id="classic", map_definition_version=1),
        )
        before = dict(mediator.__dict__)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            with patch("main.HIGHSCORES_PATH", target, create=True):
                result = main.record_highscore(mediator)
                self.assertTrue(target.exists(), "a first best writes the board")
            entry = result.document["entries"][0]
            self.assertEqual(
                entry["deliveries"],
                7,
                "the recorded deliveries are read off the mediator",
            )
            self.assertEqual(
                entry["map"], "classic", "the recorded map id is read off the mediator"
            )
            self.assertEqual(
                entry["mapDefinitionVersion"],
                1,
                "the recorded map version is read off the mediator",
            )
        self.assertEqual(
            mediator.__dict__, before, "the recorder must not mutate the mediator"
        )

    def test_record_highscore_swallows_a_mediator_without_map_definition(self):
        # GM-09f2 fail-safe: an exotic mediator lacking map_definition records
        # NOTHING (swallowed to None) rather than mislabelling a score.
        mediator = SimpleNamespace(deliveries=7)  # no map_definition
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            with patch("main.HIGHSCORES_PATH", target, create=True):
                result = main.record_highscore(mediator)
            self.assertIsNone(result, "a missing map_definition records nothing")
            self.assertFalse(target.exists(), "a swallowed record writes no board")


if __name__ == "__main__":
    unittest.main()

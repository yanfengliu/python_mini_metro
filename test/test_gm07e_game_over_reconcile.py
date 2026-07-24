"""GM-07e red contract: deterministic per-frame game-over reconciliation.

Follow-up to the GM-07d external Codex persistence review, which flagged (twice,
MAJOR) that an eventless ``PLAYING``->``GAME_OVER`` transition records nothing
and shows no best indicator until the next incidental event or the window-close
QUIT: ``main.run_game`` drains events, then advances, with no post-advance
reconciliation, so a tick that flips ``mediator.is_game_over`` leaves the
controller in ``PLAYING`` until something else happens.

These tests pin the fix. ``AppController`` exposes an idempotent
``reconcile_game_over()`` that runs the exact D-027/D-028 promotion block --
delete the autosave, record the score, store the result -- but only when the
controller is in ``PLAYING`` and the mediator is game over; ``handle_event``
calls it at the top (preserving the historical inline promotion), and
``main.run_game`` calls it once per frame after ``session.advance`` so the
promotion is frame-accurate and independent of any incidental event, while
staying mutually exclusive with the window-close QUIT record (no double record).

The controller cases turn an absent ``reconcile_game_over`` into a clean FAILURE
(not an ERROR) via a ``hasattr`` guard, mirroring the GM-07c/GM-07d controller
suites; the run-loop cases fail on their assertions at baseline.
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
from app_controller import AppController, AppScreen
from config import screen_height, screen_width
from event.keyboard import KeyboardEvent
from event.type import KeyboardEventType


class _RecordingMediator:
    """GM-07c mediator shape: no ``deliveries`` attribute exists."""

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


class _DeliveringMediator(_RecordingMediator):
    """Also exposes the lifetime ``deliveries`` objective (D-028)."""

    def __init__(self, name, deliveries):
        super().__init__(name)
        self.deliveries = deliveries


class _RecordingSession:
    def __init__(self, mediator, name):
        self.mediator = mediator
        self.name = name
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class _SpyHighscores:
    def __init__(self, results=()):
        self.deliveries_seen = []
        self._results = list(results)

    def record(self, mediator):
        # GM-09f2: the seam now receives the live mediator; the recorder derives the
        # deliveries objective (and the map identity) from it, so the spy records
        # mediator.deliveries to keep pinning the recorded objective.
        self.deliveries_seen.append(mediator.deliveries)
        if self._results:
            return self._results.pop(0)
        return None


class _SpyAutosave:
    def __init__(self):
        self.calls = []

    def save(self, mediator):
        self.calls.append(("save", mediator))

    def delete(self):
        self.calls.append(("delete",))

    def peek(self):
        self.calls.append(("peek",))
        return False

    def load(self):
        self.calls.append(("load",))
        return None

    def deletes(self):
        return [call for call in self.calls if call[0] == "delete"]

    def saves(self):
        return [call for call in self.calls if call[0] == "save"]


def _factories(mediator_factory):
    triples = []

    def _wrap(mediator):
        index = len(triples)
        renderer = SimpleNamespace(name=f"renderer-{index}")
        session = _RecordingSession(mediator, f"session-{index}")
        triples.append((mediator, renderer, session))
        return mediator, renderer, session

    def build_game():
        return _wrap(mediator_factory(len(triples)))

    def build_from(loaded):
        return _wrap(loaded)

    build_game.triples = triples
    return build_game, build_from


def _controller(*, start_state, mediator_factory, autosave=None, highscores=None):
    build_game, build_from = _factories(mediator_factory)
    return AppController(
        build_game,
        start_state=start_state,
        build_from=build_from,
        autosave=autosave,
        highscores=highscores,
    )


def _require_reconcile(testcase, controller):
    testcase.assertTrue(
        hasattr(controller, "reconcile_game_over"),
        "GM-07e: AppController must expose an idempotent reconcile_game_over()",
    )
    return controller.reconcile_game_over


class TestGM07eReconcileGameOverController(unittest.TestCase):
    def test_reconcile_promotes_eventlessly_records_and_deletes(self):
        result = SimpleNamespace(rank=1, is_best=True, document={})
        spy = _SpyHighscores(results=[result])
        autosave = _SpyAutosave()
        controller = _controller(
            start_state=AppScreen.PLAYING,
            mediator_factory=lambda index: _DeliveringMediator(f"m{index}", 42),
            autosave=autosave,
            highscores=spy,
        )
        controller.mediator.is_game_over = True
        reconcile = _require_reconcile(self, controller)
        # No event is dispatched: the tick-driven game over reconciles on its own.
        reconcile()
        self.assertEqual(controller.state, AppScreen.GAME_OVER)
        self.assertEqual(
            spy.deliveries_seen, [42], "the eventless promotion records deliveries once"
        )
        self.assertIs(controller.last_highscore_result, result)
        self.assertEqual(
            len(autosave.deletes()), 1, "the finished run's autosave is dropped"
        )
        self.assertEqual(autosave.saves(), [], "reconciliation never saves")

    def test_reconcile_is_idempotent(self):
        spy = _SpyHighscores(results=[SimpleNamespace(rank=1, is_best=True)])
        autosave = _SpyAutosave()
        controller = _controller(
            start_state=AppScreen.PLAYING,
            mediator_factory=lambda index: _DeliveringMediator(f"m{index}", 7),
            autosave=autosave,
            highscores=spy,
        )
        controller.mediator.is_game_over = True
        reconcile = _require_reconcile(self, controller)
        reconcile()
        reconcile()
        reconcile()
        self.assertEqual(controller.state, AppScreen.GAME_OVER)
        self.assertEqual(spy.deliveries_seen, [7], "idempotent: records exactly once")
        self.assertEqual(len(autosave.deletes()), 1, "idempotent: deletes exactly once")

    def test_reconcile_noop_when_not_game_over(self):
        spy = _SpyHighscores()
        autosave = _SpyAutosave()
        controller = _controller(
            start_state=AppScreen.PLAYING,
            mediator_factory=lambda index: _DeliveringMediator(f"m{index}", 3),
            autosave=autosave,
            highscores=spy,
        )
        reconcile = _require_reconcile(self, controller)
        reconcile()
        self.assertEqual(controller.state, AppScreen.PLAYING)
        self.assertEqual(spy.deliveries_seen, [], "an un-over run records nothing")
        self.assertEqual(autosave.deletes(), [], "an un-over run keeps its autosave")

    def test_reconcile_noop_unless_playing(self):
        for state in (AppScreen.TITLE, AppScreen.PAUSE_MENU, AppScreen.GAME_OVER):
            with self.subTest(state=state):
                spy = _SpyHighscores()
                autosave = _SpyAutosave()
                controller = _controller(
                    start_state=state,
                    mediator_factory=lambda index: _DeliveringMediator(f"m{index}", 9),
                    autosave=autosave,
                    highscores=spy,
                )
                controller.mediator.is_game_over = True
                reconcile = _require_reconcile(self, controller)
                reconcile()
                self.assertEqual(controller.state, state, "only PLAYING promotes")
                self.assertEqual(spy.deliveries_seen, [])
                self.assertEqual(autosave.deletes(), [])

    def test_seamless_reconcile_reads_no_deliveries_and_mints_no_best(self):
        # regression guard: green once reconcile exists -- a seam-less controller
        # must promote without touching the absent ``deliveries`` (D-028/MAJOR-3).
        build_game, _build_from = _factories(
            lambda index: _RecordingMediator(f"m{index}")
        )
        controller = AppController(build_game, start_state=AppScreen.PLAYING)
        controller.mediator.is_game_over = True
        reconcile = _require_reconcile(self, controller)
        reconcile()
        self.assertEqual(controller.state, AppScreen.GAME_OVER)
        self.assertIsNone(controller.last_highscore_result)

    def test_handle_event_promotion_still_records_via_reconcile(self):
        # The at-top-of-handle_event reconcile preserves the historical inline
        # promotion: an event on a game-over PLAYING controller still promotes,
        # records once, and drops the autosave.
        spy = _SpyHighscores(results=[SimpleNamespace(rank=1, is_best=True)])
        autosave = _SpyAutosave()
        controller = _controller(
            start_state=AppScreen.PLAYING,
            mediator_factory=lambda index: _DeliveringMediator(f"m{index}", 5),
            autosave=autosave,
            highscores=spy,
        )
        controller.mediator.is_game_over = True
        controller.handle_event(KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_SPACE))
        self.assertEqual(controller.state, AppScreen.GAME_OVER)
        self.assertEqual(spy.deliveries_seen, [5], "the event promotion records once")
        self.assertEqual(len(autosave.deletes()), 1)


class _LoopMediator:
    def __init__(self):
        self.is_game_over = False
        self.deliveries = 11
        self.held = []

    def hold_pause_reason(self, reason):
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason):
        if reason in self.held:
            self.held.remove(reason)


class _FlipSession:
    """A session whose first ``advance`` flips its mediator to game over."""

    def __init__(self, mediator):
        self.mediator = mediator
        self.advances = 0

    def prepare_layout(self, surface):
        pass

    def dispatch(self, event):
        pass

    def advance(self, elapsed_ms):
        self.advances += 1
        if self.advances == 1:
            self.mediator.is_game_over = True
        return SimpleNamespace(alpha=0.0)


class _LoopRenderer:
    """Logs its game-frame draw so the indicator's paint order can be pinned."""

    def __init__(self, draw_log):
        self._draw_log = draw_log

    def draw(self, surface, mediator, alpha, reduced_motion=False):
        self._draw_log.append("renderer")


def _drive(testcase, frame_batches, *, max_frames=None, record_result=None):
    """Drive ``main.run_game`` over ``frame_batches`` with a game-over-flipping
    session, spying the highscore recorder, best-indicator draw, and autosave
    save/delete, plus a ``draw_log`` recording the game-frame vs best-indicator
    paint order. Autosave/highscore paths are fully neutralized, never touching a
    developer's real ``saves/``.
    """

    mediators: list[_LoopMediator] = []
    draw_log: list[str] = []

    def build_mediator() -> _LoopMediator:
        mediator = _LoopMediator()
        mediators.append(mediator)
        return mediator

    record_spy = MagicMock(return_value=record_result)
    # The indicator draw logs its order relative to the renderer's game frame so
    # a regression that paints the banner BEFORE the frame (overwriting it) is
    # caught, while still recording call args (codex MINOR-4).
    best_spy = MagicMock(side_effect=lambda surface, result: draw_log.append("best"))
    write_spy = MagicMock()
    delete_spy = MagicMock()
    with contextlib.ExitStack() as stack:
        directory = stack.enter_context(tempfile.TemporaryDirectory())
        pygame_mock = stack.enter_context(patch("main.pygame"))
        stack.enter_context(patch("main.Mediator", side_effect=build_mediator))
        stack.enter_context(
            patch("main.GameSession", side_effect=lambda m, **k: _FlipSession(m))
        )
        stack.enter_context(
            patch("main.GameRenderer", side_effect=lambda: _LoopRenderer(draw_log))
        )
        stack.enter_context(patch("main.write_autosave", write_spy))
        stack.enter_context(patch("main.delete_autosave", delete_spy))
        stack.enter_context(
            patch(
                "main.HIGHSCORES_PATH",
                Path(directory) / "highscores.json",
                create=True,
            )
        )
        stack.enter_context(patch("main.record_highscore", record_spy, create=True))
        stack.enter_context(patch("main.draw_best_indicator", best_spy))
        stack.enter_context(patch("main.draw_title_screen", MagicMock()))
        stack.enter_context(patch("main.draw_pause_menu", MagicMock()))
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
        pygame_mock.event.get.side_effect = list(frame_batches)
        if max_frames is not None:
            main.run_game(max_frames=max_frames, start_state=AppScreen.PLAYING)
        else:
            with testcase.assertRaises(SystemExit):
                main.run_game(start_state=AppScreen.PLAYING)
    testcase.assertEqual(len(mediators), 1, "run_game builds exactly one game triple")
    return SimpleNamespace(
        record=record_spy,
        best=best_spy,
        delete=delete_spy,
        write=write_spy,
        draw_log=draw_log,
    )


class TestGM07eRunLoopEventlessReconcile(unittest.TestCase):
    def test_eventless_game_over_records_once_and_draws_indicator(self):
        result = SimpleNamespace(rank=1, is_best=True)
        driver = _drive(self, [[]], max_frames=1, record_result=result)
        self.assertEqual(
            driver.record.call_count, 1, "the tick-driven game over records once"
        )
        recorded_arg = driver.record.call_args.args[0]
        self.assertEqual(
            recorded_arg.deliveries,
            11,
            "the recorder reads the mediator's lifetime deliveries",
        )
        self.assertEqual(
            driver.best.call_count,
            1,
            "the best indicator is drawn the frame the game ends",
        )
        self.assertIs(
            driver.best.call_args.args[1],
            result,
            "the indicator receives the frame's fresh record result",
        )
        self.assertEqual(
            driver.delete.call_count, 1, "the finished run's autosave is dropped"
        )
        self.assertEqual(
            driver.draw_log,
            ["renderer", "best"],
            "the best indicator is painted AFTER the renderer's game-over frame "
            "so the banner is never overwritten (D-028)",
        )

    def test_eventless_game_over_then_quit_records_exactly_once(self):
        # Mutual-exclusion contract: the per-frame reconcile on the eventless
        # game-over frame draws the indicator and records, and the following
        # window-close QUIT -- now seeing GAME_OVER, not PLAYING -- must NOT
        # record, delete, or write again.
        result = SimpleNamespace(rank=1, is_best=True)
        quit_event = SimpleNamespace(type=pygame.QUIT)
        driver = _drive(self, [[], [quit_event]], record_result=result)
        self.assertEqual(
            driver.record.call_count,
            1,
            "exactly one record across the reconcile and the QUIT gate",
        )
        # The RECONCILE recorded, not the QUIT gate. Both surfaces now hand the
        # recorder the live mediator (GM-09f2), so WHICH fired is pinned by the SIDE
        # EFFECT rather than the argument shape: only the per-frame reconcile draws
        # the best indicator (asserted below, best.call_count == 1); the QUIT gate,
        # seeing GAME_OVER, records and draws nothing. At baseline (no per-frame
        # reconcile) the QUIT gate would be the recorder and best would never draw,
        # so this proof still flips there (TQ-1 / codex MINOR-5). The recorded arg
        # is the game's mediator, carrying its lifetime deliveries.
        recorded_arg = driver.record.call_args.args[0]
        self.assertEqual(recorded_arg.deliveries, 11)
        self.assertEqual(
            driver.best.call_count,
            1,
            "the indicator is drawn on the eventless game-over frame",
        )
        self.assertEqual(
            driver.delete.call_count, 1, "the autosave is dropped exactly once"
        )
        self.assertEqual(
            driver.write.call_count,
            0,
            "no autosave is recreated on the post-game-over window close",
        )


if __name__ == "__main__":
    unittest.main()

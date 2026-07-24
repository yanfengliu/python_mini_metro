"""GM-07d red contract: the AppController high-score recorder seam (D-028).

Drives a real ``AppController`` with a spy ``highscores`` seam
(``record(deliveries) -> RecordResult | None``) beside the existing autosave
seam, pinning the folded D-028 policy: at the PLAYING->GAME_OVER promotion the
controller records ``mediator.deliveries`` exactly once and stores the result
in public ``last_highscore_result``; a seam-less controller reads no
``deliveries`` at all (MAJOR-3); every promotion (re)assigns the result so a
restart shows no stale best (MINOR-7); and a controller with neither optional
seam is behaviorally identical to today.

Absent product surfaces become clean FAILUREs (never ERRORs) through the
``require_attribute``/``require-signature`` guards, mirroring
``test_gm07c_autosave_controller``.
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

from event.keyboard import KeyboardEvent
from event.type import KeyboardEventType


def _module(testcase, name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-07d product module is missing: {name} ({error})")


def _symbol(testcase, name, module_name="app_controller"):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-07d product symbol is missing: {module_name}.{name}"
    )
    return value


def _screen(testcase, name):
    states = _symbol(testcase, "AppScreen")
    testcase.assertTrue(hasattr(states, name), f"AppScreen member is missing: {name}")
    return getattr(states, name)


def _require_highscores_signature(testcase):
    controller_type = _symbol(testcase, "AppController")
    parameters = inspect.signature(controller_type).parameters
    testcase.assertIn(
        "highscores",
        parameters,
        "GM-07d: AppController.__init__ must accept an optional 'highscores' seam",
    )
    return controller_type


def _press(controller, key):
    controller.handle_event(KeyboardEvent(KeyboardEventType.KEY_UP, key))


class _RecordingMediator:
    """The GM-07c mediator shape: no ``deliveries`` attribute exists."""

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
    """A mediator that also exposes the lifetime ``deliveries`` objective."""

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


class _SpyHighscores:
    """Records each ``record(mediator)`` and returns preloaded results.

    GM-09f2: the seam receives the live mediator (the recorder derives deliveries
    AND the map identity from it), so the spy records ``mediator.deliveries`` to
    keep pinning the recorded objective.
    """

    def __init__(self, results=()):
        self.deliveries_seen = []
        self.mediators_seen = []  # the RAW seam argument, to pin identity
        self._results = list(results)

    def record(self, mediator):
        self.mediators_seen.append(mediator)
        self.deliveries_seen.append(mediator.deliveries)
        if self._results:
            return self._results.pop(0)
        return None


def _seam_controller(
    testcase, build_game, *, start_state, build_from=None, highscores=None
):
    controller_type = _require_highscores_signature(testcase)
    return controller_type(
        build_game,
        start_state=start_state,
        build_from=build_from,
        highscores=highscores,
    )


class TestGM07dRecorderSeam(unittest.TestCase):
    def test_promotion_records_deliveries_once_and_stores_result(self):
        result = SimpleNamespace(rank=1, is_best=True, document={})
        spy = _SpyHighscores(results=[result])
        build_game, build_from = _factories(
            lambda index: _DeliveringMediator(f"m{index}", 42)
        )
        controller = _seam_controller(
            self,
            build_game,
            start_state=_screen(self, "PLAYING"),
            build_from=build_from,
            highscores=spy,
        )
        controller.mediator.is_game_over = True
        _press(controller, pygame.K_SPACE)
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))
        self.assertEqual(
            spy.deliveries_seen, [42], "the promotion records mediator.deliveries once"
        )
        # The seam must receive the LIVE mediator ITSELF (so the recorder can read
        # its map identity), not a deliveries-only wrapper -- a regression that
        # forwarded SimpleNamespace(deliveries=...) would still match deliveries_seen
        # but drop the map, so pin identity (GM-09f2 review MAJOR).
        self.assertIs(
            spy.mediators_seen[0],
            controller.mediator,
            "the seam receives the live mediator, not a deliveries wrapper",
        )
        self.assertIs(
            controller.last_highscore_result,
            result,
            "the RecordResult is stored on last_highscore_result",
        )

    def test_restart_reassigns_result_and_shows_no_stale_best(self):
        first = SimpleNamespace(rank=1, is_best=True, document={})
        spy = _SpyHighscores(results=[first, None])
        build_game, build_from = _factories(
            lambda index: _DeliveringMediator(f"m{index}", 7)
        )
        controller = _seam_controller(
            self,
            build_game,
            start_state=_screen(self, "PLAYING"),
            build_from=build_from,
            highscores=spy,
        )
        controller.mediator.is_game_over = True
        _press(controller, pygame.K_SPACE)
        self.assertIs(controller.last_highscore_result, first)
        # Restart from the game-over screen, then reach a fresh game over.
        _press(controller, pygame.K_r)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        controller.mediator.is_game_over = True
        _press(controller, pygame.K_SPACE)
        self.assertEqual(spy.deliveries_seen, [7, 7], "each promotion records once")
        self.assertIsNone(
            controller.last_highscore_result,
            "a promotion with no new record clears the previous best",
        )


class TestGM07dRecorderRegressionGuards(unittest.TestCase):
    def test_seamless_promotion_reads_no_deliveries(self):
        # regression guard: green at baseline
        controller_type = _symbol(self, "AppController")
        build_game, _build_from = _factories(
            lambda index: _RecordingMediator(f"m{index}")
        )
        controller = controller_type(build_game, start_state=_screen(self, "PLAYING"))
        controller.mediator.is_game_over = True
        # The seam-less controller must promote without touching the absent
        # ``deliveries`` attribute (MAJOR-3) and never mint a best.
        _press(controller, pygame.K_SPACE)
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))
        self.assertIsNone(getattr(controller, "last_highscore_result", None))

    def test_no_optional_seams_behaves_like_baseline(self):
        # regression guard: green at baseline
        controller_type = _symbol(self, "AppController")
        build_game, _build_from = _factories(
            lambda index: _RecordingMediator(f"m{index}")
        )
        controller = controller_type(build_game, start_state=_screen(self, "PLAYING"))
        _press(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PAUSE_MENU"))
        _press(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PLAYING"))
        controller.mediator.is_game_over = True
        _press(controller, pygame.K_SPACE)
        self.assertEqual(controller.state, _screen(self, "GAME_OVER"))


if __name__ == "__main__":
    unittest.main()

"""GM-10a contract: the simulation calendar + week pause reason (D-041).

A "week" is WEEK_LENGTH_STEPS sim steps. Only the interactive human shell enables
the calendar (Mediator.week_calendar), so RL/headless/tutorial never pause. At a
boundary the mediator holds the "week" pause AFTER the complete tick (so
settlement is never interrupted) and only when not game over; the human shell
promotes it to an OFFER modal (after game-over reconcile, cancelling any gesture)
whose armed Continue resolves it. Nothing about the calendar is persisted in
GM-10a; week_index is derived from steps.
"""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import main
from app_controller import AppController, AppScreen
from config import WEEK_LENGTH_STEPS, screen_height, screen_width
from env import MiniMetroEnv
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.point import Point
from mediator import Mediator
from rl.player_env import PlayerPixelEnv
from save_game import serialize_game
from ui.menu_screens import offer_menu_layout

pygame.init()


def _step_to_boundary(mediator, extra=0):
    ticks = 0
    while mediator.steps < WEEK_LENGTH_STEPS + extra and ticks < WEEK_LENGTH_STEPS * 2:
        mediator.increment_time(17)
        ticks += 1
    return mediator


class TestGM10aCalendarCore(unittest.TestCase):
    def test_calendar_off_by_default_never_pauses(self):
        m = Mediator(seed=0)
        self.assertFalse(m.week_calendar, "the calendar is OFF by default")
        _step_to_boundary(m, extra=100)
        self.assertGreater(m.steps, WEEK_LENGTH_STEPS, "no freeze without the calendar")
        self.assertFalse(m.is_week_boundary_pending)
        self.assertFalse(m.is_paused)

    def test_calendar_on_holds_week_at_the_first_boundary(self):
        m = Mediator(seed=0)
        m.week_calendar = True
        _step_to_boundary(m)
        self.assertTrue(m.is_week_boundary_pending, "the boundary holds the week pause")
        self.assertTrue(m.is_paused)
        self.assertEqual(m.week_index, 1)
        self.assertGreaterEqual(m.steps, WEEK_LENGTH_STEPS)

    def test_freeze_then_resolve_resumes_without_immediate_retrigger(self):
        m = Mediator(seed=0)
        m.week_calendar = True
        _step_to_boundary(m)
        frozen = m.steps
        for _ in range(30):
            m.increment_time(17)
        self.assertEqual(m.steps, frozen, "a pending week freezes the sim")
        m.resolve_week_boundary()
        self.assertFalse(m.is_week_boundary_pending)
        m.increment_time(17)
        self.assertEqual(m.steps, frozen + 1, "resolve resumes advancing")
        # The next boundary is one full week later, not immediately.
        for _ in range(50):
            m.increment_time(17)
        self.assertFalse(m.is_week_boundary_pending, "no immediate re-trigger")

    def test_week_index_is_derived_from_steps(self):
        m = Mediator(seed=0)
        for boundary in (
            0,
            WEEK_LENGTH_STEPS - 1,
            WEEK_LENGTH_STEPS,
            WEEK_LENGTH_STEPS * 3,
        ):
            m.steps = boundary
            self.assertEqual(m.week_index, boundary // WEEK_LENGTH_STEPS)

    def test_speed_4_crossing_holds_without_landing_exactly(self):
        # review MAJOR: at speed 4 steps jump +4, so a boundary is CROSSED, not
        # landed on. Pin that the hold fires on the crossing (old//W < steps//W),
        # NOT on steps == W -- an exact-landing-only mutant would skip this.
        m = Mediator(seed=0)
        m.week_calendar = True
        while m.steps < WEEK_LENGTH_STEPS - 2:  # speed 1 up to steps == W-2
            m.increment_time(17)
        self.assertEqual(m.steps, WEEK_LENGTH_STEPS - 2)
        m.game_speed_multiplier = 4
        m.increment_time(17)  # W-2 -> W+2, jumping ACROSS the boundary
        self.assertEqual(m.steps, WEEK_LENGTH_STEPS + 2, "jumped past, never on, W")
        self.assertTrue(m.is_week_boundary_pending, "the +4 crossing still holds")
        self.assertEqual(m.week_index, 1)

    def test_space_and_speed_cannot_dismiss_the_week_pause(self):
        m = Mediator(seed=0)
        m.week_calendar = True
        _step_to_boundary(m)
        m.is_paused = False  # the SPACE / user-pause toggle path
        self.assertTrue(m.is_week_boundary_pending, "Space cannot clear the week pause")
        m.set_game_speed(4)  # a speed button
        self.assertTrue(m.is_week_boundary_pending, "speed cannot clear the week pause")

    def test_no_hold_when_the_boundary_tick_also_game_overs(self):
        # review MAJOR: a tick that CROSSES a boundary AND flips is_game_over must
        # NOT hold "week" -- game over wins. Drive the hold with a genuine crossing
        # (old_steps W-1 -> steps W) and a post-tick game-over state; deleting the
        # `or is_game_over` guard would hold here (the mutation the pre-set,
        # never-crossing version missed).
        crossed = Mediator(seed=0)
        crossed.week_calendar = True
        crossed.steps = WEEK_LENGTH_STEPS  # the tick advanced ACROSS the boundary...
        crossed.is_game_over = True  # ...and flipped game over on the same tick
        crossed._maybe_hold_week_boundary(WEEK_LENGTH_STEPS - 1)
        self.assertFalse(
            crossed.is_week_boundary_pending,
            "game over on the crossing tick blocks the hold",
        )
        # NOT vacuous: the identical crossing DOES hold when the run is alive.
        alive = Mediator(seed=0)
        alive.week_calendar = True
        alive.steps = WEEK_LENGTH_STEPS
        alive._maybe_hold_week_boundary(WEEK_LENGTH_STEPS - 1)
        self.assertTrue(
            alive.is_week_boundary_pending, "the same crossing holds if alive"
        )

    def test_the_boundary_hold_does_not_interrupt_queued_settlement(self):
        # review MAJOR/MINOR: the hold must come AFTER _drain_and_settle_queued_returns,
        # so a locomotive unassignment queued to settle ON the boundary-crossing tick
        # completes identically to a calendar-OFF control. `settle()` early-returns
        # while paused, so a hold placed BEFORE the settle would STRAND the metro
        # (len(metros)/available_locomotives would diverge) -- this pins that.
        def board(calendar):
            m = Mediator(seed=0)
            m.week_calendar = calendar
            path = m.create_path_from_station_indices([0, 1, 2])
            m.assign_locomotive(path)
            for _ in range(WEEK_LENGTH_STEPS - 1):
                m.increment_time(17)
            # Queue the unassignment so it settles on the boundary-crossing tick.
            m.queue_locomotive_unassignment(m.paths[0])
            m.increment_time(17)
            return m

        on = board(True)
        off = board(False)
        self.assertTrue(on.is_week_boundary_pending, "the boundary held the week")
        self.assertFalse(off.is_week_boundary_pending)
        self.assertEqual(on.steps, off.steps)
        # The queued metro settled in BOTH -- the hold did not strand it.
        self.assertEqual(len(on.metros), len(off.metros), "settle ran before the hold")
        self.assertEqual(on.available_locomotives, off.available_locomotives)
        self.assertEqual(on.deliveries, off.deliveries)


class _FakeSession:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class _FakeMediator:
    def __init__(self, *, week_pending=False, game_over=False):
        self._week_pending = week_pending
        self.is_game_over = game_over
        self.resolved = 0
        self.week_index = 1
        self.held = []

    @property
    def is_week_boundary_pending(self):
        return self._week_pending

    def resolve_week_boundary(self):
        self._week_pending = False
        self.resolved += 1

    def hold_pause_reason(self, reason):
        self.held.append(reason)

    def release_pause_reason(self, reason):
        pass


def _offer_controller(*, week_pending=True, game_over=False):
    session = _FakeSession()
    mediator = _FakeMediator(week_pending=week_pending, game_over=game_over)

    def build_game(map_id="classic"):
        return mediator, SimpleNamespace(), session

    controller = AppController(build_game, start_state=AppScreen.PLAYING)
    # AppController built its own initial mediator/session; install the fakes so we
    # drive the reconcile against a shape with the week API.
    controller.mediator = mediator
    controller.session = session
    return controller, mediator, session


class TestGM10aOfferPromotion(unittest.TestCase):
    def test_reconcile_promotes_a_pending_boundary_to_offer(self):
        controller, mediator, session = _offer_controller()
        controller.reconcile_week_boundary()
        self.assertEqual(controller.state, AppScreen.OFFER)
        # It cancelled the in-progress gameplay gesture via the letterbox cancel.
        # review MAJOR: pin the EXACT event, not just the count -- a mutant that
        # dispatches None or a MOUSE_DOWN (or drops the off-viewport position)
        # would still leave len == 1.
        self.assertEqual(len(session.dispatched), 1, "one off-viewport cancel")
        (cancel,) = session.dispatched
        self.assertIsInstance(cancel, MouseEvent)
        self.assertEqual(cancel.event_type, MouseEventType.MOUSE_UP)
        self.assertEqual((cancel.position.left, cancel.position.top), (-1, -1))

    def test_a_truthy_but_not_true_pending_flag_stays_out_of_offer(self):
        # review MAJOR: the guard is `is True`, not truthy, so a MagicMock whose
        # is_week_boundary_pending auto-vivifies to a truthy Mock must NOT promote.
        # SimpleNamespace (getattr -> False) can't distinguish `is True` from
        # truthy; a live Mock can. This pins the exact `is True` semantics.
        controller, _mediator, session = _offer_controller()
        stub = MagicMock()
        stub.is_game_over = False
        # is_week_boundary_pending is a truthy auto-Mock, never the literal True.
        controller.mediator = stub
        controller.reconcile_week_boundary()
        self.assertEqual(controller.state, AppScreen.PLAYING)
        self.assertEqual(session.dispatched, [], "no cancel dispatched")

    def test_game_over_wins_over_a_pending_week(self):
        # review MAJOR: with both pending, reconcile_game_over (run first) promotes
        # to GAME_OVER and reconcile_week_boundary no-ops on a terminal mediator.
        controller, mediator, session = _offer_controller(
            week_pending=True, game_over=True
        )
        controller.reconcile_game_over()
        controller.reconcile_week_boundary()
        self.assertEqual(controller.state, AppScreen.GAME_OVER)

    def test_reconcile_is_a_noop_without_a_pending_boundary(self):
        controller, mediator, session = _offer_controller(week_pending=False)
        controller.reconcile_week_boundary()
        self.assertEqual(controller.state, AppScreen.PLAYING)

    def test_a_stub_mediator_never_enters_the_offer(self):
        # A seam-less controller's minimal mediator has no week API; the `is True`
        # guard keeps it out of the offer even against a truthy attribute.
        build_game = lambda map_id="classic": (  # noqa: E731
            SimpleNamespace(is_game_over=False),
            SimpleNamespace(),
            _FakeSession(),
        )
        controller = AppController(build_game, start_state=AppScreen.PLAYING)
        controller.reconcile_week_boundary()  # must not raise, must not enter OFFER
        self.assertEqual(controller.state, AppScreen.PLAYING)


class TestGM10aOfferArming(unittest.TestCase):
    def _up(self, controller, rect):
        controller.handle_event(
            MouseEvent(MouseEventType.MOUSE_UP, Point(rect.centerx, rect.centery))
        )

    def _down(self, controller, rect):
        controller.handle_event(
            MouseEvent(MouseEventType.MOUSE_DOWN, Point(rect.centerx, rect.centery))
        )

    def test_continue_requires_an_offer_local_down_up_pair(self):
        # review MAJOR: a bare gameplay mouse-up that crossed the boundary must NOT
        # dismiss the offer -- only an in-offer down->up on Continue resolves it.
        controller, mediator, session = _offer_controller()
        controller.reconcile_week_boundary()
        self.assertEqual(controller.state, AppScreen.OFFER)
        rect = offer_menu_layout(screen_width, screen_height)["continue"]
        # A bare release (no matching in-offer press) is a no-op.
        self._up(controller, rect)
        self.assertEqual(controller.state, AppScreen.OFFER, "a bare release is ignored")
        self.assertEqual(mediator.resolved, 0)
        # An armed press+release resolves the week and resumes PLAYING.
        self._down(controller, rect)
        self._up(controller, rect)
        self.assertEqual(controller.state, AppScreen.PLAYING)
        self.assertEqual(mediator.resolved, 1)


class TestGM10aSaveBlock(unittest.TestCase):
    def test_saving_is_blocked_while_a_week_boundary_is_pending(self):
        m = Mediator(seed=0)
        m.week_calendar = True
        _step_to_boundary(m)
        self.assertTrue(m.is_week_boundary_pending)
        with self.assertRaisesRegex(ValueError, "week-boundary offer is pending"):
            serialize_game(m)
        # Resolving lets the save proceed.
        m.resolve_week_boundary()
        self.assertIsInstance(serialize_game(m), dict)


class TestGM10aRLUnaffected(unittest.TestCase):
    def test_a_headless_env_never_pauses_for_a_week(self):
        # The env's Mediator leaves the calendar OFF, so stepping past a boundary
        # never freezes and never holds "week" -- the RL/checkpoint path is
        # structurally free of the calendar.
        env = MiniMetroEnv()
        env.reset(seed=0)
        self.assertFalse(env.mediator.week_calendar)
        for _ in range(WEEK_LENGTH_STEPS + 60):
            env.mediator.step_time(17)
        self.assertGreater(env.mediator.steps, WEEK_LENGTH_STEPS, "no headless freeze")
        self.assertFalse(env.mediator.is_week_boundary_pending)
        self.assertFalse(env.mediator.is_paused)

    def test_the_pixel_rl_env_is_calendar_free_past_a_boundary(self):
        # The player-pixel env (the first-class RL boundary, GM-09a2) builds a bare
        # Mediator too, so the calendar is OFF and stepping past a week never freezes
        # the pixel task. step_time -> increment_time -> the hold, so this is NOT
        # vacuous: a mutant defaulting week_calendar True would freeze here.
        env = PlayerPixelEnv()
        env.reset(seed=0)
        mediator = env._mediator
        self.assertFalse(
            mediator.week_calendar, "the pixel env leaves the calendar off"
        )
        for _ in range(WEEK_LENGTH_STEPS + 60):
            mediator.step_time(17)
        self.assertGreater(mediator.steps, WEEK_LENGTH_STEPS, "no pixel-env freeze")
        self.assertFalse(mediator.is_week_boundary_pending)
        self.assertFalse(mediator.is_paused)


# --- run_game integration harness (GM-10a review MAJOR: #gating + #offer-loop) ---
# Drives the REAL main.run_game and the REAL AppController behind recording fakes
# for the Mediator/GameSession/GameRenderer factory seam (test_gm07a idiom), so the
# gating (week_calendar = max_frames is None) and the offer promotion/render/QUIT
# path are pinned against the live loop, not a hand-rolled controller.
_ELAPSED_MS = 17


def _quit_event():
    return SimpleNamespace(type=pygame.QUIT)


class _LoopRenderer:
    def __init__(self):
        self.draws = []

    def draw(self, surface, mediator, alpha, reduced_motion=False):
        self.draws.append(getattr(mediator, "week_index", None))


class _LoopSession:
    def __init__(self, mediator, **kwargs):
        self.mediator = mediator
        self.dispatched = []
        self.step_observer = kwargs.get("step_observer")

    def prepare_layout(self, surface):
        pass

    def dispatch(self, event):
        self.dispatched.append(event)

    def advance(self, elapsed_ms):
        return SimpleNamespace(alpha=1.0)


class _LoopMediator:
    def __init__(self, *, pending=False, week_index=1):
        self.is_game_over = False
        self._pending = pending
        self.week_index = week_index
        self.week_calendar = None  # build_game/build_from set this on construction
        self.map_definition = SimpleNamespace(
            map_id="classic", map_definition_version=1
        )
        self.resolved = 0

    @property
    def is_week_boundary_pending(self):
        return self._pending

    def resolve_week_boundary(self):
        self._pending = False
        self.resolved += 1

    def hold_pause_reason(self, reason):
        pass

    def release_pause_reason(self, reason):
        pass


def _drive_run_game(frames_events, *, max_frames, start_state=None, pending=False):
    """Run ``main.run_game`` over the pumped frames; return the captured harness."""

    captured = {}
    offer_draws = []
    autosaves = []
    real_app_controller = main.AppController

    def build_mediator(map_definition=None):
        mediator = _LoopMediator(pending=pending)
        captured["mediator"] = mediator
        return mediator

    def make_controller(*a, **k):
        controller = real_app_controller(*a, **k)
        captured["controller"] = controller
        return controller

    batches = iter(frames_events)
    exited = {"raised": False}

    with (
        patch("main.pygame") as pygame_mock,
        patch("main.Mediator", side_effect=build_mediator),
        patch(
            "main.GameSession",
            side_effect=lambda mediator, **k: _LoopSession(mediator, **k),
        ),
        patch("main.GameRenderer", side_effect=_LoopRenderer),
        patch("main.AppController", side_effect=make_controller),
        patch(
            "main.draw_offer_screen",
            side_effect=lambda surface, week_index: offer_draws.append(week_index),
        ),
        patch("main.draw_title_screen", side_effect=lambda *a, **k: None),
        patch("main.write_autosave", side_effect=lambda m: autosaves.append(m)),
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
        pygame_mock.event.get.side_effect = lambda: next(batches)
        try:
            main.run_game(max_frames=max_frames, start_state=start_state)
        except SystemExit:
            exited["raised"] = True
    return SimpleNamespace(
        mediator=captured.get("mediator"),
        controller=captured.get("controller"),
        offer_draws=offer_draws,
        autosaves=autosaves,
        exited=exited["raised"],
    )


class TestGM10aGating(unittest.TestCase):
    def test_a_frame_limited_run_leaves_the_calendar_off(self):
        # review MAJOR: the gate is `week_calendar = max_frames is None`. A bounded
        # (frame-limited/headless) run must build the game with the calendar OFF, so
        # a screenshot/CI run never soft-locks at a boundary with no one to resolve.
        harness = _drive_run_game(
            [[]], max_frames=1, start_state=AppScreen.PLAYING, pending=False
        )
        self.assertIs(
            harness.mediator.week_calendar, False, "bounded run: calendar gated OFF"
        )

    def test_an_unbounded_interactive_run_enables_the_calendar(self):
        # The same gate: an unbounded (interactive human) run builds with the
        # calendar ON. Driven to exit immediately via a title-screen QUIT so the
        # construction-time build_game is all we assert.
        harness = _drive_run_game(
            [[_quit_event()]], max_frames=None, start_state=None, pending=False
        )
        self.assertTrue(harness.exited, "QUIT terminated the unbounded run")
        self.assertIs(
            harness.mediator.week_calendar, True, "unbounded run: calendar gated ON"
        )

    def test_the_tutorial_mediator_leaves_the_calendar_off(self):
        # build_tutorial never sets week_calendar, so the coached tutorial inherits
        # the Mediator default (OFF) -- a tutorial week boundary never freezes.
        self.assertFalse(
            main._tutorial_mediator().week_calendar, "tutorial: calendar off"
        )


class TestGM10aRunLoopOffer(unittest.TestCase):
    def test_a_pending_boundary_promotes_and_renders_the_offer(self):
        # review MAJOR: the live loop must promote a pending boundary to OFFER and
        # render the modal (draw_offer_screen with the week index) OVER the frozen
        # game frame (the renderer still draws), cancelling the in-progress gesture.
        harness = _drive_run_game(
            [[]], max_frames=1, start_state=AppScreen.PLAYING, pending=True
        )
        self.assertEqual(harness.controller.state, AppScreen.OFFER)
        self.assertEqual(harness.offer_draws, [1], "the modal drew the week index")
        self.assertTrue(
            harness.controller.renderer.draws, "the frozen frame drew under the modal"
        )
        cancels = [
            e
            for e in harness.controller.session.dispatched
            if isinstance(e, MouseEvent)
        ]
        self.assertEqual(len(cancels), 1, "one letterbox cancel dispatched")
        self.assertEqual(cancels[0].event_type, MouseEventType.MOUSE_UP)
        self.assertEqual((cancels[0].position.left, cancels[0].position.top), (-1, -1))

    def test_closing_mid_offer_resolves_the_week_and_autosaves(self):
        # review MAJOR: a window-close WHILE the offer is up (frame 0 promotes, frame
        # 1 delivers QUIT with state already OFFER) resolves the week and autosaves
        # the resumed game, so Continue reloads PAST the boundary (GM-10a).
        harness = _drive_run_game(
            [[], [_quit_event()]],
            max_frames=None,
            start_state=AppScreen.PLAYING,
            pending=True,
        )
        self.assertTrue(harness.exited, "QUIT raised SystemExit")
        self.assertEqual(harness.mediator.resolved, 1, "closing resolved the week")
        self.assertEqual(
            harness.autosaves, [harness.mediator], "the resumed game was autosaved"
        )

    def test_no_offer_no_autosave_on_a_plain_title_quit(self):
        # Control: without a pending boundary a TITLE QUIT neither resolves a week
        # nor autosaves -- isolates the OFFER-QUIT branch from the title close.
        harness = _drive_run_game(
            [[_quit_event()]], max_frames=None, start_state=None, pending=False
        )
        self.assertTrue(harness.exited)
        self.assertEqual(harness.mediator.resolved, 0)
        self.assertEqual(harness.autosaves, [], "a title-screen close writes no save")


if __name__ == "__main__":
    unittest.main()

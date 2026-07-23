"""GM-08b red contract: the ``main.run_game`` audio consumer wiring (D-030).

Covers the loop-level plumbing that the pure ``audio`` differ leaves to ``main``:

* ``_default_audio_backend`` — real ``create_audio`` only in interactive play
  (``max_frames is None``); headless / ``max_frames`` runs and the whole suite
  get an inert ``NullAudio`` and open no mixer (review MINOR-3c/4). ``audio.py``
  imports its OWN ``pygame``, so this ``max_frames`` gate — not a ``main.pygame``
  patch — is what keeps the suite and headless/RL play silent.
* ``_audio_step`` — the per-frame consumer: it owns its OWN session reference and
  resets the snapshot the moment ``controller.session`` changes (review MAJOR-1),
  so a Continue-loaded mediator's non-zero counters never fire a spurious tone
  burst; then it plays one tone per delta ONLY on a gameplay screen.
* ``run_game`` — invokes the consumer once per frame with the (injected) backend
  and never touches ``create_audio`` under ``max_frames``.
"""

from __future__ import annotations

import contextlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import DEFAULT, MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main
from app_controller import AppScreen
from config import screen_height, screen_width


def _host(deliveries=0, paths=1, stations=3, game_over=False, snap_lists=()):
    stations_seq = [SimpleNamespace(snap_blips=list(b)) for b in snap_lists]
    return SimpleNamespace(
        deliveries=deliveries,
        unlocked_num_paths=paths,
        unlocked_num_stations=stations,
        is_game_over=game_over,
        all_stations=stations_seq,
    )


class _FakeBackend:
    def __init__(self):
        self.played: list[tuple] = []

    def play(self, event, master_percent, sfx_percent):
        self.played.append((event, master_percent, sfx_percent))


def _controller(session, mediator, master=100, sfx=100):
    return SimpleNamespace(
        session=session,
        mediator=mediator,
        current_settings=SimpleNamespace(master_volume=master, sfx_volume=sfx),
    )


class TestGM08bDefaultBackend(unittest.TestCase):
    def test_interactive_play_builds_the_real_backend(self):
        sentinel = object()
        with patch("main.create_audio", return_value=sentinel) as create_audio:
            result = main._default_audio_backend(None)
        create_audio.assert_called_once()
        self.assertIs(result, sentinel, "max_frames is None -> real create_audio()")

    def test_headless_run_uses_nullaudio_and_opens_no_mixer(self):
        with patch("main.create_audio") as create_audio:
            result = main._default_audio_backend(5)
        create_audio.assert_not_called()
        self.assertIsInstance(
            result, main.NullAudio, "a max_frames run never constructs a mixer"
        )


class TestGM08bAudioStep(unittest.TestCase):
    def test_session_change_resets_the_snapshot_with_no_burst(self):
        # MAJOR-1: a Continue-loaded mediator jumps to non-zero counters under a
        # NEW session while the stale snapshot is the title baseline. The step
        # must reset BEFORE diffing, so no delivery/path/station burst fires.
        backend = _FakeBackend()
        old_session, new_session = object(), object()
        loaded = _host(deliveries=30, paths=2, stations=5)
        controller = _controller(new_session, loaded)
        stale = main.snapshot_of(_host(deliveries=0, paths=1, stations=3))
        prev, snap = main._audio_step(
            controller, AppScreen.PLAYING, old_session, stale, backend
        )
        self.assertEqual(backend.played, [], "session change resets before diff")
        self.assertIs(prev, new_session, "the consumer adopts the new session ref")
        # The snapshot now matches the loaded run, so the next flat frame is silent.
        main._audio_step(controller, AppScreen.PLAYING, prev, snap, backend)
        self.assertEqual(backend.played, [])

    def test_same_session_delta_plays_at_the_live_volumes(self):
        backend = _FakeBackend()
        session = object()
        controller = _controller(session, _host(deliveries=1), master=80, sfx=40)
        snap = main.snapshot_of(_host(deliveries=0))
        prev, snap = main._audio_step(
            controller, AppScreen.PLAYING, session, snap, backend
        )
        self.assertEqual([e for e, _m, _s in backend.played], ["delivery"])
        self.assertEqual(backend.played[0][1:], (80, 40), "live SFX volumes routed")
        self.assertIs(prev, session, "an unchanged session ref is preserved")

    def test_no_audio_outside_gameplay_screens(self):
        backend = _FakeBackend()
        session = object()
        controller = _controller(session, _host(deliveries=5))
        snap = main.snapshot_of(_host(deliveries=0))
        for screen in (AppScreen.TITLE, AppScreen.SETTINGS):
            main._audio_step(controller, screen, session, snap, backend)
        self.assertEqual(
            backend.played, [], "silent on title/settings even with a delta"
        )

    def test_pause_and_game_over_screens_still_play(self):
        for screen in (AppScreen.PAUSE_MENU, AppScreen.GAME_OVER):
            backend = _FakeBackend()
            session = object()
            controller = _controller(session, _host(deliveries=1))
            snap = main.snapshot_of(_host(deliveries=0))
            main._audio_step(controller, screen, session, snap, backend)
            self.assertEqual(
                [e for e, _m, _s in backend.played], ["delivery"], f"{screen} audible"
            )


def _loop_harness():
    """The GM-08a-style fully-mocked pygame loop harness, with a real-typed
    Mediator mock so the real snapshot differ runs without a real mixer."""
    patches = patch.multiple(
        "main",
        pygame=DEFAULT,
        Mediator=DEFAULT,
        GameSession=DEFAULT,
        GameRenderer=DEFAULT,
        convert_pygame_event=DEFAULT,
        read_settings=DEFAULT,
    )
    mocks = patches.start()
    mocks["read_settings"].return_value = SimpleNamespace(
        master_volume=100, sfx_volume=100, fullscreen=False, reduced_motion=False
    )
    pygame_mock = mocks["pygame"]
    pygame_mock.QUIT = 12
    pygame_mock.RESIZABLE = 1
    pygame_mock.FULLSCREEN = 2
    pygame_mock.SCALED = 4
    window = MagicMock()
    window.get_size.return_value = (screen_width, screen_height)
    pygame_mock.display.set_mode.return_value = window
    surface = MagicMock()
    surface.get_size.return_value = (screen_width, screen_height)
    pygame_mock.Surface.return_value = surface
    clock = MagicMock()
    clock.tick.return_value = 17
    pygame_mock.time.Clock.return_value = clock
    pygame_mock.event.get.return_value = []
    session = mocks["GameSession"].return_value
    session.advance.return_value = SimpleNamespace(alpha=1.0)
    mediator = mocks["Mediator"].return_value
    mediator.deliveries = 0
    mediator.unlocked_num_paths = 1
    mediator.unlocked_num_stations = 3
    mediator.is_game_over = False
    mediator.all_stations = []
    return patches, pygame_mock


class TestGM08bRunGameWiring(unittest.TestCase):
    def test_bounded_run_game_never_constructs_a_mixer(self):
        patches, _pygame = _loop_harness()
        try:
            with patch("main.create_audio") as create_audio:
                main.run_game(max_frames=2)  # no injected backend
            create_audio.assert_not_called()
        finally:
            patches.stop()

    def test_unbounded_run_game_never_constructs_a_mixer(self):
        # The exact review-MAJOR scenario: a loop test drives REAL run_game with
        # max_frames=None and patches only main.pygame. audio.py imports its own
        # pygame, so the mixer-free guarantee must come from run_game defaulting
        # to NullAudio, NOT from a max_frames gate. The backend is chosen during
        # setup, so we let setup complete then exit the loop from the audio step
        # (before any render/QUIT handling) and assert create_audio never ran.
        patches, _pygame = _loop_harness()
        try:

            def _exit_after_setup(*args, **kwargs):
                raise SystemExit

            with patch("main.create_audio") as create_audio:
                with patch("main._audio_step", side_effect=_exit_after_setup):
                    with contextlib.suppress(SystemExit):
                        main.run_game()  # unbounded, no injected backend
            create_audio.assert_not_called()
        finally:
            patches.stop()

    def test_loop_invokes_the_consumer_each_frame_with_the_injected_backend(self):
        patches, _pygame = _loop_harness()
        try:
            backend = _FakeBackend()
            calls: list[tuple] = []

            def _spy(controller, state, prev_session, snapshot, used_backend):
                calls.append((state, used_backend))
                return prev_session, snapshot

            with patch("main._audio_step", side_effect=_spy):
                main.run_game(max_frames=3, audio_backend=backend)
            self.assertEqual(len(calls), 3, "one consumer step per frame")
            for state, used_backend in calls:
                self.assertIsInstance(
                    state, AppScreen, "post-reconcile state is passed"
                )
                self.assertIs(used_backend, backend, "the injected backend is threaded")
        finally:
            patches.stop()


if __name__ == "__main__":
    unittest.main()

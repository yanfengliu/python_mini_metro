"""GM-08b red contract: the ``audio`` module (D-030).

Mints the main-only procedural-tone audio backend: deterministic tone
generation, a fail-safe ``create_audio`` factory (``NullAudio`` on any device
failure), a real ``ProceduralAudio`` mixer backend, and a PURE ``diff_and_play``
counter differ. Every missing product surface becomes a clean FAILURE (never an
import/collection ERROR) through the ``require_attribute`` guards, mirroring
``test_gm08a_settings``.
"""

from __future__ import annotations

import importlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

AUDIO_MODULE = "audio"


def _module(testcase, name=AUDIO_MODULE):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-08b product module is missing: {name} ({error})")


def _symbol(testcase, name, module_name=AUDIO_MODULE):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-08b product symbol is missing: {module_name}.{name}"
    )
    return value


def _host(deliveries=0, paths=1, stations=3, game_over=False, snap_lists=()):
    # A duck-typed mediator stand-in: the pure differ reads attributes only.
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


class TestGM08bToneGeneration(unittest.TestCase):
    def test_generate_tone_is_deterministic_mono_int16(self):
        generate = _symbol(self, "_generate_tone")
        import numpy as np

        a = generate(880.0, 90)
        b = generate(880.0, 90)
        self.assertEqual(a.dtype, np.int16, "tones are int16")
        self.assertEqual(a.ndim, 1, "generated tones are mono (1-D)")
        self.assertGreater(a.shape[0], 0)
        self.assertEqual(a.tobytes(), b.tobytes(), "generation is byte-stable")
        # A different spec yields different bytes.
        self.assertNotEqual(a.tobytes(), generate(220.0, 300).tobytes())

    def test_generate_tone_length_tracks_sample_rate(self):
        # The rate is a parameter so the tone stays correct against whatever rate
        # the mixer negotiated; a higher rate yields proportionally more samples
        # and different bytes (review MINOR: no detune on a pre-initialized mixer).
        generate = _symbol(self, "_generate_tone")
        low = generate(880.0, 100, 44100)
        high = generate(880.0, 100, 48000)
        self.assertEqual(low.shape[0], int(44100 * 100 / 1000))
        self.assertEqual(high.shape[0], int(48000 * 100 / 1000))
        self.assertNotEqual(low.tobytes(), high.tobytes(), "rate changes the samples")

    def test_shape_for_mixer_matches_channel_count(self):
        shape_for = _symbol(self, "_shape_for_mixer")
        generate = _symbol(self, "_generate_tone")
        mono = generate(880.0, 50)
        stereo = shape_for(mono, 2)
        self.assertEqual(
            stereo.shape, (mono.shape[0], 2), "stereo duplicates the column"
        )
        self.assertEqual(stereo.dtype, mono.dtype)
        # Mono passthrough.
        self.assertEqual(shape_for(mono, 1).ndim, 1)


class TestGM08bCreateAudioFailSafe(unittest.TestCase):
    def test_create_audio_returns_nullaudio_when_mixer_init_fails(self):
        create_audio = _symbol(self, "create_audio")
        null_type = _symbol(self, "NullAudio")
        module = _module(self)
        with mock.patch.object(
            module.pygame.mixer, "init", side_effect=module.pygame.error("no device")
        ):
            backend = create_audio()
        self.assertIsInstance(
            backend, null_type, "no device -> NullAudio, never raises"
        )

    def test_nullaudio_play_is_a_silent_no_op(self):
        null_type = _symbol(self, "NullAudio")
        # Any arguments, no exception, no return contract beyond None.
        self.assertIsNone(null_type().play("delivery", 100, 100))


class TestGM08bDiffAndPlay(unittest.TestCase):
    def _diff(self):
        return _symbol(self, "diff_and_play"), _symbol(self, "snapshot_of")

    def test_flat_frame_plays_nothing(self):
        diff_and_play, snapshot_of = self._diff()
        host = _host()
        backend = _FakeBackend()
        snap = snapshot_of(host)
        diff_and_play(host, snap, backend, 100, 100)
        self.assertEqual(backend.played, [], "no delta -> no tone")

    def test_snapshot_tolerates_a_host_missing_counters(self):
        # A cosmetic side-effect must never crash the loop: a minimal host with
        # none of the audio counters snapshots to all-zeros and drives no tone,
        # so unrelated run_game surfaces stay decoupled from audio.
        snapshot_of = _symbol(self, "snapshot_of")
        diff_and_play = _symbol(self, "diff_and_play")
        bare = SimpleNamespace()
        snap = snapshot_of(bare)
        self.assertEqual(snap, (0, 0, 0, False, 0), "absent counters read as zero")
        backend = _FakeBackend()
        diff_and_play(bare, snap, backend, 100, 100)
        self.assertEqual(backend.played, [], "a counterless host is silent")

    def test_each_event_plays_once_on_a_positive_delta(self):
        diff_and_play, snapshot_of = self._diff()
        backend = _FakeBackend()
        before = _host(
            deliveries=5, paths=1, stations=3, game_over=False, snap_lists=([1],)
        )
        snap = snapshot_of(before)
        after = _host(
            deliveries=6, paths=2, stations=4, game_over=True, snap_lists=([1, 2],)
        )
        diff_and_play(after, snap, backend, 80, 40)
        events = [e for (e, _m, _s) in backend.played]
        self.assertCountEqual(
            events,
            ["delivery", "path_unlock", "station_unlock", "game_over", "snap"],
            "each newly-occurred event fires exactly once",
        )
        for _e, master, sfx in backend.played:
            self.assertEqual((master, sfx), (80, 40), "the live volumes are passed")

    def test_game_over_fires_only_on_the_false_to_true_edge(self):
        diff_and_play, snapshot_of = self._diff()
        backend = _FakeBackend()
        over = _host(game_over=True)
        snap = snapshot_of(over)  # already over
        diff_and_play(over, snap, backend, 100, 100)
        self.assertEqual(
            backend.played, [], "still-over frame does not replay game_over"
        )

    def test_returned_snapshot_advances_so_the_next_frame_is_flat(self):
        diff_and_play, snapshot_of = self._diff()
        backend = _FakeBackend()
        host = _host(deliveries=1)
        snap = snapshot_of(_host(deliveries=0))
        snap = diff_and_play(host, snap, backend, 100, 100)
        self.assertEqual(len(backend.played), 1)
        diff_and_play(host, snap, backend, 100, 100)  # same host, advanced snapshot
        self.assertEqual(len(backend.played), 1, "the advanced snapshot is now flat")


class TestGM08bProceduralAudioRealMixer(unittest.TestCase):
    """Exercises a REAL mixer under the dummy audio driver (review MAJOR-2)."""

    def setUp(self):
        import pygame

        self._prior_driver = os.environ.get("SDL_AUDIODRIVER")
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    def tearDown(self):
        import pygame

        try:
            pygame.mixer.quit()
        except Exception:
            pass
        if self._prior_driver is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = self._prior_driver

    def test_dummy_driver_builds_a_real_backend_and_plays(self):
        create_audio = _symbol(self, "create_audio")
        procedural_type = _symbol(self, "ProceduralAudio")
        backend = create_audio()
        self.assertIsInstance(
            backend,
            procedural_type,
            "the dummy driver must yield a real ProceduralAudio, not a degraded NullAudio",
        )
        # Every event plays without error at the computed gain.
        for event in ("delivery", "path_unlock", "station_unlock", "game_over", "snap"):
            backend.play(event, 100, 100)
        # The built tone tracks the mixer's ACTUAL negotiated rate, not the
        # hardcoded default (review MINOR): the delivery sound's sample count
        # equals int(real_rate * 90ms / 1000).
        import pygame

        real_rate = pygame.mixer.get_init()[0]
        samples = pygame.sndarray.array(backend._sounds["delivery"])
        self.assertEqual(
            len(samples),
            int(real_rate * 90 / 1000),
            "ProceduralAudio generates against get_init()[0], not a constant",
        )


if __name__ == "__main__":
    unittest.main()

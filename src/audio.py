"""GM-08b procedural-tone gameplay audio (D-030).

A main-only sound-effects backend built from short, deterministic, synthesized
tones — no external assets. It holds ALL of its own constants (importing only
``pygame`` and ``numpy``, never ``config``), so the high-risk balance module is
untouched and the mediator/rendering/save surfaces stay audio-free.

The module offers:

* :func:`create_audio` — a FAIL-SAFE factory returning a real
  :class:`ProceduralAudio` when a mixer is available, or an inert
  :class:`NullAudio` on any device/build failure (never raising), so audio can
  never block gameplay, headless play, or tests.
* :func:`diff_and_play` / :func:`snapshot_of` — a PURE, duck-typed per-frame
  differ that turns monotonic gameplay counters into one tone per newly-occurred
  event. It reads attributes only (no gameplay import), so it is unit-testable
  with a plain namespace and keeps ``main``'s wiring to a couple of lines.

Only ``main`` imports this module; the loop-level consumer fires solely inside
``main.run_game``, so agent, headless, and RL entries construct no mixer.
"""

from __future__ import annotations

import numpy as np
import pygame

# --- Tone specification (in-module, config-free) --------------------------

_SAMPLE_RATE = 44100
_AMPLITUDE = 0.5  # headroom below int16 clipping
_RAMP_SECONDS = 0.005  # short linear attack/decay to avoid click artifacts

# Per-event (frequency_hz, duration_ms): distinct, short, unobtrusive cues.
_TONE_SPECS: dict[str, tuple[float, int]] = {
    "delivery": (880.0, 90),  # bright A5 confirmation
    "path_unlock": (659.25, 140),  # E5, a touch longer
    "station_unlock": (987.77, 120),  # B5
    "game_over": (220.0, 320),  # low, long A3
    "snap": (1318.51, 40),  # high, very short click
}

EVENT_NAMES: tuple[str, ...] = tuple(_TONE_SPECS)


def _generate_tone(
    frequency_hz: float, duration_ms: int, sample_rate: int = _SAMPLE_RATE
) -> np.ndarray:
    """Build a deterministic MONO int16 sine tone with a click-free envelope.

    Given fixed inputs (including ``sample_rate``) the output bytes are stable
    and device-independent, so a tone can be pinned byte-for-byte in tests
    without any external file. The rate is a parameter, not a constant, so the
    pitch/duration stay correct against whatever rate the mixer negotiated
    (review MINOR — a pre-initialized mixer at a different rate would otherwise
    detune the tone).
    """
    sample_count = int(sample_rate * duration_ms / 1000)
    if sample_count <= 0:
        return np.zeros(0, dtype=np.int16)
    t = np.arange(sample_count, dtype=np.float64) / sample_rate
    wave = np.sin(2.0 * np.pi * frequency_hz * t)
    envelope = np.ones(sample_count, dtype=np.float64)
    ramp = min(sample_count // 2, int(sample_rate * _RAMP_SECONDS))
    if ramp > 0:
        envelope[:ramp] = np.linspace(0.0, 1.0, ramp, dtype=np.float64)
        envelope[-ramp:] = np.linspace(1.0, 0.0, ramp, dtype=np.float64)
    samples = wave * envelope * (_AMPLITUDE * 32767.0)
    return samples.astype(np.int16)


def _shape_for_mixer(mono: np.ndarray, channels: int) -> np.ndarray:
    """Match a mono tone to the mixer's channel count.

    A stereo mixer requires a 2-D ``(n, channels)`` array for ``make_sound``;
    a mono mixer takes the 1-D array unchanged.
    """
    if channels <= 1:
        return mono
    return np.repeat(mono.reshape(-1, 1), channels, axis=1)


class NullAudio:
    """Inert backend: every :meth:`play` is a silent no-op."""

    def play(self, event: str, master_percent: int, sfx_percent: int) -> None:
        return None


class ProceduralAudio:
    """Real mixer backend: one pre-built :class:`pygame.mixer.Sound` per event."""

    def __init__(self) -> None:
        # Read the ACTUAL negotiated format: pygame.init() may have already
        # opened the mixer, so create_audio's requested frequency can be a no-op
        # and the real rate/channel count come from get_init() (review MINOR +
        # NIT — generate against the real rate, not the hardcoded default).
        init = pygame.mixer.get_init()
        sample_rate = init[0] if init else _SAMPLE_RATE
        channels = init[2] if init else 1
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        for event, (frequency_hz, duration_ms) in _TONE_SPECS.items():
            tone = _shape_for_mixer(
                _generate_tone(frequency_hz, duration_ms, sample_rate), channels
            )
            self._sounds[event] = pygame.sndarray.make_sound(tone)

    def play(self, event: str, master_percent: int, sfx_percent: int) -> None:
        sound = self._sounds.get(event)
        if sound is None:
            return None
        gain = (master_percent / 100.0) * (sfx_percent / 100.0)
        gain = max(0.0, min(1.0, gain))
        try:
            sound.set_volume(gain)
            sound.play()  # may return None with no free channel; harmless
        except Exception:
            # Best-effort: a play failure must never disturb the game loop.
            pass
        return None


def create_audio() -> NullAudio | ProceduralAudio:
    """Return a real backend if a mixer initializes, else an inert one.

    The mixer init AND every sound build are wrapped together, so a post-init
    failure (e.g. a channel-shape mismatch) also degrades to :class:`NullAudio`
    rather than surfacing — audio-init failure can never block gameplay.
    """
    try:
        pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16)
        return ProceduralAudio()
    except Exception:
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        return NullAudio()


# --- Pure per-frame differ ------------------------------------------------

_Snapshot = tuple[int, int, int, bool, int]


def _snap_sum(host) -> int:
    stations = getattr(host, "all_stations", ()) or ()
    return sum(len(getattr(station, "snap_blips", ())) for station in stations)


def snapshot_of(host) -> _Snapshot:
    """Capture the audio-relevant counters off a duck-typed gameplay host.

    Duck-typed and TOLERANT: a host missing a counter contributes 0/False. A
    cosmetic audio side-effect must never crash the game loop, so the differ
    reads best-effort off any object exposing the real mediator's counters and
    stays inert (no tones) for one that does not.
    """
    return (
        int(getattr(host, "deliveries", 0)),
        int(getattr(host, "unlocked_num_paths", 0)),
        int(getattr(host, "unlocked_num_stations", 0)),
        bool(getattr(host, "is_game_over", False)),
        _snap_sum(host),
    )


def diff_and_play(
    host,
    snapshot: _Snapshot,
    backend,
    master_percent: int,
    sfx_percent: int,
) -> _Snapshot:
    """Play one tone per newly-occurred event; return the advanced snapshot.

    Pure and duck-typed: it reads counters off ``host`` and compares to the
    prior ``snapshot``. The four count signals are monotonic within a session
    and the game-over flag fires only on its ``False``->``True`` edge; the snap
    sum is best-effort (it can shrink as blips expire, so a snap coinciding with
    an expiry may be missed — acceptable for a cosmetic click).
    """
    current = snapshot_of(host)
    prev_deliveries, prev_paths, prev_stations, prev_over, prev_snap = snapshot
    cur_deliveries, cur_paths, cur_stations, cur_over, cur_snap = current
    if cur_deliveries > prev_deliveries:
        backend.play("delivery", master_percent, sfx_percent)
    if cur_paths > prev_paths:
        backend.play("path_unlock", master_percent, sfx_percent)
    if cur_stations > prev_stations:
        backend.play("station_unlock", master_percent, sfx_percent)
    if cur_over and not prev_over:
        backend.play("game_over", master_percent, sfx_percent)
    if cur_snap > prev_snap:
        backend.play("snap", master_percent, sfx_percent)
    return current

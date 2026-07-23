"""GM-08a typed settings store: presentation-only, fail-safe-to-defaults (D-029).

The settings persist display/audio/accessibility preferences to
``saves/settings.json`` as a strict versioned document. Like the highscores
leaderboard and unlike a save, loading is FAIL-SAFE: a missing, unreadable,
non-ASCII, malformed, forward-version, or pathologically nested file yields the
typed ``DEFAULT_SETTINGS`` and never raises, so a cosmetic preferences file can
never block play. Saving validates the board first and RAISES on failure; the
best-effort swallow lives at the ``main`` layer. It reuses the GM-07b
canonical-ASCII recipe and scalar validators -- so it joins the persistence
isolation set -- but never imports gameplay.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path as FilesystemPath
from typing import Any

from save_schema import canonical_save_bytes
from save_schema_records import _bool, _exact_keys, _int, _object, _string

SETTINGS_SCHEMA_VERSION = 1
SETTINGS_STATE_CONTRACT = "mini-metro-settings-v1"
_VOLUME_MIN = 0
_VOLUME_MAX = 100

_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "stateContract",
        "fullscreen",
        "masterVolume",
        "musicVolume",
        "sfxVolume",
        "reducedMotion",
    }
)


def _fail(label: str, message: str) -> None:
    raise ValueError(f"settings {label} {message}")


def _percent_int(value: Any, label: str) -> int:
    # A volume is an integer percent in [0, 100] -- integer (not float) so the
    # canonical bytes stay unambiguous; ``_int`` already rejects bool and float.
    number = _int(value, label)
    if not (_VOLUME_MIN <= number <= _VOLUME_MAX):
        _fail(label, f"must be an integer percent in [{_VOLUME_MIN}, {_VOLUME_MAX}]")
    return number


@dataclass(frozen=True)
class Settings:
    """The immutable presentation-only settings value."""

    fullscreen: bool = False
    master_volume: int = 100
    music_volume: int = 100
    sfx_volume: int = 100
    reduced_motion: bool = False


DEFAULT_SETTINGS = Settings()


def validate_settings(document: Any) -> None:
    """Strictly validate one settings document; any rejection raises ValueError."""

    board = _object(document, "document")
    # Reject non-string keys BEFORE _exact_keys, whose sorted() would otherwise
    # leak a TypeError on a directly-built dict with mixed int/None keys; JSON
    # only ever yields string keys, so this only guards misuse.
    if any(not isinstance(key, str) for key in board):
        _fail("document", "has a non-string key")
    # Exact-key check BEFORE any field access so a missing key raises ValueError.
    _exact_keys(board, _TOP_LEVEL_KEYS, "document")
    if _int(board["schemaVersion"], "schemaVersion") != SETTINGS_SCHEMA_VERSION:
        _fail("schemaVersion", "is unsupported (forward versions are rejected)")
    if _string(board["stateContract"], "stateContract") != SETTINGS_STATE_CONTRACT:
        _fail("stateContract", f"must be {SETTINGS_STATE_CONTRACT!r}")
    _bool(board["fullscreen"], "fullscreen")
    _bool(board["reducedMotion"], "reducedMotion")
    _percent_int(board["masterVolume"], "masterVolume")
    _percent_int(board["musicVolume"], "musicVolume")
    _percent_int(board["sfxVolume"], "sfxVolume")


def settings_to_document(settings: Settings) -> dict[str, Any]:
    """Project a ``Settings`` to its canonical document shape."""

    return {
        "schemaVersion": SETTINGS_SCHEMA_VERSION,
        "stateContract": SETTINGS_STATE_CONTRACT,
        "fullscreen": settings.fullscreen,
        "masterVolume": settings.master_volume,
        "musicVolume": settings.music_volume,
        "sfxVolume": settings.sfx_volume,
        "reducedMotion": settings.reduced_motion,
    }


def settings_from_document(document: Any) -> Settings:
    """Strictly validate a document, then construct the typed ``Settings``."""

    validate_settings(document)
    return Settings(
        fullscreen=document["fullscreen"],
        master_volume=document["masterVolume"],
        music_volume=document["musicVolume"],
        sfx_volume=document["sfxVolume"],
        reduced_motion=document["reducedMotion"],
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    # A duplicate JSON key cannot be seen on an already-parsed dict, so rejection
    # happens at parse time, mirroring save_load._reject_duplicate_keys.
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"settings file repeats the JSON object key {key!r}")
        mapping[key] = value
    return mapping


def load_settings(path: Any) -> Settings:
    """Read and strictly validate settings, or FAIL SAFE to ``DEFAULT_SETTINGS``.

    A missing, unreadable, non-ASCII, malformed, duplicate-key, forward-version,
    or pathologically nested (RecursionError) file yields the typed defaults and
    NEVER raises -- the deliberate difference from ``load_game``, because a
    cosmetic preferences file must not block play.
    """

    try:
        payload = FilesystemPath(path).read_bytes()
        document = json.loads(
            payload.decode("ascii"), object_pairs_hook=_reject_duplicate_keys
        )
        return settings_from_document(document)
    except Exception:
        return DEFAULT_SETTINGS


def save_settings(settings: Settings, path: Any) -> FilesystemPath:
    """Atomically write canonical settings bytes to ``path``; RAISE on failure.

    Validates the derived document first so a structurally invalid value can
    never overwrite a valid file. Repeats the reviewed GM-07b atomic-writer
    shape as a save-local copy (mkstemp -> fsync -> os.replace -> finally
    unlink), so an interrupted write keeps the previous valid settings.
    """

    document = settings_to_document(settings)
    validate_settings(document)
    payload = canonical_save_bytes(document)
    destination = FilesystemPath(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = FilesystemPath(temporary_name)
    handle_opened = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle_opened = True
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if not handle_opened:
            # os.fdopen never returned, so the with block never took ownership of
            # the descriptor. Close the raw fd here so a failing fdopen cannot
            # leak it and -- on Windows -- so the unlink below cannot fail with a
            # PermissionError that masks the original error (mirrors GM-07d:C).
            try:
                os.close(descriptor)
            except OSError:
                pass
        temporary.unlink(missing_ok=True)
    return destination

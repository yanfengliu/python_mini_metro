"""GM-07d high-score leaderboard: strict versioned document, ranked insertion.

The leaderboard persists lifetime deliveries keyed by ``(map, rulesVersion)``
to ``saves/highscores.json`` (D-028). It reuses the GM-07b canonical-ASCII
recipe and the save-schema scalar validators -- so it joins the persistence
isolation set -- but it never imports gameplay. Unlike a save, loading is
START-EMPTY tolerant: a missing, unreadable, non-ASCII, malformed,
forward-version, or pathologically nested file yields the empty board and never
raises, so a cosmetic leaderboard can never block play. Saving RAISES on
failure; the best-effort swallow lives at the ``main`` recorder layer.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path as FilesystemPath
from typing import Any

from save_schema import canonical_save_bytes
from save_schema_records import (
    _array,
    _exact_keys,
    _int,
    _nonnegative_int,
    _object,
    _string,
)

HIGHSCORES_SCHEMA_VERSION = 1
HIGHSCORES_STATE_CONTRACT = "mini-metro-highscores-v1"
HIGHSCORES_PER_KEY_CAP = 10
HIGHSCORES_MAP_CLASSIC = "classic"

_TOP_LEVEL_KEYS = frozenset({"schemaVersion", "stateContract", "entries"})
_ENTRY_KEYS = frozenset({"map", "rulesVersion", "deliveries"})


def _fail(label: str, message: str) -> None:
    raise ValueError(f"highscores {label} {message}")


def _ascii_string(value: Any, label: str) -> str:
    # The leaderboard is ASCII-canonical (D-026), so a string whose content is
    # non-ASCII -- even when the file's bytes are ASCII because a ``\uXXXX``
    # escape decoded to it -- is foreign and starts the board empty at load.
    text = _string(value, label)
    if not text.isascii():
        _fail(label, "must be ASCII")
    return text


def _empty_document() -> dict[str, Any]:
    """Return a fresh canonical empty leaderboard document."""

    return {
        "schemaVersion": HIGHSCORES_SCHEMA_VERSION,
        "stateContract": HIGHSCORES_STATE_CONTRACT,
        "entries": [],
    }


@dataclass(frozen=True)
class RecordResult:
    """The outcome of recording one score: the new board plus its placement."""

    document: dict[str, Any]
    rank: int | None
    is_best: bool


def validate_highscores(document: Any) -> None:
    """Strictly validate one leaderboard document; any rejection raises ValueError."""

    board = _object(document, "document")
    # Exact-key check BEFORE any field access so a missing key raises
    # ValueError (not KeyError), mirroring the save schema header.
    _exact_keys(board, _TOP_LEVEL_KEYS, "document")
    if _int(board["schemaVersion"], "schemaVersion") != HIGHSCORES_SCHEMA_VERSION:
        _fail("schemaVersion", "is unsupported (forward versions are rejected)")
    if _string(board["stateContract"], "stateContract") != HIGHSCORES_STATE_CONTRACT:
        _fail("stateContract", f"must be {HIGHSCORES_STATE_CONTRACT!r}")
    for index, item in enumerate(_array(board["entries"], "entries")):
        label = f"entries[{index}]"
        entry = _object(item, label)
        _exact_keys(entry, _ENTRY_KEYS, label)
        _ascii_string(entry["map"], f"{label}.map")
        _ascii_string(entry["rulesVersion"], f"{label}.rulesVersion")
        _nonnegative_int(entry["deliveries"], f"{label}.deliveries")


def _sort_key(entry: dict[str, Any]) -> tuple[str, str, int]:
    # Canonical order: map ascending, rulesVersion ascending, deliveries
    # descending; exact ties fall to the stable sort over append order.
    return (entry["map"], entry["rulesVersion"], -entry["deliveries"])


def record_score(
    document: dict[str, Any],
    *,
    deliveries: int,
    map: str,
    rules_version: str,
) -> RecordResult:
    """Return a NEW board with the score inserted; never mutate the input.

    All entries are stored in the pinned canonical order and the recorded
    ``(map, rulesVersion)`` group is truncated to ``HIGHSCORES_PER_KEY_CAP``.
    Entries under other keys are never dropped -- for the canonical boards the
    recorder itself produces they are returned unchanged -- so a record is
    isolated to its own key. The result carries the new entry's 1-based rank
    within its key (``None`` if it fell outside the cap) and whether it became
    that key's new best. ``map`` and ``rules_version`` are required, never
    defaulted, so a caller can never record under the wrong key.
    """

    # Fail fast on misuse: a negative/non-int deliveries or a non-ASCII key must
    # raise here rather than mint a bogus entry that a later save would persist
    # into a board that reloads empty (codex MAJOR-2).
    _nonnegative_int(deliveries, "deliveries")
    _ascii_string(map, "map")
    _ascii_string(rules_version, "rulesVersion")

    entry = {"map": map, "rulesVersion": rules_version, "deliveries": deliveries}
    entries = [dict(existing) for existing in document["entries"]]
    entries.append(entry)
    entries.sort(key=_sort_key)
    target = (map, rules_version)
    kept: list[dict[str, Any]] = []
    seen_target = 0
    for item in entries:
        if (item["map"], item["rulesVersion"]) == target:
            # Only the recorded key is capped; unrelated keys are never dropped,
            # so recording one key cannot evict another's entries (codex MAJOR-3).
            if seen_target < HIGHSCORES_PER_KEY_CAP:
                kept.append(item)
                seen_target += 1
        else:
            kept.append(item)
    rank: int | None = None
    position = 0
    for item in kept:
        if item["map"] == map and item["rulesVersion"] == rules_version:
            position += 1
            if item is entry:
                rank = position
                break
    result_document = {
        "schemaVersion": document["schemaVersion"],
        "stateContract": document["stateContract"],
        "entries": kept,
    }
    return RecordResult(document=result_document, rank=rank, is_best=rank == 1)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    # A duplicate JSON key cannot be seen on an already-parsed dict, so
    # rejection happens at parse time, mirroring save_load._reject_duplicate_keys.
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"highscores file repeats the JSON object key {key!r}")
        mapping[key] = value
    return mapping


def load_highscores(path: Any) -> dict[str, Any]:
    """Read and strictly validate a leaderboard, or START EMPTY on any failure.

    A missing, unreadable, non-ASCII, malformed, duplicate-key, forward-version,
    or pathologically nested (RecursionError) file yields the empty board and
    NEVER raises -- the deliberate difference from ``load_game``, which fails
    closed, because a cosmetic leaderboard must not block play.
    """

    try:
        payload = FilesystemPath(path).read_bytes()
        document = json.loads(
            payload.decode("ascii"), object_pairs_hook=_reject_duplicate_keys
        )
        validate_highscores(document)
        return document
    except Exception:
        return _empty_document()


def save_highscores(document: dict[str, Any], path: Any) -> FilesystemPath:
    """Atomically write canonical leaderboard bytes to ``path``; RAISE on failure.

    Validates the board first so a structurally invalid document can never
    overwrite a valid file with bytes that would reload empty (codex MAJOR-2).
    Repeats the reviewed GM-07b atomic-writer shape as a save-local copy
    (mkstemp -> fsync -> os.replace -> finally unlink), so an interrupted write
    keeps the previous valid leaderboard and leaves no temporary litter behind.
    """

    validate_highscores(document)
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
            # os.fdopen never returned, so the with block never took ownership
            # of the descriptor and never closed it. Close the raw fd here so a
            # failing fdopen (OOM/EMFILE) cannot leak it and -- on Windows -- so
            # the still-open temporary can be unlinked below without a
            # PermissionError masking the original failure. Tolerate an already
            # closed fd: some fdopen failure paths close it before raising.
            try:
                os.close(descriptor)
            except OSError:
                pass
        temporary.unlink(missing_ok=True)
    return destination

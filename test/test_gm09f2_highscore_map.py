"""GM-09f2 contract: the high-score leaderboard records the MAP identity (D-039).

The recorder threads the LIVE ``map_definition`` (id + version) off the mediator
instead of hardcoding ``classic``, and the leaderboard keys every entry by the full
``(map, mapDefinitionVersion, rulesVersion)`` identity -- so a non-Classic run is
recorded under its own map, and a future ``classic@2`` terrain revision ranks and
caps separately from ``classic@1``. A legacy v1 board is NOT migrated (its map labels
are not provably accurate); it starts empty like any other unreadable format.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import main
from highscores import (
    HIGHSCORES_PER_KEY_CAP,
    HIGHSCORES_SCHEMA_VERSION,
    record_score,
    validate_highscores,
)
from maps import CLASSIC, RIVER


def _empty_board() -> dict:
    return {
        "schemaVersion": HIGHSCORES_SCHEMA_VERSION,
        "stateContract": "mini-metro-highscores-v1",
        "entries": [],
    }


def _mediator(deliveries: int, map_definition) -> SimpleNamespace:
    # The recorder reads deliveries + map_definition.{map_id, map_definition_version}.
    return SimpleNamespace(deliveries=deliveries, map_definition=map_definition)


class TestGM09f2RecorderThreadsLiveMap(unittest.TestCase):
    """main.record_highscore records the mediator's real map, not a hardcoded classic."""

    def _record_real(self, mediator):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            with patch("main.HIGHSCORES_PATH", target, create=True):
                result = main.record_highscore(mediator)
                stored = json.loads(target.read_bytes()) if target.exists() else None
        return result, stored

    def test_classic_run_records_under_classic_at_one(self):
        result, stored = self._record_real(_mediator(7, CLASSIC))
        entry = result.document["entries"][0]
        self.assertEqual(
            (entry["map"], entry["mapDefinitionVersion"], entry["deliveries"]),
            ("classic", 1, 7),
        )
        self.assertEqual(stored["entries"][0]["map"], "classic")

    def test_a_river_run_records_under_river_not_classic(self):
        # The load-bearing GM-09f2 behavior: a non-Classic game is keyed by ITS map.
        result, _stored = self._record_real(_mediator(9, RIVER))
        entry = result.document["entries"][0]
        self.assertEqual(entry["map"], "river", "a river run must record under river")
        self.assertEqual(entry["mapDefinitionVersion"], RIVER.map_definition_version)
        self.assertEqual(entry["deliveries"], 9)

    def test_a_non_one_map_version_is_read_not_hardcoded(self):
        # Both real maps are @1, so a regression forwarding a literal version 1 would
        # pass the classic/river tests; drive a synthetic non-1 version to PROVE the
        # recorder reads map_definition.map_definition_version (GM-09f2 review MAJOR).
        synthetic = SimpleNamespace(map_id="classic", map_definition_version=7)
        result, stored = self._record_real(_mediator(4, synthetic))
        entry = result.document["entries"][0]
        self.assertEqual(
            entry["mapDefinitionVersion"], 7, "the recorder reads the live map version"
        )
        self.assertEqual(
            stored["entries"][0]["mapDefinitionVersion"],
            7,
            "the persisted board preserves the live version",
        )

    def test_the_recorded_board_validates_as_v2(self):
        result, _stored = self._record_real(_mediator(5, RIVER))
        self.assertEqual(result.document["schemaVersion"], 2)
        self.assertIsNone(validate_highscores(result.document))


class TestGM09f2CrossDefinitionVersionIdentity(unittest.TestCase):
    """The full identity keys the rank AND the cap, so classic@2 is independent of @1."""

    def _board_with(self, entries) -> dict:
        board = _empty_board()
        board["entries"] = entries
        validate_highscores(board)
        return board

    def test_a_fresh_definition_version_ranks_first_not_against_the_old(self):
        # The rank-loop MAJOR (both plan lanes): a first classic@2 score must be rank 1
        # / is_best True even when a higher classic@1 group exists -- it is the best of
        # its OWN identity, not rank 2 behind classic@1.
        board = self._board_with(
            [
                {
                    "map": "classic",
                    "mapDefinitionVersion": 1,
                    "rulesVersion": "rules-v1",
                    "deliveries": 100,
                }
            ]
        )
        result = record_score(
            board,
            deliveries=1,
            map="classic",
            map_definition_version=2,
            rules_version="rules-v1",
        )
        self.assertEqual(result.rank, 1, "classic@2's first score ranks 1 within @2")
        self.assertIs(result.is_best, True)

    def test_a_new_version_cannot_evict_an_over_cap_old_version_group(self):
        # Cross-identity isolation: classic@1 holds an over-cap group (validation checks
        # structure, not the cap); recording classic@2 must not truncate it.
        over_cap = [
            {
                "map": "classic",
                "mapDefinitionVersion": 1,
                "rulesVersion": "rules-v1",
                "deliveries": d,
            }
            for d in range(HIGHSCORES_PER_KEY_CAP + 1, 0, -1)
        ]
        board = self._board_with(over_cap)
        result = record_score(
            board,
            deliveries=5,
            map="classic",
            map_definition_version=2,
            rules_version="rules-v1",
        )
        classic_v1 = [
            e
            for e in result.document["entries"]
            if e["map"] == "classic" and e["mapDefinitionVersion"] == 1
        ]
        self.assertEqual(
            len(classic_v1),
            HIGHSCORES_PER_KEY_CAP + 1,
            "recording classic@2 must not drop an over-cap classic@1 entry",
        )
        self.assertEqual((result.rank, result.is_best), (1, True))

    def test_two_definition_versions_sort_as_distinct_groups(self):
        board = _empty_board()
        for deliveries, version in ((5, 1), (9, 2), (3, 1), (7, 2)):
            board = record_score(
                board,
                deliveries=deliveries,
                map="classic",
                map_definition_version=version,
                rules_version="rules-v1",
            ).document
        ordered = [
            (e["mapDefinitionVersion"], e["deliveries"]) for e in board["entries"]
        ]
        # Canonical order: identity ascending (version 1 before 2), deliveries desc.
        self.assertEqual(ordered, [(1, 5), (1, 3), (2, 9), (2, 7)])


class TestGM09f2LegacyBoardStartsEmpty(unittest.TestCase):
    def test_a_v1_board_is_not_migrated_but_starts_empty(self):
        # D-039: a v1 board's map="classic" labels are not provably accurate (the
        # recorder was classic-hardcoded while non-Classic saves became loadable), so
        # it is discarded rather than synthesized to authoritative classic@1.
        from highscores import load_highscores

        v1_board = {
            "schemaVersion": 1,
            "stateContract": "mini-metro-highscores-v1",
            "entries": [
                {"map": "classic", "rulesVersion": "rules-v1", "deliveries": 42}
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            target.write_bytes(json.dumps(v1_board).encode("ascii"))
            loaded = load_highscores(target)
        self.assertEqual(loaded, _empty_board(), "a legacy v1 board starts empty")


if __name__ == "__main__":
    unittest.main()
